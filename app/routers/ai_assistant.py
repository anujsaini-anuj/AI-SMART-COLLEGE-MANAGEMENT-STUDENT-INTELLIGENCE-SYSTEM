from fastapi import APIRouter, Depends, HTTPException, Form
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.models import Student

from app.utils.auth import get_current_user

from app.services.ai_assistant import create_ai_assistant


router = APIRouter(
    prefix="/ai",
    tags=["AI College Assistant"]
)


@router.post("/chat")
def ai_chat(
    question: str = Form(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    AI College Assistant.

    Students can ask about their own information.
    Faculty and admin can ask about student information
    according to their role.
    """

    question = question.strip()

    if not question:
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty"
        )

    # -------------------------------------------------
    # STUDENT CONTEXT
    # -------------------------------------------------

    if current_user.role == "student":

        student = db.query(Student).filter(
            Student.user_id == current_user.id
        ).first()

        if not student:
            raise HTTPException(
                status_code=404,
                detail="Student profile not found"
            )

        user_context = f"""
Current user role: student
Current student ID: {student.student_id}
Current student name: {student.name}

IMPORTANT SECURITY RULE:

The current student can access ONLY their own
student information.

If the student asks about another student,
do not provide that student's information.
"""

    # -------------------------------------------------
    # FACULTY CONTEXT
    # -------------------------------------------------

    elif current_user.role == "faculty":

        user_context = """
Current user role: faculty.

Faculty can ask questions about student academic
information.
"""

    # -------------------------------------------------
    # ADMIN CONTEXT
    # -------------------------------------------------

    elif current_user.role == "admin":

        user_context = """
Current user role: admin.

Admin can access authorized college information.
"""

    else:

        raise HTTPException(
            status_code=403,
            detail="AI Assistant access not allowed"
        )

    # -------------------------------------------------
    # CREATE AI ASSISTANT
    # -------------------------------------------------

    try:

        agent = create_ai_assistant(
            db,
            current_user
        )

        prompt = f"""
{user_context}

User question:
{question}

Instructions:

- Use database tools for student information.
- Never invent data.
- If information is not available,
  clearly say that it is not available.
- Give the answer in simple English.
- ALWAYS answer in English, even if the user
  asks in Hindi or Hinglish.
- Do not use Hindi script or Hindi words.
"""

        response = agent.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
        )

        # -------------------------------------------------
        # EXTRACT AI RESPONSE
        # -------------------------------------------------

        message = response["messages"][-1]
        content = message.content

        if isinstance(content, str):

            answer = content

        else:

            answer = ""

            for item in content:

                if (
                    isinstance(item, dict)
                    and item.get("type") == "text"
                ):
                    answer += item.get("text", "")

        return {
            "question": question,
            "answer": answer.strip()
        }

    except Exception as e:
       print(f"AI Assistant Error: {e}")

       raise HTTPException(
            status_code=500,
            detail="AI Assistant is temporarily unavailable. Please try again later."
        )