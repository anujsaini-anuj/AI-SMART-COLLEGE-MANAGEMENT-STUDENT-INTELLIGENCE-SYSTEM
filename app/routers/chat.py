from datetime import datetime, timezone
import time

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect
)

from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from jose import jwt, JWTError

from app.database.database import get_db, SessionLocal
from app.database.models import (
    User,
    Student,
    Faculty,
    HOD,
    Department,
    Course,
    Subject,
    FacultySubject,
    ChatConversation,
    ChatParticipant,
    ChatMessage,
    ChatMessageReceipt
)

from app.schemas.chat import CreateGroupChatRequest
from app.utils.auth import get_current_user, SECRET_KEY, ALGORITHM
from app.services.chat_manager import chat_manager

from sqlalchemy.exc import IntegrityError

import asyncio

import logging

logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/chat",
    tags=["Chat"]
)



def is_chat_allowed(db: Session, user_a: User, user_b: User) -> bool:


    if not user_a.is_active or not user_b.is_active:
        return False


    if user_a.id == user_b.id:
        return False

    # Get both users' college profiles.
    student_a = db.query(Student).filter(
        Student.user_id == user_a.id
    ).first()

    student_b = db.query(Student).filter(
        Student.user_id == user_b.id
    ).first()

    if student_a and not student_a.is_active:
        return False

    if student_b and not student_b.is_active:
        return False

    # Admin can chat with every active user.
    if user_a.role == "admin" or user_b.role == "admin":
        return True

    faculty_a = db.query(Faculty).filter(
        Faculty.user_id == user_a.id
    ).first()

    faculty_b = db.query(Faculty).filter(
        Faculty.user_id == user_b.id
    ).first()

    hod_a = db.query(HOD).filter(
        HOD.user_id == user_a.id
    ).first()

    hod_b = db.query(HOD).filter(
        HOD.user_id == user_b.id
    ).first()

    # Student to Student: same department, course,
    # batch year and semester.
    if student_a and student_b:

        return (
            student_a.department_id == student_b.department_id
            and student_a.course_id == student_b.course_id
            and student_a.batch_year == student_b.batch_year
            and student_a.semester == student_b.semester
        )

    # Student to Faculty: faculty must teach at least
    # one subject of student's course and semester.
    if student_a and faculty_b:

        if faculty_b.department_id != student_a.department_id:
            return False

        return db.query(FacultySubject.id).join(
            Subject,
            Subject.id == FacultySubject.subject_id
        ).filter(
            FacultySubject.faculty_id == faculty_b.id,
            Subject.course_id == student_a.course_id,
            Subject.semester == student_a.semester
        ).first() is not None

    # Faculty to Student: same rule in reverse.
    if faculty_a and student_b:

        if faculty_a.department_id != student_b.department_id:
            return False

        return db.query(FacultySubject.id).join(
            Subject,
            Subject.id == FacultySubject.subject_id
        ).filter(
            FacultySubject.faculty_id == faculty_a.id,
            Subject.course_id == student_b.course_id,
            Subject.semester == student_b.semester
        ).first() is not None

    # Student to HOD: same department.
    if student_a and hod_b:

        return student_a.department_id == hod_b.department_id

    if hod_a and student_b:

        return hod_a.department_id == student_b.department_id

    # Faculty to Faculty: same department.
    if faculty_a and faculty_b:

        return faculty_a.department_id == faculty_b.department_id

    # Faculty to HOD: same department.
    if faculty_a and hod_b:

        return faculty_a.department_id == hod_b.department_id

    if hod_a and faculty_b:

        return hod_a.department_id == faculty_b.department_id

    # HOD to HOD: same department.
    if hod_a and hod_b:

        return hod_a.department_id == hod_b.department_id

    # Unknown or unsupported profile combination.
    return False



# ==================================================
# HELPER: CHECK CONVERSATION MEMBERSHIP
# ==================================================

