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


# ============================================================
# HELPER FUNCTION
# ============================================================

def _get_student(db: Session, student_id: str):
    """
    Find student using actual student ID like STU001.
    """
    return db.query(Student).filter(
        Student.student_id == student_id
    ).first()


# ============================================================
# STUDENT DATA FUNCTIONS
# ============================================================

def get_student_performance(db: Session, student_id: str):

    student = _get_student(db, student_id)

    if not student:
        return {
            "message": "Student not found."
        }

    records = db.query(Performance).filter(
        Performance.student_id == student_id
    ).all()

    if not records:
        return {
            "message": "Performance data is not available."
        }

    result = []

    for performance in records:

        subject = db.query(Subject).filter(
            Subject.id == performance.subject_id
        ).first()

        result.append({
            "student_id": student.student_id,
            "student_name": student.name,
            "subject_id": performance.subject_id,
            "subject_name": subject.name if subject else "Unknown",

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


def get_student_attendance(db: Session, student_id: str):

    student = _get_student(db, student_id)

    if not student:
        return {
            "message": "Student not found."
        }

    records = db.query(Attendance).filter(
        Attendance.student_id == student_id
    ).order_by(
        Attendance.date.desc()
    ).all()

    if not records:
        return {
            "message": "Attendance data is not available."
        }

    result = []

    for attendance in records:

        subject = db.query(Subject).filter(
            Subject.id == attendance.subject_id
        ).first()

        result.append({
            "student_id": student.student_id,
            "student_name": student.name,
            "subject_id": attendance.subject_id,
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


def get_student_marks(db: Session, student_id: str):

    student = _get_student(db, student_id)

    if not student:
        return {
            "message": "Student not found."
        }

    records = db.query(Marks).filter(
        Marks.student_id == student_id
    ).order_by(
        Marks.exam_date.desc()
    ).all()

    if not records:
        return {
            "message": "Marks data is not available."
        }

    result = []

    for marks in records:

        subject = db.query(Subject).filter(
            Subject.id == marks.subject_id
        ).first()

        result.append({
            "student_id": student.student_id,
            "student_name": student.name,
            "subject_id": marks.subject_id,
            "subject_name":
                subject.name if subject else "Unknown",

            "exam_type": marks.exam_type,

            "marks_obtained":
                marks.marks_obtained,

            "max_marks":
                marks.max_marks,

            "exam_date":
                str(marks.exam_date)
                if marks.exam_date
                else None
        })

    return {
        "student_id": student.student_id,
        "student_name": student.name,
        "marks": result
    }


def get_student_risk(db: Session, student_id: str):

    student = _get_student(db, student_id)

    if not student:
        return {
            "message": "Student not found."
        }

    records = db.query(StudentRisk).filter(
        StudentRisk.student_id == student_id
    ).all()

    if not records:
        return {
            "message": "Risk data is not available."
        }

    result = []

    for risk in records:

        subject = db.query(Subject).filter(
            Subject.id == risk.subject_id
        ).first()

        result.append({
            "student_id": student.student_id,
            "student_name": student.name,
            "subject_id": risk.subject_id,
            "subject_name":
                subject.name if subject else "Unknown",

            "risk_score": risk.risk_score,
            "risk_level": risk.risk_level,
            "risk_reason": risk.risk_reason
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

    student = _get_student(db, student_id)

    if not student:
        return {
            "message": "Student not found."
        }

    records = db.query(Recommendation).filter(
        Recommendation.student_id == student_id
    ).order_by(
        Recommendation.created_at.desc()
    ).all()

    if not records:
        return {
            "message": "Recommendations are not available."
        }

    result = []

    for recommendation in records:

        subject = db.query(Subject).filter(
            Subject.id == recommendation.subject_id
        ).first()

        result.append({
            "recommendation_id":
                recommendation.id,

            "student_id":
                student.student_id,

            "student_name":
                student.name,

            "subject_id":
                recommendation.subject_id,

            "subject_name":
                subject.name if subject else "Unknown",

            "recommendation_text":
                recommendation.recommendation_text,

            "recommendation_type":
                recommendation.recommendation_type,

            "priority":
                recommendation.priority,

            "created_at":
                str(recommendation.created_at)
        })

    return {
        "student_id": student.student_id,
        "student_name": student.name,
        "recommendations": result
    }


# ============================================================
# COLLEGE SUMMARY FUNCTIONS
# THESE ARE FOR FACULTY / ADMIN
# ============================================================

def get_total_students(db: Session):

    total = db.query(Student).count()

    return {
        "total_students": total
    }


def get_low_attendance_students(
    db: Session,
    threshold: float = 75
):

    performances = db.query(Performance).filter(
        Performance.attendance_percentage < threshold
    ).all()

    if not performances:
        return {
            "message": "No students found with low attendance."
        }

    result = []

    for performance in performances:

        student = _get_student(
            db,
            performance.student_id
        )

        subject = db.query(Subject).filter(
            Subject.id == performance.subject_id
        ).first()

        if student:

            result.append({
                "student_id":
                    student.student_id,

                "student_name":
                    student.name,

                "subject_name":
                    subject.name if subject
                    else "Unknown",

                "attendance_percentage":
                    performance.attendance_percentage
            })

    return {
        "threshold": threshold,
        "students": result
    }


def get_high_risk_students(db: Session):

    risk_records = db.query(StudentRisk).filter(
        StudentRisk.risk_level == "High"
    ).all()

    if not risk_records:
        return {
            "message": "No high-risk students found."
        }

    result = []

    for risk in risk_records:

        student = _get_student(
            db,
            risk.student_id
        )

        subject = db.query(Subject).filter(
            Subject.id == risk.subject_id
        ).first()

        if student:

            result.append({
                "student_id":
                    student.student_id,

                "student_name":
                    student.name,

                "subject_name":
                    subject.name if subject
                    else "Unknown",

                "risk_score":
                    risk.risk_score,

                "risk_level":
                    risk.risk_level,

                "risk_reason":
                    risk.risk_reason
            })

    return {
        "students": result
    }


def get_average_attendance(db: Session):

    performances = db.query(
        Performance
    ).all()

    if not performances:
        return {
            "message":
                "Performance data is not available."
        }

    total = sum(
        performance.attendance_percentage
        for performance in performances
    )

    average = total / len(performances)

    return {
        "average_attendance_percentage":
            round(average, 2),

        "records_used":
            len(performances)
    }


# ============================================================
# CREATE AI TOOLS
# ============================================================

def create_ai_tools(
    db: Session,
    current_user
):

    # ========================================================
    # STUDENT TOOLS
    # ========================================================

    if current_user.role == "student":

        student = db.query(Student).filter(
            Student.user_id == current_user.id
        ).first()

        if not student:
            return []

        student_id = student.student_id

        # ----------------------------------------------------
        # MY PERFORMANCE
        # ----------------------------------------------------

        @tool
        def my_performance():
            """
            Get the current student's academic performance.

            Includes:
            - Attendance percentage
            - Marks percentage
            - Assignment percentage
            - Overall percentage
            - Performance level
            """

            return get_student_performance(
                db,
                student_id
            )

        # ----------------------------------------------------
        # MY ATTENDANCE
        # ----------------------------------------------------

        @tool
        def my_attendance():
            """
            Get the current student's attendance records.
            """

            return get_student_attendance(
                db,
                student_id
            )

        # ----------------------------------------------------
        # MY MARKS
        # ----------------------------------------------------

        @tool
        def my_marks():
            """
            Get the current student's marks.
            """

            return get_student_marks(
                db,
                student_id
            )

        # ----------------------------------------------------
        # MY RISK
        # ----------------------------------------------------

        @tool
        def my_risk():
            """
            Get the current student's academic risk information.

            Includes:
            - Risk score
            - Risk level
            - Risk reason
            """

            return get_student_risk(
                db,
                student_id
            )

        # ----------------------------------------------------
        # MY RECOMMENDATIONS
        # ----------------------------------------------------

        @tool
        def my_recommendations():
            """
            Get personalized recommendations
            for the current student.
            """

            return get_student_recommendations(
                db,
                student_id
            )

        # ----------------------------------------------------
        # IMPORTANT:
        # STUDENT GETS ONLY OWN DATA TOOLS
        # ----------------------------------------------------

        return [
            my_performance,
            my_attendance,
            my_marks,
            my_risk,
            my_recommendations
        ]


    # ========================================================
    # FACULTY / ADMIN TOOLS
    # ========================================================

    elif current_user.role in ["faculty", "admin"]:

        # ----------------------------------------------------
        # TOTAL STUDENTS
        # ----------------------------------------------------

        @tool
        def total_students():
            """
            Get the total number of registered students
            in the college database.
            """

            return get_total_students(db)

        # ----------------------------------------------------
        # LOW ATTENDANCE STUDENTS
        # ----------------------------------------------------

        @tool
        def low_attendance_students(
            threshold: float = 75
        ):
            """
            Find students whose attendance is below
            the specified threshold.

            Default threshold is 75 percent.
            """

            return get_low_attendance_students(
                db,
                threshold
            )

        # ----------------------------------------------------
        # HIGH RISK STUDENTS
        # ----------------------------------------------------

        @tool
        def high_risk_students():
            """
            Get students who are currently marked
            as High Risk.
            """

            return get_high_risk_students(db)

        # ----------------------------------------------------
        # AVERAGE ATTENDANCE
        # ----------------------------------------------------

        @tool
        def average_attendance():
            """
            Get the average attendance percentage
            from available performance records.
            """

            return get_average_attendance(db)

        # ----------------------------------------------------
        # STUDENT PERFORMANCE
        # ----------------------------------------------------

        @tool
        def student_performance(
            student_id: str
        ):
            """
            Get academic performance of a student.

            Example student ID:
            STU001
            """

            return get_student_performance(
                db,
                student_id
            )

        # ----------------------------------------------------
        # STUDENT ATTENDANCE
        # ----------------------------------------------------

        @tool
        def student_attendance(
            student_id: str
        ):
            """
            Get attendance records of a student.

            Example student ID:
            STU001
            """

            return get_student_attendance(
                db,
                student_id
            )

        # ----------------------------------------------------
        # STUDENT MARKS
        # ----------------------------------------------------

        @tool
        def student_marks(
            student_id: str
        ):
            """
            Get marks of a student.

            Example student ID:
            STU001
            """

            return get_student_marks(
                db,
                student_id
            )

        # ----------------------------------------------------
        # STUDENT RISK
        # ----------------------------------------------------

        @tool
        def student_risk(
            student_id: str
        ):
            """
            Get academic risk information of a student.

            Example student ID:
            STU001
            """

            return get_student_risk(
                db,
                student_id
            )

        # ----------------------------------------------------
        # STUDENT RECOMMENDATIONS
        # ----------------------------------------------------

        @tool
        def student_recommendations(
            student_id: str
        ):
            """
            Get recommendations generated
            for a student.

            Example student ID:
            STU001
            """

            return get_student_recommendations(
                db,
                student_id
            )

        # ----------------------------------------------------
        # FACULTY / ADMIN GETS ALL AUTHORIZED TOOLS
        # ----------------------------------------------------

        return [
            total_students,
            low_attendance_students,
            high_risk_students,
            average_attendance,

            student_performance,
            student_attendance,
            student_marks,
            student_risk,
            student_recommendations
        ]


    # ========================================================
    # UNKNOWN ROLE
    # ========================================================

    return []