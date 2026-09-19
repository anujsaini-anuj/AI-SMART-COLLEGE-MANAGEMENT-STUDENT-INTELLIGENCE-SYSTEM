from sqlalchemy.orm import Session

from app.database.models import (
    Student,
    Performance,
    Attendance,
    Marks,
    StudentRisk,
    Recommendation,
    Subject,
    Faculty,
    FacultySubject
)

from langchain_core.tools import tool


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def _get_student(db: Session, student_id: str):

    return db.query(Student).filter(
        Student.student_id == student_id
    ).first()


def _get_subject(db: Session, subject_id: int):

    return db.query(Subject).filter(
        Subject.id == subject_id
    ).first()


# ============================================================
# FACULTY SUBJECT AUTHORIZATION
# ============================================================

def faculty_has_subject_access(
    db: Session,
    faculty_user_id: int,
    subject_id: int
):
    """
    Check whether the logged-in faculty is assigned
    to the requested subject.
    """

    faculty = db.query(Faculty).filter(
        Faculty.user_id == faculty_user_id
    ).first()

    if not faculty:
        return False

    assignment = db.query(FacultySubject).filter(
        FacultySubject.faculty_id == faculty.id,
        FacultySubject.subject_id == subject_id
    ).first()

    return assignment is not None


# ============================================================
# CHECK STUDENT SUBJECT
# ============================================================

def student_has_subject(
    db: Session,
    student_id: str,
    subject_id: int
):
    """
    Check whether the student belongs to the subject.

    In the current database design, a student's academic
    records identify the subject through student_id + subject_id.
    """

    performance = db.query(Performance).filter(
        Performance.student_id == student_id,
        Performance.subject_id == subject_id
    ).first()

    if performance:
        return True

    attendance = db.query(Attendance).filter(
        Attendance.student_id == student_id,
        Attendance.subject_id == subject_id
    ).first()

    if attendance:
        return True

    marks = db.query(Marks).filter(
        Marks.student_id == student_id,
        Marks.subject_id == subject_id
    ).first()

    if marks:
        return True

    risk = db.query(StudentRisk).filter(
        StudentRisk.student_id == student_id,
        StudentRisk.subject_id == subject_id
    ).first()

    if risk:
        return True

    recommendation = db.query(Recommendation).filter(
        Recommendation.student_id == student_id,
        Recommendation.subject_id == subject_id
    ).first()

    if recommendation:
        return True

    return False


# ============================================================
# STUDENT PERFORMANCE
# ============================================================