def check_chat_member(
    db: Session,
    conversation_id: int,
    user_id: int
):
    # 1. Check whether user is a participant
    participant = db.query(ChatParticipant).filter(
        ChatParticipant.conversation_id == conversation_id,
        ChatParticipant.user_id == user_id
    ).first()

    if participant is None:
        raise HTTPException(
            status_code=403,
            detail="You are not a participant of this chat"
        )

    # 2. Check whether conversation exists
    conversation = db.query(ChatConversation).filter(
        ChatConversation.id == conversation_id
    ).first()

    if conversation is None:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found"
        )

    # 3. Get all chat participants
    participants = db.query(ChatParticipant).filter(
        ChatParticipant.conversation_id == conversation_id
    ).all()

    if len(participants) < 2:
        raise HTTPException(
            status_code=403,
            detail="Invalid chat conversation"
        )

    participant_ids = [p.user_id for p in participants]

    # 4. Get all active users
    users = db.query(User).filter(
        User.id.in_(participant_ids),
        User.is_active == True
    ).all()

    if len(users) != len(participant_ids):
        raise HTTPException(
            status_code=403,
            detail="A chat participant is inactive or unavailable"
        )

    # 5. Find current user
    current_user = next(
        (
            user for user in users
            if user.id == user_id
        ),
        None
    )

    if current_user is None:
        raise HTTPException(
            status_code=403,
            detail="Your account is inactive"
        )

    # 6. Validate current user against other participants only
    for other_user in users:

        if other_user.id == current_user.id:
            continue

        if not is_chat_allowed(
            db,
            current_user,
            other_user
        ):
            raise HTTPException(
                status_code=403,
                detail="You are no longer allowed to access this chat"
            )

    return participant

# ==================================================
# CREATE / OPEN DIRECT CHAT
# ==================================================

