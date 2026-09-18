from sqlalchemy.orm import Session

from app.database.models import (
    Student,
    Performance,
    Attendance,
    Marks,
    StudentRisk,
    Recommendation,
    Subject
)

from langchain_core.tools import tool


# =========================================================
# Helper
# =========================================================

def _get_student(
    db: Session,
    student_id: str
):
    return db.query(Student).filter(
        Student.student_id == student_id
    ).first()


# =========================================================
# Database Functions
# =========================================================

def get_student_performance(
    db: Session,
    student_id: str
):
    """Get performance information of a student."""

    student = _get_student(db, student_id)

    if not student:
        return {"error": "Student not found"}

    performances = db.query(Performance).filter(
        Performance.student_id == student_id
    ).all()

    if not performances:
        return {
            "error": "Performance record not found"
        }

    result = []

    for performance in performances:

        subject = db.query(Subject).filter(
            Subject.id == performance.subject_id
        ).first()

        result.append({
            "subject_name":
                subject.name if subject else "Unknown",

            "attendance_percentage":
                performance.attendance_percentage,

            "marks_percentage":
                performance.marks_percentage,

            "assignment_percentage":
                performance.assignment_percentage,

            "overall_percentage":
                performance.overall_percentage,

            "performance_level":
                performance.performance_level
        })

    return {
        "student_id": student.student_id,
        "student_name": student.name,
        "performance": result
    }


def get_student_attendance(
    db: Session,
    student_id: str
):
    """Get attendance records of a student."""

    student = _get_student(db, student_id)

    if not student:
        return {"error": "Student not found"}

    attendance_records = db.query(Attendance).filter(
        Attendance.student_id == student_id
    ).all()

    if not attendance_records:
        return {
            "error": "Attendance record not found"
        }

    result = []

    for attendance in attendance_records:

        subject = db.query(Subject).filter(
            Subject.id == attendance.subject_id
        ).first()

        result.append({
            "subject_name":
                subject.name if subject else "Unknown",

            "date": str(attendance.date),

            "status": attendance.status
        })

    return {
        "student_id": student.student_id,
        "student_name": student.name,
        "attendance": result
    }


def get_student_marks(
    db: Session,
    student_id: str
):
    """Get marks and examination records of a student."""

    student = _get_student(db, student_id)

    if not student:
        return {"error": "Student not found"}

    marks_records = db.query(Marks).filter(
        Marks.student_id == student_id
    ).all()

    if not marks_records:
        return {
            "error": "Marks record not found"
        }

    result = []

    for marks in marks_records:

        subject = db.query(Subject).filter(
            Subject.id == marks.subject_id
        ).first()

        result.append({
            "subject_name":
                subject.name if subject else "Unknown",

            "exam_type":
                marks.exam_type,

            "marks_obtained":
                marks.marks_obtained,

            "max_marks":
                marks.max_marks,

            "exam_date":
                str(marks.exam_date)
                if marks.exam_date else None
        })

    return {
        "student_id": student.student_id,
        "student_name": student.name,
        "marks": result
    }


def get_student_risk(
    db: Session,
    student_id: str
):
    """Get academic risk information of a student."""

    student = _get_student(db, student_id)

    if not student:
        return {"error": "Student not found"}

    risk_records = db.query(StudentRisk).filter(
        StudentRisk.student_id == student_id
    ).all()

    if not risk_records:
        return {
            "error": "Risk record not found"
        }

    result = []

    for risk in risk_records:

        subject = db.query(Subject).filter(
            Subject.id == risk.subject_id
        ).first()

        result.append({
            "subject_name":
                subject.name if subject else "Unknown",

            "risk_score":
                risk.risk_score,

            "risk_level":
                risk.risk_level,

            "risk_reason":
                risk.risk_reason
        })

    return {
        "student_id": student.student_id,
        "student_name": student.name,
        "risk": result
    }


def get_student_recommendations(
    db: Session,
    student_id: str
):
    """Get personalized recommendations of a student."""

    student = _get_student(db, student_id)

    if not student:
        return {"error": "Student not found"}

    recommendations = db.query(
        Recommendation
    ).filter(
        Recommendation.student_id == student_id
    ).all()

    if not recommendations:
        return {
            "error": "Recommendation record not found"
        }

    result = []

    for recommendation in recommendations:

        subject = db.query(Subject).filter(
            Subject.id == recommendation.subject_id
        ).first()

        result.append({
            "subject_name":
                subject.name if subject else "Unknown",

            "recommendation_text":
                recommendation.recommendation_text,

            "recommendation_type":
                recommendation.recommendation_type,

            "priority":
                recommendation.priority
        })

    return {
        "student_id": student.student_id,
        "student_name": student.name,
        "recommendations": result
    }


# =========================================================
# AI Tools
# =========================================================

def create_ai_tools(
    db: Session,
    current_user
):

    # -----------------------------------------------------
    # STUDENT TOOLS
    # -----------------------------------------------------

    if current_user.role == "student":

        student = db.query(Student).filter(
            Student.user_id == current_user.id
        ).first()

        if not student:
            return []

        student_id = student.student_id

        @tool
        def my_performance():
            """
            Get the academic performance of the
            currently logged-in student.

            Includes attendance, marks, assignments,
            overall percentage and performance level.
            """
            return get_student_performance(
                db,
                student_id
            )

        @tool
        def my_attendance():
            """
            Get the attendance records of the
            currently logged-in student.
            """
            return get_student_attendance(
                db,
                student_id
            )

        @tool
        def my_marks():
            """
            Get the marks and examination records
            of the currently logged-in student.
            """
            return get_student_marks(
                db,
                student_id
            )

        @tool
        def my_risk():
            """
            Get the academic risk information of the
            currently logged-in student.
            """
            return get_student_risk(
                db,
                student_id
            )

        @tool
        def my_recommendations():
            """
            Get personalized recommendations of the
            currently logged-in student.
            """
            return get_student_recommendations(
                db,
                student_id
            )

        return [
            my_performance,
            my_attendance,
            my_marks,
            my_risk,
            my_recommendations
        ]


    # -----------------------------------------------------
    # FACULTY / ADMIN TOOLS
    # -----------------------------------------------------

    @tool
    def student_performance(student_id: str):
        """
        Get the academic performance of a student.

        Faculty and admin users can use this tool
        when they need student performance information.
        """
        return get_student_performance(
            db,
            student_id
        )


    @tool
    def student_attendance(student_id: str):
        """
        Get attendance records of a student.
        """
        return get_student_attendance(
            db,
            student_id
        )


    @tool
    def student_marks(student_id: str):
        """
        Get marks and examination records of a student.
        """
        return get_student_marks(
            db,
            student_id
        )


    @tool
    def student_risk(student_id: str):
        """
        Get academic risk information of a student.
        """
        return get_student_risk(
            db,
            student_id
        )


    @tool
    def student_recommendations(student_id: str):
        """
        Get personalized recommendations of a student.
        """
        return get_student_recommendations(
            db,
            student_id
        )


    return [
        student_performance,
        student_attendance,
        student_marks,
        student_risk,
        student_recommendations
    ]