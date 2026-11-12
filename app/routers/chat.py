from datetime import datetime, timezone

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
    ChatConversation,
    ChatParticipant,
    ChatMessage,
    ChatMessageReceipt
)

from app.schemas.chat import CreateGroupChatRequest
from app.utils.auth import get_current_user, SECRET_KEY, ALGORITHM
from app.services.chat_manager import chat_manager

import asyncio

import logging

logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/chat",
    tags=["Chat"]
)


# ==================================================
# HELPER: CHECK CONVERSATION MEMBERSHIP
# ==================================================

def check_chat_member(
    db: Session,
    conversation_id: int,
    user_id: int
):

    participant = db.query(ChatParticipant).filter(
        ChatParticipant.conversation_id == conversation_id,
        ChatParticipant.user_id == user_id
    ).first()

    if participant is None:

        raise HTTPException(
            status_code=403,
            detail="You are not a participant of this chat"
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

    users = db.query(User).filter(
        User.id.in_(participant_ids),
        User.is_active == True
    ).all()

    if len(users) != len(participant_ids):

        raise HTTPException(
            status_code=400,
            detail="One or more users do not exist or are inactive"
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


# ==================================================
# GET CHAT CONTACTS
# ==================================================

@router.get("/contacts")
def get_chat_contacts(
    search: str = Query(default="", max_length=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    query = db.query(User).filter(
        User.id != current_user.id,
        User.is_active == True
    )

    if search.strip():

        query = query.filter(
            User.name.ilike(f"%{search.strip()}%")
        )

    users = query.order_by(User.name).limit(50).all()

    return [
        {
            "user_id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "is_online": chat_manager.is_online(user.id)
        }
        for user in users
    ]


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
        ChatMessage.conversation_id == conversation_id,
        ChatMessage.is_deleted == False
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
            "created_at": message.created_at.isoformat()
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

    db = SessionLocal()
    current_user = None

    try:

        # ------------------------------------------
        # 1. AUTHENTICATION
        # ------------------------------------------

        auth_data = await asyncio.wait_for(
            websocket.receive_json(),
            timeout=10
        )

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

        except (JWTError, ValueError, TypeError):

            await websocket.close(code=1008)
            return

        current_user = db.query(User).filter(
            User.id == user_id,
            User.is_active == True
        ).first()

        if current_user is None:

            await websocket.close(code=1008)
            return

        # ------------------------------------------
        # 2. CHECK CHAT MEMBERSHIP
        # ------------------------------------------

        participant = db.query(ChatParticipant).filter(
            ChatParticipant.conversation_id == conversation_id,
            ChatParticipant.user_id == current_user.id
        ).first()

        if participant is None:

            await websocket.close(code=1008)
            return

        participant_ids = [
            row.user_id
            for row in db.query(ChatParticipant.user_id).filter(
                ChatParticipant.conversation_id == conversation_id
            ).all()
        ]

        # ------------------------------------------
        # 3. REGISTER CONNECTION
        # ------------------------------------------

        await chat_manager.connect(
            current_user.id,
            conversation_id,
            websocket
        )

        await websocket.send_json({
            "type": "connected",
            "conversation_id": conversation_id,
            "user_id": current_user.id,
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
                "user_id": current_user.id,
                "status": "online"
            }
        )

        # ------------------------------------------
        # 4. RECEIVE EVENTS
        # ------------------------------------------

        while True:

            data = await websocket.receive_json()

            event_type = data.get("type")

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

                message = ChatMessage(
                    conversation_id=conversation_id,
                    sender_id=current_user.id,
                    content=content
                )

                db.add(message)
                db.flush()

                now = datetime.now(timezone.utc)

                recipients = [
                    user_id
                    for user_id in participant_ids
                    if user_id != current_user.id
                ]

                for recipient_id in recipients:

                    receipt = ChatMessageReceipt(
                        message_id=message.id,
                        user_id=recipient_id
                    )


                    db.add(receipt)

                conversation = db.query(ChatConversation).filter(
                    ChatConversation.id == conversation_id
                ).first()

                conversation.updated_at = now

                db.commit()
                db.refresh(message)


                recipient_ids = [
                    user_id
                    for user_id in participant_ids
                    if user_id != current_user.id
                ]

                await chat_manager.broadcast(
                    conversation_id,
                    recipient_ids,
                    {
                        "type": "message",
                        "message_id": message.id,
                        "conversation_id": conversation_id,
                        "sender_id": current_user.id,
                        "sender_name": current_user.name,
                        "content": message.content,
                        "created_at": message.created_at.isoformat()
                    }
                )

                # Message successfully saved in database
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

                is_typing = bool(
                    data.get("is_typing", False)
                )

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

                if not isinstance(message_id, int) or message_id <= 0:

                    await websocket.send_json({
                        "type": "error",
                        "message": "Valid message_id is required"
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

                    receipt.delivered_at = now

                    db.commit()

                    await chat_manager.send_to_user(
                        message.sender_id,
                        conversation_id,
                        {
                            "type": "delivery",
                            "message_id": message_id,
                            "delivered_to": current_user.id,
                            "delivered_at": now.isoformat()
                        }
                    )

            # ======================================
            # READ RECEIPT
            # ======================================

            elif event_type == "read":

                message_id = data.get("message_id")

                if not isinstance(message_id, int) or message_id <= 0:

                    await websocket.send_json({
                        "type": "error",
                        "message": "Valid message_id is required"
                    })

                    continue

                target_message = db.query(ChatMessage).filter(
                    ChatMessage.id == message_id,
                    ChatMessage.conversation_id == conversation_id
                ).first()

                if target_message is None:

                    await websocket.send_json({
                        "type": "error",
                        "message": "Message not found in this chat"
                    })

                    continue

                now = datetime.now(timezone.utc)

                message_ids_query = db.query(
                    ChatMessage.id
                ).filter(
                    ChatMessage.conversation_id == conversation_id,
                    ChatMessage.id <= message_id
                )

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

                await chat_manager.broadcast(
                    conversation_id,
                    participant_ids,
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

        if current_user is not None:

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

        db.close()