@router.post("/direct/{other_user_id}")
def create_direct_chat(
    other_user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    if other_user_id == current_user.id:

        raise HTTPException(
            status_code=400,
            detail="You cannot create a chat with yourself"
        )

    other_user = db.query(User).filter(
        User.id == other_user_id,
        User.is_active == True
    ).first()

    if other_user is None:

        raise HTTPException(
            status_code=404,
            detail="User not found or inactive"
        )

    # College-based chat permission check
    if not is_chat_allowed(db, current_user, other_user):

        raise HTTPException(
            status_code=403,
            detail="You are not allowed to chat with this user"
        )

    first_id, second_id = sorted([
        current_user.id,
        other_user.id
    ])

    direct_key = f"direct:{first_id}:{second_id}"

    conversation = db.query(ChatConversation).filter(
        ChatConversation.direct_key == direct_key
    ).first()

    if conversation:

        return {
            "message": "Direct chat already exists",
            "conversation_id": conversation.id,
            "conversation_type": "direct"
        }

    conversation = ChatConversation(
        conversation_type="direct",
        direct_key=direct_key,
        created_by=current_user.id
    )

    db.add(conversation)

    try:
        db.flush()

        db.add_all([
            ChatParticipant(
                conversation_id=conversation.id,
                user_id=current_user.id
            ),
            ChatParticipant(
                conversation_id=conversation.id,
                user_id=other_user.id
            )
        ])

        db.commit()
        db.refresh(conversation)

    except IntegrityError:

        db.rollback()

        conversation = db.query(ChatConversation).filter(
            ChatConversation.direct_key == direct_key
        ).first()

        if conversation is None:
            raise HTTPException(
                status_code=409,
                detail="Could not create direct chat. Please retry."
            )

    return {
        "message": "Direct chat created successfully",
        "conversation_id": conversation.id,
        "conversation_type": "direct"
    }


# ==================================================
# CREATE GROUP CHAT
# ==================================================

@router.post("/groups")
def create_group_chat(
    request: CreateGroupChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    if current_user.role not in ["admin", "faculty", "hod"]:

        raise HTTPException(
            status_code=403,
            detail="Only admin, faculty or HOD can create group chats"
        )

    participant_ids = set(request.participant_ids)
    participant_ids.add(current_user.id)

    if len(participant_ids) < 2:
        raise HTTPException(
            status_code=400,
            detail="A group chat must have at least 2 participants"
        )


    users = db.query(User).filter(
        User.id.in_(participant_ids),
        User.is_active == True
    ).all()

    if len(users) != len(participant_ids):

        raise HTTPException(
            status_code=400,
            detail="One or more users do not exist or are inactive"
        )


    # Check every participant against every other participant.
    for i, user_a in enumerate(users):

        for user_b in users[i + 1:]:

            if not is_chat_allowed(db, user_a, user_b):

                raise HTTPException(
                    status_code=403,
                    detail=(
                        f"Group chat is not allowed between "
                        f"{user_a.name} and {user_b.name}"
                    )
                )

    conversation = ChatConversation(
        conversation_type="group",
        title=request.title.strip(),
        created_by=current_user.id
    )

    db.add(conversation)
    db.flush()

    for user in users:

        db.add(
            ChatParticipant(
                conversation_id=conversation.id,
                user_id=user.id
            )
        )

    db.commit()
    db.refresh(conversation)

    return {
        "message": "Group created successfully",
        "conversation_id": conversation.id,
        "title": conversation.title,
        "participant_count": len(users)
    }


@router.get("/contacts")
def get_chat_contacts(
    search: str = Query(default="", max_length=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    users = db.query(User).filter(
        User.id != current_user.id,
        User.is_active == True
    ).order_by(User.name).all()

    allowed_contacts = []

    for user in users:

        if not is_chat_allowed(db, current_user, user):
            continue

        if search.strip() and search.strip().lower() not in user.name.lower():
            continue

        allowed_contacts.append({
            "user_id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "is_online": chat_manager.is_online(user.id)
        })

        if len(allowed_contacts) >= 50:
            break

    return allowed_contacts

# ==================================================
# GET MY CONVERSATIONS
# ==================================================

@router.get("/conversations")
def get_my_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    conversations = (
        db.query(ChatConversation)
        .join(
            ChatParticipant,
            ChatParticipant.conversation_id == ChatConversation.id
        )
        .filter(
            ChatParticipant.user_id == current_user.id
        )
        .order_by(ChatConversation.updated_at.desc())
        .all()
    )

    result = []

    for conversation in conversations:

        try:
            check_chat_member(
                db,
                conversation.id,
                current_user.id
            )
        except HTTPException:
            continue

        participants = (
            db.query(User)
            .join(
                ChatParticipant,
                ChatParticipant.user_id == User.id
            )
            .filter(
                ChatParticipant.conversation_id == conversation.id
            )
            .all()
        )

        unread_count = (
            db.query(func.count(ChatMessageReceipt.id))
            .join(
                ChatMessage,
                ChatMessage.id == ChatMessageReceipt.message_id
            )
            .filter(
                ChatMessage.conversation_id == conversation.id,
                ChatMessage.is_deleted == False,
                ChatMessageReceipt.user_id == current_user.id,
                ChatMessageReceipt.read_at.is_(None)
            )
            .scalar()
        )

        result.append({
            "conversation_id": conversation.id,
            "conversation_type": conversation.conversation_type,
            "title": conversation.title,
            "participants": [
                {
                    "user_id": user.id,
                    "name": user.name,
                    "role": user.role,
                    "is_online": chat_manager.is_online(user.id)
                }
                for user in participants
            ],
            "unread_count": unread_count or 0,
            "updated_at": conversation.updated_at.isoformat()
        })

    return result


# ==================================================
# GET CHAT HISTORY
# ==================================================

@router.get("/conversations/{conversation_id}/messages")
def get_chat_messages(
    conversation_id: int,
    limit: int = Query(default=50, ge=1, le=100),
    before_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    check_chat_member(
        db,
        conversation_id,
        current_user.id
    )

    query = db.query(ChatMessage).filter(
        ChatMessage.conversation_id == conversation_id
    )

    if before_id:

        query = query.filter(
            ChatMessage.id < before_id
        )

    messages = (
        query.order_by(ChatMessage.id.desc())
        .limit(limit)
        .all()
    )

    messages.reverse()

    return [
        {
            "message_id": message.id,
            "conversation_id": message.conversation_id,
            "sender_id": message.sender_id,
            "content": message.content,
            "created_at": message.created_at.isoformat(),
            "edited_at": (
                message.edited_at.isoformat()
                if message.edited_at else None
            ),
            "is_deleted": message.is_deleted
        }
        for message in messages
    ]




# ==================================================
# WEBSOCKET CHAT
# ==================================================

@router.websocket("/ws/{conversation_id}")
async def chat_websocket(
    websocket: WebSocket,
    conversation_id: int
):

    await websocket.accept()

    current_user = None
    current_user_id = None
    current_user_name = None
    connected = False

    try:

        # ------------------------------------------
        # 1. AUTHENTICATION
        # ------------------------------------------

        auth_data = await asyncio.wait_for(
            websocket.receive_json(),
            timeout=10
        )

        if not isinstance(auth_data, dict):
            await websocket.close(code=1008)
            return

        if auth_data.get("type") != "auth":
            await websocket.close(code=1008)
            return

        token = auth_data.get("token")

        if not token:

            await websocket.close(code=1008)
            return

        try:

            payload = jwt.decode(
                token,
                SECRET_KEY,
                algorithms=[ALGORITHM]
            )

            user_id = int(payload.get("sub"))

            token_exp = payload.get("exp")

            if token_exp is None:
                await websocket.close(code=1008)
                return

        except (JWTError, ValueError, TypeError):

            await websocket.close(code=1008)
            return

        # ------------------------------------------
        # 2. AUTHENTICATE USER + CHECK MEMBERSHIP
        # ------------------------------------------

        auth_db = SessionLocal()

        try:

            current_user = auth_db.query(User).filter(
                User.id == user_id,
                User.is_active == True
            ).first()

            if current_user is None:

                await websocket.close(code=1008)
                return

            current_user_id = current_user.id
            current_user_name = current_user.name

            check_chat_member(
                auth_db,
                conversation_id,
                current_user_id
            )

            participant_ids = [
                row.user_id
                for row in auth_db.query(ChatParticipant.user_id).filter(
                    ChatParticipant.conversation_id == conversation_id
                ).all()
            ]

        except HTTPException:

            await websocket.close(code=1008)
            return

        finally:

            auth_db.close()

        # ------------------------------------------
        # 3. REGISTER CONNECTION
        # ------------------------------------------

        await chat_manager.connect(
            current_user_id,
            conversation_id,
            websocket
        )
        connected = True

        await websocket.send_json({
            "type": "connected",
            "conversation_id": conversation_id,
            "user_id": current_user_id,
            "message": "WebSocket connected successfully"
        })

        await chat_manager.broadcast(
            conversation_id,
            [
                user_id
                for user_id in participant_ids
                if user_id != current_user.id
            ],
            {
                "type": "presence",
                "user_id": current_user_id,
                "status": "online"
            }
        )

        # ------------------------------------------
        # 4. RECEIVE EVENTS
        # ------------------------------------------

        while True:
                
                # Remaining JWT lifetime
                remaining_seconds = token_exp - time.time()

                if remaining_seconds <= 0:

            
                    await websocket.send_json({
                        "type": "error",
                        "message": "Authentication token expired"
                    })

                    await websocket.close(code=1008)
                    break

                try:

                    # Wait only until the token expires.
                    data = await asyncio.wait_for(
                        websocket.receive_json(),
                        timeout=remaining_seconds
                    )

                except asyncio.TimeoutError:

                    await websocket.send_json({
                        "type": "error",
                        "message": "Authentication token expired"
                    })

                    await websocket.close(code=1008)
                    break

            

                db = SessionLocal()


                # 1. Re-check account, membership and permissions
                try:

                    # 2. Validate incoming data first
                    if not isinstance(data, dict):
                        await websocket.send_json({
                            "type": "error",
                            "message": "Invalid event data"
                        })
                        continue

                    event_type = data.get("type")

                    try:
                        participant = check_chat_member(
                            db,
                            conversation_id,
                            current_user.id
                        )

                        participant_ids = [
                            row.user_id
                            for row in db.query(ChatParticipant.user_id).filter(
                                ChatParticipant.conversation_id == conversation_id
                            ).all()
                        ]

                    except HTTPException:
                        await websocket.close(code=1008)
                        break


                    # EDIT MESSAGE
                    if data.get("type") == "edit":
                        message_id = data.get("message_id")
                        new_content = data.get("content")

                        if (
                            not isinstance(message_id, int)
                            or isinstance(message_id, bool)
                            or message_id <= 0
                        ):
                            await websocket.send_json({
                                "type": "error",
                                "message": "Valid positive message_id is required"
                            })
                            continue

                        if not isinstance(new_content, str):
                            await websocket.send_json({
                                "type": "error",
                                "message": "Message content must be text"
                            })
                            continue

                        new_content = new_content.strip()

                        if not new_content or len(new_content) > 5000:
                            await websocket.send_json({
                                "type": "error",
                                "message": "Message must contain 1 to 5000 characters"
                            })
                            continue

                        message = db.query(ChatMessage).filter(
                            ChatMessage.id == message_id,
                            ChatMessage.conversation_id == conversation_id
                        ).with_for_update().first()

                        if message is None:

                            db.rollback()

                            await websocket.send_json({
                                "type": "error",
                                "message": "Message not found"
                            })
                            continue

                        if message.sender_id != current_user_id:
                            db.rollback()

                            await websocket.send_json({
                                "type": "error",
                                "message": "You can only edit your own messages"
                            })
                            continue

                        if message.is_deleted:
                            db.rollback()

                            await websocket.send_json({
                                "type": "error",
                                "message": "Deleted messages cannot be edited"
                            })
                            continue

                        message.content = new_content
                        message.edited_at = datetime.now(timezone.utc)

                        conversation = db.query(ChatConversation).filter(
                            ChatConversation.id == conversation_id
                        ).first()

                        if conversation:
                            conversation.updated_at = datetime.now(timezone.utc)

                        try:
                            db.commit()
                            db.refresh(message)

                        except Exception:
                            db.rollback()
                            logger.exception("Message edit failed")

                            await websocket.send_json({
                                "type": "error",
                                "message": "Unable to edit message"
                            })
                            continue

                        event = {
                            "type": "message_edited",
                            "message_id": message.id,
                            "conversation_id": conversation_id,
                            "sender_id": current_user.id,
                            "content": message.content,
                            "edited_at": message.edited_at.isoformat()
                        }

                        recipients = [
                            uid for uid in participant_ids
                            if uid != current_user.id
                        ]

                        try:

                            await chat_manager.broadcast(
                                conversation_id,
                                recipients,
                                event
                            )

                        except Exception:
                            logger.exception("Message edit broadcast failed")

                        # Sender ko confirmation
                        await websocket.send_json({
                            **event,
                            "type": "edit_success"
                        })

                        continue


                    # DELETE MESSAGE
                    if data.get("type") == "delete":
                        message_id = data.get("message_id")

                        if (
                            not isinstance(message_id, int)
                            or isinstance(message_id, bool)
                            or message_id <= 0
                        ):

                            await websocket.send_json({
                                "type": "error",
                                "message": "Valid positive message_id is required"
                            })
                            continue

                        message = db.query(ChatMessage).filter(
                            ChatMessage.id == message_id,
                            ChatMessage.conversation_id == conversation_id
                        ).with_for_update().first()

                        if message is None:
                            db.rollback()

                            await websocket.send_json({
                                "type": "error",
                                "message": "Message not found"
                            })
                            continue

                        if message.sender_id != current_user.id:
                            db.rollback()

                            await websocket.send_json({
                                "type": "error",
                                "message": "You can only delete your own messages"
                            })
                            continue

                        if message.is_deleted:
                            db.rollback()

                            await websocket.send_json({
                                "type": "error",
                                "message": "Message is already deleted"
                            })
                            continue

                        # Soft delete
                        message.is_deleted = True
                        message.content = "This message was deleted"

                        conversation = db.query(ChatConversation).filter(
                            ChatConversation.id == conversation_id
                        ).first()

                        if conversation:
                            conversation.updated_at = datetime.now(timezone.utc)

                        try:
                            db.commit()

                        except Exception:
                            db.rollback()
                            logger.exception("Message delete failed")

                            await websocket.send_json({
                                "type": "error",
                                "message": "Unable to delete message"
                            })
                            continue

                        event = {
                            "type": "message_deleted",
                            "message_id": message.id,
                            "conversation_id": conversation_id,
                            "deleted_by": current_user.id,
                            "content": message.content,
                            "is_deleted": True
                        }

                        recipients = [
                            uid for uid in participant_ids
                            if uid != current_user.id
                        ]

                        try:

                            await chat_manager.broadcast(
                                conversation_id,
                                recipients,
                                event
                            )

                        except Exception:
                            logger.exception("Message delete broadcast failed")

                        # Sender ko confirmation
                        await websocket.send_json({
                            **event,
                            "type": "delete_success"
                        })

                        continue

                    # ======================================
                    # SEND MESSAGE
                    # ======================================
                            
                    if event_type == "send":

                        content = data.get("content", "")

                        if not isinstance(content, str):
                            await websocket.send_json({
                                "type": "error",
                                "message": "Message content must be text"
                            })
                            continue

                        content = content.strip()

                        if not content or len(content) > 5000:
                            await websocket.send_json({
                                "type": "error",
                                "message": "Message must contain 1 to 5000 characters"
                            })
                            continue

                        try:
                            now = datetime.now(timezone.utc)

                            message = ChatMessage(
                                conversation_id=conversation_id,
                                sender_id=current_user_id,
                                content=content
                            )

                            db.add(message)
                            db.flush()

                            recipients = [
                                uid for uid in participant_ids
                                if uid != current_user.id
                            ]

                            for recipient_id in recipients:
                                db.add(
                                    ChatMessageReceipt(
                                        message_id=message.id,
                                        user_id=recipient_id
                                    )
                                )

                            conversation = db.query(ChatConversation).filter(
                                ChatConversation.id == conversation_id
                            ).first()

                            if conversation is None:
                                raise ValueError("Conversation not found")

                            conversation.updated_at = now

                            db.commit()
                            db.refresh(message)

                        except Exception:
                            db.rollback()

                            logger.exception("Failed to save chat message")

                            await websocket.send_json({
                                "type": "error",
                                "message": "Message could not be saved. Please retry."
                            })
                            continue

                        try:

                            # Broadcast only after successful database commit.
                            await chat_manager.broadcast(
                                conversation_id,
                                recipients,
                                {
                                    "type": "message",
                                    "message_id": message.id,
                                    "conversation_id": conversation_id,
                                    "sender_id": current_user_id,
                                    "sender_name": current_user_name,
                                    "content": message.content,
                                    "created_at": message.created_at.isoformat()
                                }
                            )

                        except Exception:
                            logger.exception("Message broadcast failed")

                        await websocket.send_json({
                            "type": "sent",
                            "message_id": message.id,
                            "conversation_id": conversation_id,
                            "message": "Message saved successfully"
                        })


                    # ======================================
                    # TYPING INDICATOR
                    # ======================================

                    elif event_type == "typing":

                        is_typing_value = data.get("is_typing", False)

                        if not isinstance(is_typing_value, bool):
                            await websocket.send_json({
                                "type": "error",
                                "message": "is_typing must be true or false"
                            })
                            continue

                        is_typing = is_typing_value

                        await chat_manager.broadcast(
                            conversation_id,
                            [
                                user_id
                                for user_id in participant_ids
                                if user_id != current_user.id
                            ],
                            {
                                "type": "typing",
                                "user_id": current_user.id,
                                "is_typing": is_typing
                            }
                        )


                    # ======================================
                    # MESSAGE DELIVERED ACKNOWLEDGEMENT
                    # ======================================

                    elif event_type == "delivered":

                        message_id = data.get("message_id")

                        if (
                            not isinstance(message_id, int)
                            or isinstance(message_id, bool)
                            or message_id <= 0
                        ):

                            await websocket.send_json({
                                "type": "error",
                                "message": "Valid positive message_id is required"
                            })

                            continue

                        message = db.query(ChatMessage).filter(
                            ChatMessage.id == message_id,
                            ChatMessage.conversation_id == conversation_id,
                            ChatMessage.sender_id != current_user.id
                        ).first()

                        if message is None:
                            continue

                        receipt = db.query(ChatMessageReceipt).filter(
                            ChatMessageReceipt.message_id == message_id,
                            ChatMessageReceipt.user_id == current_user.id
                        ).first()

                        if receipt is None:
                            continue

                        if receipt.delivered_at is None:

                            now = datetime.now(timezone.utc)

                            try:

                                receipt.delivered_at = now

                                db.commit()

                            except Exception:

                                db.rollback()

                                logger.exception("Failed to update delivery receipt")

                                await websocket.send_json({
                                    "type": "error",
                                    "message": "Delivery receipt could not be updated"
                                })

                                continue

                            try:

                                await chat_manager.send_to_user(
                                    message.sender_id,
                                    conversation_id,
                                    {
                                        "type": "delivery",
                                        "message_id": message_id,
                                        "delivered_to": current_user_id,
                                        "delivered_at": now.isoformat()
                                    }
                                )

                            except Exception:

                                logger.exception("Delivery notification failed")

                    # ======================================
                    # READ RECEIPT
                    # ======================================

                    elif event_type == "read":

                        message_id = data.get("message_id")

                        if (
                            not isinstance(message_id, int)
                            or isinstance(message_id, bool)
                            or message_id <= 0
                        ):
                            
                            await websocket.send_json({
                                "type": "error",
                                "message": "Valid message_id is required"
                            })

                            continue

                        target_message = db.query(ChatMessage).filter(
                            ChatMessage.id == message_id,
                            ChatMessage.conversation_id == conversation_id,
                            ChatMessage.sender_id != current_user_id,
                            ChatMessage.is_deleted == False
                        ).first()

                        if target_message is None:
                            await websocket.send_json({
                                "type": "error",
                                "message": "Message not found in this conversation"
                            })
                            continue

                        
                        now = datetime.now(timezone.utc)

                        # Only messages sent by other participants
                        # will be marked as read for the current user.
                        message_ids_query = db.query(
                            ChatMessage.id
                        ).filter(
                            ChatMessage.conversation_id == conversation_id,
                            ChatMessage.id <= message_id,
                            ChatMessage.sender_id != current_user_id,
                            ChatMessage.is_deleted == False
                        )

                        try:
                            db.query(ChatMessageReceipt).filter(
                                ChatMessageReceipt.message_id.in_(message_ids_query),
                                ChatMessageReceipt.user_id == current_user.id,
                                ChatMessageReceipt.read_at.is_(None)
                            ).update(
                                {
                                    ChatMessageReceipt.read_at: now,
                                    ChatMessageReceipt.delivered_at: now
                                },
                                synchronize_session=False
                            )

                            participant.last_read_at = now

                            db.commit()

                        except Exception:
                            db.rollback()

                            logger.exception("Failed to update read receipt")

                            await websocket.send_json({
                                "type": "error",
                                "message": "Read receipt could not be updated"
                            })
                            continue

                        await chat_manager.broadcast(
                            conversation_id,
                            [
                                uid for uid in participant_ids
                                if uid != current_user.id
                            ],
                            {
                                "type": "read",
                                "conversation_id": conversation_id,
                                "user_id": current_user.id,
                                "message_id": message_id,
                                "read_at": now.isoformat()
                            }
                        )

                    # ======================================
                    # PING / PONG
                    # ======================================

                    elif event_type == "ping":

                        await websocket.send_json({
                            "type": "pong"
                        })

                    else:

                        await websocket.send_json({
                            "type": "error",
                            "message": "Unsupported event type"
                        })

                finally:
                    db.close()

    except asyncio.TimeoutError:

        await websocket.close(code=1008)

        return

    except WebSocketDisconnect:
        pass

    except Exception:

        logger.exception("WebSocket chat error")

        try:

            await websocket.close(code=1011)

        except Exception:
            pass

    finally:

        if current_user is not None and connected:

            await chat_manager.disconnect(
                current_user.id,
                conversation_id,
                websocket
            )

            # Notify remaining participants.
            try:

                remaining_db = SessionLocal()

                try:

                    participant_ids = [
                        row.user_id
                        for row in remaining_db.query(
                            ChatParticipant.user_id
                        ).filter(
                            ChatParticipant.conversation_id == conversation_id
                        ).all()
                    ]

                finally:

                    remaining_db.close()

                await chat_manager.broadcast(
                    conversation_id,
                    [
                        user_id
                        for user_id in participant_ids
                        if user_id != current_user.id
                    ],
                    {
                        "type": "presence",
                        "user_id": current_user.id,
                        "status": (
                            "online"
                            if chat_manager.is_online(current_user.id)
                            else "offline"
                        )
                    }
                )

            except Exception:
                pass