def get_student_performance(
    db: Session,
    student_id: str,
    subject_id: int | None = None
):

    student = _get_student(db, student_id)

    if not student:
        return {
            "message": "Student not found."
        }

    query = db.query(Performance).filter(
        Performance.student_id == student_id
    )

    if subject_id is not None:
        query = query.filter(
            Performance.subject_id == subject_id
        )

    records = query.all()

    if not records:
        return {
            "message": "Performance data is not available."
        }

    result = []

    for performance in records:

        subject = _get_subject(
            db,
            performance.subject_id
        )

        result.append({
            "student_id":
                student.student_id,

            "student_name":
                student.name,

            "subject_id":
                performance.subject_id,

            "subject_name":
                subject.name if subject
                else "Unknown",

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
        "student_id":
            student.student_id,

        "student_name":
            student.name,

        "performance":
            result
    }


# ============================================================
# STUDENT ATTENDANCE
# ============================================================

def get_student_attendance(
    db: Session,
    student_id: str,
    subject_id: int | None = None
):

    student = _get_student(db, student_id)

    if not student:
        return {
            "message": "Student not found."
        }

    query = db.query(Attendance).filter(
        Attendance.student_id == student_id
    )

    if subject_id is not None:
        query = query.filter(
            Attendance.subject_id == subject_id
        )

    records = query.order_by(
        Attendance.date.desc()
    ).all()

    if not records:
        return {
            "message": "Attendance data is not available."
        }

    result = []

    for attendance in records:

        subject = _get_subject(
            db,
            attendance.subject_id
        )

        result.append({
            "student_id":
                student.student_id,

            "student_name":
                student.name,

            "subject_id":
                attendance.subject_id,

            "subject_name":
                subject.name if subject
                else "Unknown",

            "date":
                str(attendance.date),

            "status":
                attendance.status
        })

    return {
        "student_id":
            student.student_id,

        "student_name":
            student.name,

        "attendance":
            result
    }


# ============================================================
# STUDENT MARKS
# ============================================================

def get_student_marks(
    db: Session,
    student_id: str,
    subject_id: int | None = None
):

    student = _get_student(db, student_id)

    if not student:
        return {
            "message": "Student not found."
        }

    query = db.query(Marks).filter(
        Marks.student_id == student_id
    )

    if subject_id is not None:
        query = query.filter(
            Marks.subject_id == subject_id
        )

    records = query.order_by(
        Marks.exam_date.desc()
    ).all()

    if not records:
        return {
            "message": "Marks data is not available."
        }

    result = []

    for marks in records:

        subject = _get_subject(
            db,
            marks.subject_id
        )

        result.append({
            "student_id":
                student.student_id,

            "student_name":
                student.name,

            "subject_id":
                marks.subject_id,

            "subject_name":
                subject.name if subject
                else "Unknown",

            "exam_type":
                marks.exam_type,

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
        "student_id":
            student.student_id,

        "student_name":
            student.name,

        "marks":
            result
    }


# ============================================================
# STUDENT RISK
# ============================================================

def get_student_risk(
    db: Session,
    student_id: str,
    subject_id: int | None = None
):

    student = _get_student(db, student_id)

    if not student:
        return {
            "message": "Student not found."
        }

    query = db.query(StudentRisk).filter(
        StudentRisk.student_id == student_id
    )

    if subject_id is not None:
        query = query.filter(
            StudentRisk.subject_id == subject_id
        )

    records = query.all()

    if not records:
        return {
            "message": "Risk data is not available."
        }

    result = []

    for risk in records:

        subject = _get_subject(
            db,
            risk.subject_id
        )

        result.append({
            "student_id":
                student.student_id,

            "student_name":
                student.name,

            "subject_id":
                risk.subject_id,

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
        "student_id":
            student.student_id,

        "student_name":
            student.name,

        "risk":
            result
    }


# ============================================================
# STUDENT RECOMMENDATIONS
# ============================================================

def get_student_recommendations(
    db: Session,
    student_id: str,
    subject_id: int | None = None
):

    student = _get_student(db, student_id)

    if not student:
        return {
            "message": "Student not found."
        }

    query = db.query(Recommendation).filter(
        Recommendation.student_id == student_id
    )

    if subject_id is not None:
        query = query.filter(
            Recommendation.subject_id == subject_id
        )

    records = query.order_by(
        Recommendation.created_at.desc()
    ).all()

    if not records:
        return {
            "message": "Recommendations are not available."
        }

    result = []

    for recommendation in records:

        subject = _get_subject(
            db,
            recommendation.subject_id
        )

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
                subject.name if subject
                else "Unknown",

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
        "student_id":
            student.student_id,

        "student_name":
            student.name,

        "recommendations":
            result
    }


# ============================================================
# COLLEGE SUMMARY
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
            "message":
                "No students found with low attendance."
        }

    result = []

    for performance in performances:

        student = _get_student(
            db,
            performance.student_id
        )

        subject = _get_subject(
            db,
            performance.subject_id
        )

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
        "threshold":
            threshold,

        "students":
            result
    }


def get_high_risk_students(db: Session):

    risk_records = db.query(StudentRisk).filter(
        StudentRisk.risk_level == "High"
    ).all()

    if not risk_records:
        return {
            "message":
                "No high-risk students found."
        }

    result = []

    for risk in risk_records:

        student = _get_student(
            db,
            risk.student_id
        )

        subject = _get_subject(
            db,
            risk.subject_id
        )

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
        "students":
            result
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
    # STUDENT
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
            Get the current student's attendance.
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
            Get the current student's academic risk.
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
            Get the current student's recommendations.
            """

            return get_student_recommendations(
                db,
                student_id
            )

        # ----------------------------------------------------
        # STUDENT ONLY GETS OWN TOOLS
        # ----------------------------------------------------

        return [
            my_performance,
            my_attendance,
            my_marks,
            my_risk,
            my_recommendations
        ]


    # ========================================================
    # FACULTY / ADMIN
    # ========================================================

    elif current_user.role in ["faculty", "admin"]:

        # ====================================================
        # TOTAL STUDENTS
        # ====================================================

        @tool
        def total_students():
            """
            Get total registered students.
            """

            return get_total_students(db)

        # ====================================================
        # LOW ATTENDANCE
        # ====================================================

        @tool
        def low_attendance_students(
            threshold: float = 75
        ):
            """
            Get students with attendance below threshold.
            """

            return get_low_attendance_students(
                db,
                threshold
            )

        # ====================================================
        # HIGH RISK
        # ====================================================

        @tool
        def high_risk_students():
            """
            Get high-risk students.
            """

            return get_high_risk_students(db)

        # ====================================================
        # AVERAGE ATTENDANCE
        # ====================================================

        @tool
        def average_attendance():
            """
            Get average attendance.
            """

            return get_average_attendance(db)

        # ====================================================
        # STUDENT PERFORMANCE
        # ====================================================

        @tool
        def student_performance(
            student_id: str,
            subject_id: int
        ):
            """
            Get a student's performance for a subject.

            Faculty can only access subjects assigned
            to them.
            """

            if current_user.role == "faculty":

                allowed = faculty_has_subject_access(
                    db,
                    current_user.id,
                    subject_id
                )

                if not allowed:

                    return {
                        "error":
                            "Access denied. This subject is not assigned to you."
                    }

            student = _get_student(
                db,
                student_id
            )

            if not student:

                return {
                    "error":
                        "Student not found."
                }

            if not student_has_subject(
                db,
                student_id,
                subject_id
            ):

                return {
                    "error":
                        "This student does not have data for the requested subject."
                }

            return get_student_performance(
                db,
                student_id,
                subject_id
            )

        # ====================================================
        # STUDENT ATTENDANCE
        # ====================================================

        @tool
        def student_attendance(
            student_id: str,
            subject_id: int
        ):
            """
            Get a student's attendance for a subject.

            Faculty can only access subjects assigned
            to them.
            """

            if current_user.role == "faculty":

                allowed = faculty_has_subject_access(
                    db,
                    current_user.id,
                    subject_id
                )

                if not allowed:

                    return {
                        "error":
                            "Access denied. This subject is not assigned to you."
                    }

            student = _get_student(
                db,
                student_id
            )

            if not student:

                return {
                    "error":
                        "Student not found."
                }

            if not student_has_subject(
                db,
                student_id,
                subject_id
            ):

                return {
                    "error":
                        "This student does not have data for the requested subject."
                }

            return get_student_attendance(
                db,
                student_id,
                subject_id
            )

        # ====================================================
        # STUDENT MARKS
        # ====================================================

        @tool
        def student_marks(
            student_id: str,
            subject_id: int
        ):
            """
            Get a student's marks for a subject.

            Faculty can only access subjects assigned
            to them.
            """

            if current_user.role == "faculty":

                allowed = faculty_has_subject_access(
                    db,
                    current_user.id,
                    subject_id
                )

                if not allowed:

                    return {
                        "error":
                            "Access denied. This subject is not assigned to you."
                    }

            student = _get_student(
                db,
                student_id
            )

            if not student:

                return {
                    "error":
                        "Student not found."
                }

            if not student_has_subject(
                db,
                student_id,
                subject_id
            ):

                return {
                    "error":
                        "This student does not have data for the requested subject."
                }

            return get_student_marks(
                db,
                student_id,
                subject_id
            )

        # ====================================================
        # STUDENT RISK
        # ====================================================

        @tool
        def student_risk(
            student_id: str,
            subject_id: int
        ):
            """
            Get a student's risk information for a subject.

            Faculty can only access subjects assigned
            to them.
            """

            if current_user.role == "faculty":

                allowed = faculty_has_subject_access(
                    db,
                    current_user.id,
                    subject_id
                )

                if not allowed:

                    return {
                        "error":
                            "Access denied. This subject is not assigned to you."
                    }

            student = _get_student(
                db,
                student_id
            )

            if not student:

                return {
                    "error":
                        "Student not found."
                }

            if not student_has_subject(
                db,
                student_id,
                subject_id
            ):

                return {
                    "error":
                        "This student does not have data for the requested subject."
                }

            return get_student_risk(
                db,
                student_id,
                subject_id
            )

        # ====================================================
        # STUDENT RECOMMENDATIONS
        # ====================================================

        @tool
        def student_recommendations(
            student_id: str,
            subject_id: int
        ):
            """
            Get a student's recommendations for a subject.

            Faculty can only access subjects assigned
            to them.
            """

            if current_user.role == "faculty":

                allowed = faculty_has_subject_access(
                    db,
                    current_user.id,
                    subject_id
                )

                if not allowed:

                    return {
                        "error":
                            "Access denied. This subject is not assigned to you."
                    }

            student = _get_student(
                db,
                student_id
            )

            if not student:

                return {
                    "error":
                        "Student not found."
                }

            if not student_has_subject(
                db,
                student_id,
                subject_id
            ):

                return {
                    "error":
                        "This student does not have data for the requested subject."
                }

            return get_student_recommendations(
                db,
                student_id,
                subject_id
            )

        # ====================================================
        # FACULTY / ADMIN TOOLS
        # ====================================================

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