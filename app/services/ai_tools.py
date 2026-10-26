from sqlalchemy.orm import Session

from datetime import date, datetime

from app.database.models import (
    Student,
    Performance,
    Attendance,
    Marks,
    StudentRisk,
    Recommendation,
    Subject,
    Faculty,
    FacultySubject,
    Course,
    HOD,
    Accountant,
    Librarian,
    AdmissionOfficer,
    AdmissionApplication,
    FeeStructure,
    StudentFee,
    FeePayment,
    Book,
    BookCopy,
    BookIssue,
    LibraryFine

)

from sqlalchemy import func, or_, case

from langchain_core.tools import tool


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def _get_student(
    db: Session,
    student_id: str
):
    student_id = student_id.strip()

    return db.query(Student).filter(
        Student.student_id == student_id
    ).first()


def _get_subject(
    db: Session,
    subject_id: int
):
    return db.query(Subject).filter(
        Subject.id == subject_id
    ).first()


# ============================================================
# BULK LOOKUP HELPERS
# ============================================================

def _get_students_map(
    db: Session,
    student_ids
):
    """
    Load multiple students using ONE database query.

    Returns:
        {
            "STU001": Student object,
            "STU002": Student object
        }
    """

    student_ids = list(set(student_ids))

    if not student_ids:
        return {}

    students = db.query(Student).filter(
        Student.student_id.in_(student_ids)
    ).all()

    return {
        student.student_id: student
        for student in students
    }


def _get_subjects_map(
    db: Session,
    subject_ids
):
    """
    Load multiple subjects using ONE database query.

    Returns:
        {
            1: Subject object,
            2: Subject object
        }
    """

    subject_ids = list(set(subject_ids))

    if not subject_ids:
        return {}

    subjects = db.query(Subject).filter(
        Subject.id.in_(subject_ids)
    ).all()

    return {
        subject.id: subject
        for subject in subjects
    }



# ============================================================
# STUDENT LOOKUP - ROLE-BASED ACCESS CONTROL
# ============================================================


def find_student_by_name(
    db: Session,
    student_name: str,
    current_user
):
    """
    Admin:
        Can search all active students.

    Faculty:
        Can search only active students belonging to
        their department and an assigned subject's
        course and semester.

    Other roles:
        Access denied.
    """

    if not student_name or not student_name.strip():
        return {
            "error": "Student name cannot be empty."
        }

    student_name = student_name.strip()

    # Treat SQL LIKE wildcard characters as literal input.
    escaped_name = (
        student_name
        .replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )

    search_pattern = f"%{escaped_name}%"

    # --------------------------------------------------------
    # ADMIN: COLLEGE-WIDE SEARCH
    # --------------------------------------------------------

    if current_user.role == "admin":

        students = (
            db.query(Student)
            .filter(
                Student.is_active.is_(True),
                Student.name.ilike(
                    search_pattern,
                    escape="\\"
                )
            )
            .order_by(Student.name.asc())
            .limit(20)
            .all()
        )

    # --------------------------------------------------------
    # FACULTY: ASSIGNED ACADEMIC SCOPE ONLY
    # --------------------------------------------------------

    elif current_user.role == "faculty":

        faculty = (
            db.query(Faculty)
            .filter(
                Faculty.user_id == current_user.id
            )
            .first()
        )

        if not faculty:
            return {
                "error": "Access denied. Faculty profile not found."
            }

        students = (
            db.query(Student)
            .join(
                Subject,
                (Student.course_id == Subject.course_id)
                & (Student.semester == Subject.semester)
            )
            .join(
                Course,
                Course.id == Student.course_id
            )
            .join(
                FacultySubject,
                FacultySubject.subject_id == Subject.id
            )
            .filter(
                FacultySubject.faculty_id == faculty.id,
                Student.is_active.is_(True),
                Student.department_id == faculty.department_id,
                Course.department_id == faculty.department_id,
                Student.name.ilike(
                    search_pattern,
                    escape="\\"
                )
            )
            .distinct()
            .order_by(Student.name.asc())
            .limit(20)
            .all()
        )

    else:
        return {
            "error": "Access denied."
        }

    # --------------------------------------------------------
    # HANDLE RESULTS
    # --------------------------------------------------------

    if not students:
        return {
            "error": (
                "Student not found in your authorized academic scope."
                if current_user.role == "faculty"
                else "Student not found."
            )
        }

    if len(students) > 1:
        return {
            "error": (
                "Multiple students found. "
                "Please provide a more specific name."
            ),
            "students": [
                {
                    "student_id": student.student_id,
                    "student_name": student.name
                }
                for student in students
            ]
        }

    student = students[0]

    return {
        "student_id": student.student_id,
        "student_name": student.name
    }

# ============================================================
# GET FACULTY ASSIGNED SUBJECT IDS
# ============================================================

def get_faculty_subject_ids(
    db: Session,
    faculty_user_id: int
):
    """
    Get subject IDs assigned to the logged-in faculty.
    """

    faculty = db.query(Faculty).filter(
        Faculty.user_id == faculty_user_id
    ).first()

    if not faculty:
        return []

    assignments = db.query(FacultySubject).filter(
        FacultySubject.faculty_id == faculty.id
    ).all()

    return [
        assignment.subject_id
        for assignment in assignments
    ]


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
# SUBJECT LOOKUP
# ============================================================

def find_subject_by_name(
    db: Session,
    subject_name: str
):
    """
    Find a subject using subject name or subject code.
    """

    subject_name = subject_name.strip()

    if not subject_name:
        return {
            "error": "Subject name cannot be empty."
        }

    # First search by subject name
    subject = db.query(Subject).filter(
        Subject.name.ilike(subject_name)
    ).first()

    # If not found, search by subject code
    if not subject:
        subject = db.query(Subject).filter(
            Subject.code.ilike(subject_name)
        ).first()

    if not subject:
        return {
            "error": "Subject not found."
        }

    return {
        "subject_id": subject.id,
        "subject_name": subject.name,
        "subject_code": subject.code
    }




# ============================================================
# FACULTY-STUDENT-SUBJECT AUTHORIZATION
# ============================================================
def get_faculty_student_subject_ids(
    db: Session,
    faculty_user_id: int,
    student: Student
) -> list[int]:

    faculty = (
        db.query(Faculty)
        .filter(Faculty.user_id == faculty_user_id)
        .first()
    )

    if not faculty or not student.is_active:
        return []

    if faculty.department_id != student.department_id:
        return []

    rows = (
        db.query(Subject.id)
        .join(
            FacultySubject,
            FacultySubject.subject_id == Subject.id
        )
        .join(
            Course,
            Course.id == Subject.course_id
        )
        .filter(
            FacultySubject.faculty_id == faculty.id,
            Subject.course_id == student.course_id,
            Subject.semester == student.semester,
            Course.department_id == faculty.department_id,
            Course.department_id == student.department_id
        )
        .distinct()
        .all()
    )

    return [row[0] for row in rows]

def faculty_can_access_student_subject(
    db: Session,
    faculty_user_id: int,
    student_id: str,
    subject_id: int
) -> bool:
    """
    Verify faculty access to a specific student's subject data.
    """

    student = _get_student(db, student_id)

    if not student or not student.is_active:
        return False

    allowed_subject_ids = get_faculty_student_subject_ids(
        db=db,
        faculty_user_id=faculty_user_id,
        student=student
    )

    return subject_id in allowed_subject_ids


# ============================================================
# CHECK STUDENT SUBJECT
# ============================================================

def student_has_subject(
    db: Session,
    student_id: str,
    subject_id: int
) -> bool:
    """Check that an active student belongs to the
    subject's course, semester and department."""

    student = _get_student(db, student_id)
    subject = _get_subject(db, subject_id)

    if not student or not student.is_active or not subject:
        return False

    course = (
        db.query(Course)
        .filter(Course.id == subject.course_id)
        .first()
    )

    if not course:
        return False

    return (
        student.course_id == subject.course_id
        and student.semester == subject.semester
        and student.department_id == course.department_id
    )

# ============================================================
# STUDENT PERFORMANCE
# ============================================================

def get_student_performance(
    db: Session,
    student_id: str,
    subject_id: int | None = None,
    allowed_subject_ids: list[int] | None = None
):

    student = _get_student(
        db,
        student_id
    )

    if not student or not student.is_active:
        return {
            "message": "Active student not found."
        }

    query = db.query(Performance).filter(
        Performance.student_id == student_id
    )

    if subject_id is not None:

        query = query.filter(
            Performance.subject_id == subject_id
        )

    elif allowed_subject_ids is not None:

        if not allowed_subject_ids:
            return {
                "message": "No subjects assigned to this faculty."
            }

        query = query.filter(
            Performance.subject_id.in_(allowed_subject_ids)
        )

    records = query.all()

    if not records:
        return {
            "message": "Performance data is not available."
        }

    # --------------------------------------------------------
    # LOAD ALL SUBJECTS IN ONE QUERY
    # --------------------------------------------------------

    subject_ids = [
        performance.subject_id
        for performance in records
    ]

    subjects_by_id = _get_subjects_map(
        db,
        subject_ids
    )

    # --------------------------------------------------------
    # BUILD RESULT
    # --------------------------------------------------------

    result = []

    for performance in records:

        subject = subjects_by_id.get(
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
                (
                    subject.name
                    if subject
                    else "Unknown"
                ),

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
    subject_id: int | None = None,
    allowed_subject_ids: list[int] | None = None
):
    student = _get_student(
        db,
        student_id
    )

    if not student or not student.is_active:
        return {
            "message": "Active student not found."
        }

        

    query = db.query(Attendance).filter(
        Attendance.student_id == student_id
    )

    # Specific subject
    if subject_id is not None:

        query = query.filter(
            Attendance.subject_id == subject_id
        )

    # Faculty overall query
    elif allowed_subject_ids is not None:

        if not allowed_subject_ids:
            return {
                "message": "No subjects assigned to this faculty."
            }

        query = query.filter(
            Attendance.subject_id.in_(allowed_subject_ids)
        )

    records = query.order_by(
        Attendance.date.desc()
    ).all()

    if not records:
        return {
            "message": "Attendance data is not available."
        }

    # --------------------------------------------------------
    # LOAD ALL SUBJECTS IN ONE QUERY
    # --------------------------------------------------------

    subject_ids = [
        attendance.subject_id
        for attendance in records
    ]

    subjects_by_id = _get_subjects_map(
        db,
        subject_ids
    )

    # --------------------------------------------------------
    # BUILD RESULT
    # --------------------------------------------------------

    result = []

    for attendance in records:

        subject = subjects_by_id.get(
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
                (
                    subject.name
                    if subject
                    else "Unknown"
                ),

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
    subject_id: int | None = None,
    allowed_subject_ids: list[int] | None = None
):
    student = _get_student(
        db,
        student_id
    )

    if not student or not student.is_active:
        return {
            "message": "Active student not found."
        }

    
    query = db.query(Marks).filter(
        Marks.student_id == student_id
    )

    # Specific subject
    if subject_id is not None:

        query = query.filter(
            Marks.subject_id == subject_id
        )

    # Faculty overall query
    elif allowed_subject_ids is not None:

        if not allowed_subject_ids:
            return {
                "message": "No subjects assigned to this faculty."
            }

        query = query.filter(
            Marks.subject_id.in_(allowed_subject_ids)
        )

    records = query.order_by(
        Marks.exam_date.desc()
    ).all()

    if not records:
        return {
            "message": "Marks data is not available."
        }

    # --------------------------------------------------------
    # LOAD ALL SUBJECTS IN ONE QUERY
    # --------------------------------------------------------

    subject_ids = [
        marks.subject_id
        for marks in records
    ]

    subjects_by_id = _get_subjects_map(
        db,
        subject_ids
    )

    # --------------------------------------------------------
    # BUILD RESULT
    # --------------------------------------------------------

    result = []

    for marks in records:

        subject = subjects_by_id.get(
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
                (
                    subject.name
                    if subject
                    else "Unknown"
                ),

            "exam_type":
                marks.exam_type,

            "marks_obtained":
                marks.marks_obtained,

            "max_marks":
                marks.max_marks,

            "exam_date":
                (
                    str(marks.exam_date)
                    if marks.exam_date
                    else None
                )
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
    subject_id: int | None = None,
    allowed_subject_ids: list[int] | None = None
):

    student = _get_student(
        db,
        student_id
    )

    if not student or not student.is_active:
        return {
            "message": "Active student not found."
        }

   
    query = db.query(StudentRisk).filter(
        StudentRisk.student_id == student_id
    )

    # Specific subject
    if subject_id is not None:

        query = query.filter(
            StudentRisk.subject_id == subject_id
        )

    # Faculty overall query
    elif allowed_subject_ids is not None:

        if not allowed_subject_ids:
            return {
                "message": "No subjects assigned to this faculty."
            }

        query = query.filter(
            StudentRisk.subject_id.in_(allowed_subject_ids)
        )

    records = query.all()

    if not records:
        return {
            "message": "Risk data is not available."
        }

    # --------------------------------------------------------
    # LOAD ALL SUBJECTS IN ONE QUERY
    # --------------------------------------------------------

    subject_ids = [
        risk.subject_id
        for risk in records
    ]

    subjects_by_id = _get_subjects_map(
        db,
        subject_ids
    )

    # --------------------------------------------------------
    # BUILD RESULT
    # --------------------------------------------------------

    result = []

    for risk in records:

        subject = subjects_by_id.get(
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
                (
                    subject.name
                    if subject
                    else "Unknown"
                ),

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
    subject_id: int | None = None,
    allowed_subject_ids: list[int] | None = None
):
    student = _get_student(
        db,
        student_id
    )

    if not student or not student.is_active:
        return {
            "message": "Active student not found."
        }


    query = db.query(Recommendation).filter(
        Recommendation.student_id == student_id
    )

    # Specific subject
    if subject_id is not None:

        query = query.filter(
            Recommendation.subject_id == subject_id
        )

    # Faculty overall query
    elif allowed_subject_ids is not None:

        if not allowed_subject_ids:
            return {
                "message": "No subjects assigned to this faculty."
            }

        query = query.filter(
            Recommendation.subject_id.in_(allowed_subject_ids)
        )

    records = query.order_by(
        Recommendation.created_at.desc()
    ).all()

    if not records:
        return {
            "message": "Recommendations are not available."
        }

    # --------------------------------------------------------
    # LOAD ALL SUBJECTS IN ONE QUERY
    # --------------------------------------------------------

    subject_ids = [
        recommendation.subject_id
        for recommendation in records
    ]

    subjects_by_id = _get_subjects_map(
        db,
        subject_ids
    )

    # --------------------------------------------------------
    # BUILD RESULT
    # --------------------------------------------------------

    result = []

    for recommendation in records:

        subject = subjects_by_id.get(
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
                (
                    subject.name
                    if subject
                    else "Unknown"
                ),

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


def get_total_students(
    db: Session,
    current_user
):
    """
    Admin:
        Count all active students in the college.

    Faculty:
        Count active students belonging to courses and
        semesters where the faculty has assigned subjects.

    The count does not depend on Performance records.
    """

    # ADMIN: college-wide count
    if current_user.role == "admin":
        total = (
            db.query(Student)
            .filter(Student.is_active.is_(True))
            .count()
        )

        return {"total_students": total}

    # Only admin and faculty are supported here.
    if current_user.role != "faculty":
        return {"error": "Access denied."}

    faculty = (
        db.query(Faculty)
        .filter(Faculty.user_id == current_user.id)
        .first()
    )

    if not faculty:
        return {"error": "Faculty profile not found."}

    # FACULTY: count students in the faculty's
    # authorized course and semester scope.
    total = (
        db.query(Student.id)
        .join(
            Subject,
            (Student.course_id == Subject.course_id)
            & (Student.semester == Subject.semester)
        )
        .join(
            Course,
            Course.id == Student.course_id
        )
        .join(
            FacultySubject,
            FacultySubject.subject_id == Subject.id
        )
        .filter(
            FacultySubject.faculty_id == faculty.id,
            Student.is_active.is_(True),
            Student.department_id == faculty.department_id,
            Student.department_id == Course.department_id,
            Course.department_id == faculty.department_id
        )
        .distinct()
        .count()
    )

    return {"total_students": total}

    
# ============================================================
# LOW ATTENDANCE STUDENTS
# ============================================================


def get_low_attendance_students(
    db: Session,
    current_user,
    threshold: float = 75
):
    if threshold < 0 or threshold > 100:
        return {
            "error": "Threshold must be between 0 and 100."
        }

    query = (
        db.query(Performance)
        .join(
            Student,
            Student.student_id == Performance.student_id
        )
        .join(
            Subject,
            Subject.id == Performance.subject_id
        )
        .join(
            Course,
            Course.id == Subject.course_id
        )
        .filter(
            Performance.attendance_percentage < threshold,
            Student.is_active.is_(True),
            Student.course_id == Subject.course_id,
            Student.semester == Subject.semester,
            Student.department_id == Course.department_id
        )
    )

    if current_user.role == "faculty":
        faculty = db.query(Faculty).filter(
            Faculty.user_id == current_user.id
        ).first()

        if not faculty:
            return {"error": "Faculty profile not found."}

        query = query.join(
            FacultySubject,
            FacultySubject.subject_id == Subject.id
        ).filter(
            FacultySubject.faculty_id == faculty.id,
            Student.department_id == faculty.department_id,
            Course.department_id == faculty.department_id
        )

    elif current_user.role != "admin":
        return {"error": "Access denied."}

    performances = query.all()

    if not performances:
        return {
            "threshold": threshold,
            "students": []
        }

    students_by_id = _get_students_map(
        db,
        [p.student_id for p in performances]
    )

    subjects_by_id = _get_subjects_map(
        db,
        [p.subject_id for p in performances]
    )

    result = []

    for performance in performances:
        student = students_by_id.get(performance.student_id)
        subject = subjects_by_id.get(performance.subject_id)

        if not student or not subject:
            continue

        result.append({
            "student_id": student.student_id,
            "student_name": student.name,
            "subject_name": subject.name,
            "attendance_percentage": performance.attendance_percentage
        })

    return {
        "threshold": threshold,
        "students": result
    }


# ============================================================
# HIGH RISK STUDENTS
# ============================================================


def get_high_risk_students(
    db: Session,
    current_user
):
    query = (
        db.query(StudentRisk)
        .join(
            Student,
            Student.student_id == StudentRisk.student_id
        )
        .join(
            Subject,
            Subject.id == StudentRisk.subject_id
        )
        .join(
            Course,
            Course.id == Subject.course_id
        )
        .filter(
            StudentRisk.risk_level == "High",
            Student.is_active.is_(True),
            Student.course_id == Subject.course_id,
            Student.semester == Subject.semester,
            Student.department_id == Course.department_id
        )
    )

    if current_user.role == "faculty":
        faculty = db.query(Faculty).filter(
            Faculty.user_id == current_user.id
        ).first()

        if not faculty:
            return {"error": "Faculty profile not found."}

        query = query.join(
            FacultySubject,
            FacultySubject.subject_id == Subject.id
        ).filter(
            FacultySubject.faculty_id == faculty.id,
            Student.department_id == faculty.department_id,
            Course.department_id == faculty.department_id
        )

    elif current_user.role != "admin":
        return {"error": "Access denied."}

    risk_records = query.all()

    if not risk_records:
        return {"students": []}

    students_by_id = _get_students_map(
        db,
        [r.student_id for r in risk_records]
    )

    subjects_by_id = _get_subjects_map(
        db,
        [r.subject_id for r in risk_records]
    )

    result = []

    for risk in risk_records:
        student = students_by_id.get(risk.student_id)
        subject = subjects_by_id.get(risk.subject_id)

        if not student or not subject:
            continue

        result.append({
            "student_id": student.student_id,
            "student_name": student.name,
            "subject_name": subject.name,
            "risk_score": risk.risk_score,
            "risk_level": risk.risk_level,
            "risk_reason": risk.risk_reason
        })

    return {"students": result}



def get_average_attendance(
    db: Session,
    current_user
):
    query = (
        db.query(Performance)
        .join(
            Student,
            Student.student_id == Performance.student_id
        )
        .join(
            Subject,
            Subject.id == Performance.subject_id
        )
        .join(
            Course,
            Course.id == Subject.course_id
        )
        .filter(
            Student.is_active.is_(True),
            Student.course_id == Subject.course_id,
            Student.semester == Subject.semester,
            Student.department_id == Course.department_id
        )
    )

    if current_user.role == "faculty":
        faculty = db.query(Faculty).filter(
            Faculty.user_id == current_user.id
        ).first()

        if not faculty:
            return {"error": "Faculty profile not found."}

        query = query.join(
            FacultySubject,
            FacultySubject.subject_id == Subject.id
        ).filter(
            FacultySubject.faculty_id == faculty.id,
            Student.department_id == faculty.department_id,
            Course.department_id == faculty.department_id
        )

    elif current_user.role != "admin":
        return {"error": "Access denied."}

    performances = query.all()

    if not performances:
        return {
            "average_attendance_percentage": None,
            "records_used": 0
        }

    total = sum(
        float(p.attendance_percentage or 0)
        for p in performances
    )

    return {
        "average_attendance_percentage": round(
            total / len(performances), 2
        ),
        "records_used": len(performances)
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
            Student.user_id == current_user.id,
            Student.is_active.is_(True)
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
        # STUDENT LOOKUP TOOL
        # ====================================================

        @tool
        def find_student(student_name: str):
            """
            Find a student by name.

            Admin can search all students.
            Faculty can search only within their
            authorized department, course and semester.
            """

            return find_student_by_name(
                db=db,
                student_name=student_name,
                current_user=current_user
            )



        # ====================================================
        # SUBJECT LOOKUP
        # ====================================================

        @tool
        def find_subject(
            subject_name: str
        ):
            """
            Find a subject using subject name or subject code.

            Faculty can access only assigned subjects.
            Admin can access all subjects.
            """

            subject_name = subject_name.strip()

            if not subject_name:
                return {
                    "error":
                        "Subject name cannot be empty."
                }

            # ------------------------------------------------
            # FACULTY
            # ------------------------------------------------
            if current_user.role == "faculty":

                faculty = db.query(Faculty).filter(
                    Faculty.user_id == current_user.id
                ).first()

                if not faculty:
                    return {
                        "error": "Faculty profile not found."
                    }

                subject = (
                    db.query(Subject)
                    .join(
                        FacultySubject,
                        FacultySubject.subject_id == Subject.id
                    )
                    .filter(
                        FacultySubject.faculty_id == faculty.id,
                        (
                            Subject.name.ilike(subject_name)
                            | Subject.code.ilike(subject_name)
                        )
                    )
                    .first()
                )

                if not subject:
                    return {
                        "error": (
                            "Subject not found in your assigned subjects."
                        )
                    }

                return {
                    "subject_id": subject.id,
                    "subject_name": subject.name,
                    "subject_code": subject.code
                }
            # ------------------------------------------------
            # ADMIN
            # ------------------------------------------------

            return find_subject_by_name(
                db,
                subject_name
            )

        # ====================================================
        # TOTAL STUDENTS
        # ====================================================

        @tool
        def total_students():
            """
            Get total students.

            Admin gets college-wide count.
            Faculty gets count limited to assigned subjects.
            """

            return get_total_students(
                db,
                current_user
            )

        # ====================================================
        # LOW ATTENDANCE
        # ====================================================

        @tool
        def low_attendance_students(
            threshold: float = 75
        ):
            """
            Get students with attendance below threshold.

            Admin gets college-wide data.
            Faculty gets only assigned-subject data.
            """

            return get_low_attendance_students(
                db,
                current_user,
                threshold
            )

        # ====================================================
        # HIGH RISK
        # ====================================================

        @tool
        def high_risk_students():
            """
            Get high-risk students.

            Admin gets college-wide data.
            Faculty gets only assigned-subject data.
            """

            return get_high_risk_students(
                db,
                current_user
            )

        # ====================================================
        # AVERAGE ATTENDANCE
        # ====================================================

        @tool
        def average_attendance():
            """
            Get average attendance.

            Admin gets college-wide average.
            Faculty gets average for assigned subjects.
            """

            return get_average_attendance(
                db,
                current_user
            )

        # ====================================================
        # STUDENT PERFORMANCE
        # ====================================================

        @tool
        def student_performance(
            student_id: str,
            subject_id: int | None = None
        ):
            """
            Get a student's performance.

            Admin:
            - Can access all subjects.

            Faculty:
            - Can access only assigned subjects.
            - If subject_id is not provided, only assigned
              subject data is returned.
            """

            student_id = student_id.strip()

            allowed_subject_ids = None

            # ------------------------------------------------
            # FACULTY AUTHORIZATION
            # ------------------------------------------------

            if current_user.role == "faculty":

                if subject_id is not None:

                    allowed = faculty_can_access_student_subject(
                        db=db,
                        faculty_user_id=current_user.id,
                        student_id=student_id,
                        subject_id=subject_id
                    )

                    if not allowed:
                        return {
                            "error": (
                                "Access denied. You are not authorized "
                                "to access this student's subject data."
                            )
                        }

                else:

                    student = _get_student(
                        db,
                        student_id
                    )

                    if not student or not student.is_active:
                        return {
                            "error": "Active student not found."
                        }
                  

                    allowed_subject_ids = get_faculty_student_subject_ids(
                        db=db,
                        faculty_user_id=current_user.id,
                        student=student
                    )

                    if not allowed_subject_ids:
                        return {
                            "error": (
                                "Access denied. No authorized subjects "
                                "are available for this student."
                            )
                        }

            # ------------------------------------------------
            # STUDENT VALIDATION
            # ------------------------------------------------

            student = _get_student(
                db,
                student_id
            )

            if not student:
                return {
                    "error":
                        "Student not found."
                }

            # ------------------------------------------------
            # SUBJECT VALIDATION
            # ------------------------------------------------

            if subject_id is not None:

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
                subject_id,
                allowed_subject_ids
            )

        # ====================================================
        # STUDENT ATTENDANCE
        # ====================================================

        @tool
        def student_attendance(
            student_id: str,
            subject_id: int | None = None
        ):
            """
            Get a student's attendance.

            Admin:
            - Can access all subjects.

            Faculty:
            - Can access only assigned subjects.
            - If subject_id is not provided, only attendance
              from assigned subjects is returned.
            """

            student_id = student_id.strip()

            allowed_subject_ids = None

            # ------------------------------------------------
            # FACULTY AUTHORIZATION
            # ------------------------------------------------

            if current_user.role == "faculty":

                if subject_id is not None:

                    allowed = faculty_can_access_student_subject(
                        db=db,
                        faculty_user_id=current_user.id,
                        student_id=student_id,
                        subject_id=subject_id
                    )

                    if not allowed:
                        return {
                            "error": (
                                "Access denied. You are not authorized "
                                "to access this student's subject data."
                            )
                        }

                else:
                    student = _get_student(
                        db,
                        student_id
                    )

                    if not student or not student.is_active:
                        return {
                            "error": "Active student not found."
                        }

                    allowed_subject_ids = get_faculty_student_subject_ids(
                        db=db,
                        faculty_user_id=current_user.id,
                        student=student
                    )

                    if not allowed_subject_ids:
                        return {
                            "error": (
                                "Access denied. No authorized subjects "
                                "are available for this student."
                            )
                        }

            # ------------------------------------------------
            # STUDENT VALIDATION
            # ------------------------------------------------

            student = _get_student(
                db,
                student_id
            )

            if not student:
                return {
                    "error":
                        "Student not found."
                }

            # ------------------------------------------------
            # SUBJECT VALIDATION
            # ------------------------------------------------

            if subject_id is not None:

                if not student_has_subject(
                    db,
                    student_id,
                    subject_id
                ):
                    return {
                        "error":
                            "This student does not have data for the requested subject."
                    }

            # ------------------------------------------------
            # GET ATTENDANCE
            # ------------------------------------------------

            attendance_data = get_student_attendance(
                db,
                student_id,
                subject_id,
                allowed_subject_ids
            )

            # ------------------------------------------------
            # CALCULATE SUMMARY
            # ------------------------------------------------

            if "attendance" in attendance_data:

                records = attendance_data["attendance"]

                total_classes = len(records)

                present_classes = sum(
                    1
                    for record in records
                    if record["status"].lower() == "present"
                )

                attendance_percentage = (
                    present_classes /
                    total_classes *
                    100
                    if total_classes > 0
                    else 0
                )

                attendance_data["summary"] = {
                    "total_classes":
                        total_classes,

                    "present_classes":
                        present_classes,

                    "absent_classes":
                        total_classes - present_classes,

                    "attendance_percentage":
                        round(
                            attendance_percentage,
                            2
                        )
                }

            return attendance_data

        # ====================================================
        # STUDENT MARKS
        # ====================================================

        @tool
        def student_marks(
            student_id: str,
            subject_id: int | None = None
        ):
            """
            Get a student's marks.

            Admin:
            - Can access all subjects.

            Faculty:
            - Can access only assigned subjects.
            - If subject_id is not provided, only assigned
              subject data is returned.
            """

            student_id = student_id.strip()

            allowed_subject_ids = None

            # ------------------------------------------------
            # FACULTY AUTHORIZATION
            # ------------------------------------------------

            if current_user.role == "faculty":

                if subject_id is not None:

                    allowed = faculty_can_access_student_subject(
                        db=db,
                        faculty_user_id=current_user.id,
                        student_id=student_id,
                        subject_id=subject_id
                    )

                    if not allowed:
                        return {
                            "error": (
                                "Access denied. You are not authorized "
                                "to access this student's subject data."
                            )
                        }

                else:

                    student = _get_student(
                        db,
                        student_id
                    )

                    if not student or not student.is_active:
                        return {
                            "error": "Active student not found."
                        }
                                        
                    allowed_subject_ids = get_faculty_student_subject_ids(
                        db=db,
                        faculty_user_id=current_user.id,
                        student=student
                    )

                    if not allowed_subject_ids:
                        return {
                            "error": (
                                "Access denied. No authorized subjects "
                                "are available for this student."
                            )
                        }

            # ------------------------------------------------
            # STUDENT VALIDATION
            # ------------------------------------------------

            student = _get_student(
                db,
                student_id
            )

            if not student:
                return {
                    "error":
                        "Student not found."
                }

            # ------------------------------------------------
            # SUBJECT VALIDATION
            # ------------------------------------------------

            if subject_id is not None:

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
                subject_id,
                allowed_subject_ids
            )

        # ====================================================
        # STUDENT RISK
        # ====================================================

        @tool
        def student_risk(
            student_id: str,
            subject_id: int | None = None
        ):
            """
            Get a student's risk information.

            Admin:
            - Can access all subjects.

            Faculty:
            - Can access only assigned subjects.
            - If subject_id is not provided, only assigned
              subject data is returned.
            """

            student_id = student_id.strip()

            allowed_subject_ids = None

            # ------------------------------------------------
            # FACULTY AUTHORIZATION
            # ------------------------------------------------

            if current_user.role == "faculty":


                if subject_id is not None:
                    allowed = faculty_can_access_student_subject(
                        db=db,
                        faculty_user_id=current_user.id,
                        student_id=student_id,
                        subject_id=subject_id
                    )

                    if not allowed:
                        return {
                            "error": (
                                "Access denied. You are not authorized "
                                "to access this student's subject data."
                            )
                        }

               
                else:
                    student = _get_student(
                        db,
                        student_id
                    )

                    if not student or not student.is_active:
                        return {
                            "error": "Active student not found."
                        }

                    allowed_subject_ids = get_faculty_student_subject_ids(
                        db=db,
                        faculty_user_id=current_user.id,
                        student=student
                    )

                    if not allowed_subject_ids:
                        return {
                            "error": (
                                "Access denied. No authorized subjects "
                                "are available for this student."
                            )
                        }

            # ------------------------------------------------
            # STUDENT VALIDATION
            # ------------------------------------------------

            student = _get_student(
                db,
                student_id
            )

            if not student:
                return {
                    "error":
                        "Student not found."
                }

            # ------------------------------------------------
            # SUBJECT VALIDATION
            # ------------------------------------------------

            if subject_id is not None:

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
                subject_id,
                allowed_subject_ids
            )

        # ====================================================
        # STUDENT RECOMMENDATIONS
        # ====================================================

        @tool
        def student_recommendations(
            student_id: str,
            subject_id: int | None = None
        ):
            """
            Get a student's recommendations.

            Admin:
            - Can access all subjects.

            Faculty:
            - Can access only assigned subjects.
            - If subject_id is not provided, only assigned
              subject data is returned.
            """

            student_id = student_id.strip()

            allowed_subject_ids = None

            # ------------------------------------------------
            # FACULTY AUTHORIZATION
            # ------------------------------------------------

            if current_user.role == "faculty":

                if subject_id is not None:

                    allowed = faculty_can_access_student_subject(
                        db=db,
                        faculty_user_id=current_user.id,
                        student_id=student_id,
                        subject_id=subject_id
                    )

                    if not allowed:
                        return {
                            "error": (
                                "Access denied. You are not authorized "
                                "to access this student's subject data."
                            )
                        }

                else:
                    student = _get_student(
                        db,
                        student_id
                    )

                    if not student or not student.is_active:
                        return {
                            "error": "Active student not found."
                        }

                    allowed_subject_ids = get_faculty_student_subject_ids(
                        db=db,
                        faculty_user_id=current_user.id,
                        student=student
                    )

                    if not allowed_subject_ids:
                        return {
                            "error": (
                                "Access denied. No authorized subjects "
                                "are available for this student."
                            )
                        }

            # ------------------------------------------------
            # STUDENT VALIDATION
            # ------------------------------------------------

            student = _get_student(
                db,
                student_id
            )

            if not student:
                return {
                    "error":
                        "Student not found."
                }

            # ------------------------------------------------
            # SUBJECT VALIDATION
            # ------------------------------------------------

            if subject_id is not None:

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
                subject_id,
                allowed_subject_ids
            )


        # ====================================================
        # ADMIN: STUDENT LIBRARY LOANS
        # ====================================================

        @tool
        def student_library_loans(student_id: str):
            """
            Get the currently issued and overdue books
            for a student.

            Admin can view library loan records for any
            active student. This tool is read-only.
            """

            student_id = student_id.strip()

            if not student_id:
                return {
                    "error": "Student ID cannot be empty."
                }

            # Find the active student
            student = db.query(Student).filter(
                Student.student_id == student_id,
                Student.is_active.is_(True)
            ).first()

            if not student:
                return {
                    "error": "Active student not found."
                }

            # Fetch currently issued books
            rows = (
                db.query(BookIssue, BookCopy, Book)
                .join(
                    BookCopy,
                    BookCopy.id == BookIssue.book_copy_id
                )
                .join(
                    Book,
                    Book.id == BookCopy.book_id
                )
                .filter(
                    BookIssue.student_id == student_id,
                    BookIssue.status == "issued"
                )
                .order_by(BookIssue.due_date.asc())
                .limit(50)
                .all()
            )

            today = date.today()
            issued_books = []
            overdue_books = []

            for issue, copy, book in rows:

                due_date = issue.due_date

                # Handle both DATE and DATETIME database columns
                if isinstance(due_date, datetime):
                    due_date = due_date.date()

                book_record = {
                    "issue_id": issue.id,
                    "title": book.title,
                    "accession_number": copy.accession_number,
                    "issue_date": (
                        str(issue.issue_date)
                        if issue.issue_date
                        else None
                    ),
                    "due_date": (
                        str(issue.due_date)
                        if issue.due_date
                        else None
                    ),
                    "fine_amount": float(
                        issue.fine_amount or 0
                    ),
                    "overdue": (
                        due_date < today
                        if due_date is not None
                        else False
                    )
                }

                issued_books.append(book_record)

                if (
                    due_date is not None
                    and due_date < today
                ):
                    overdue_books.append(book_record)

            return {
                "student_id": student.student_id,
                "student_name": student.name,
                "total_issued_books": len(issued_books),
                "total_overdue_books": len(overdue_books),
                "issued_books": issued_books,
                "overdue_books": overdue_books,
                "checked_on": str(today)
            }

        # ====================================================
        # RETURN TOOLS
        # ====================================================

        return [
            find_student,
            find_subject,
            total_students,
            low_attendance_students,
            high_risk_students,
            average_attendance,
            student_performance,
            student_attendance,
            student_marks,
            student_risk,
            student_recommendations,
            student_library_loans
        ]


    
    # ========================================================
    # HOD / ACCOUNTANT / LIBRARIAN / ADMISSION OFFICER
    # ROLE-SPECIFIC READ-ONLY AI TOOLS
    # ========================================================

    elif current_user.role in [
        "hod",
        "accountant",
        "librarian",
        "admission_officer",
    ]:

        # ====================================================
        # HOD: OWN DEPARTMENT ONLY
        # ====================================================

        if current_user.role == "hod":

            hod = db.query(HOD).filter(
                HOD.user_id == current_user.id
            ).first()

            if not hod:
                return []

            department_id = hod.department_id

            @tool
            def hod_department_summary():
                """
                Get summary counts for the logged-in HOD's
                own department only.
                """

                students_count = (
                    db.query(Student)
                    .filter(
                        Student.department_id == department_id,
                        Student.is_active.is_(True),
                    )
                    .count()
                )

                faculty_count = (
                    db.query(Faculty)
                    .filter(
                        Faculty.department_id == department_id
                    )
                    .count()
                )

                course_count = (
                    db.query(Course)
                    .filter(
                        Course.department_id == department_id
                    )
                    .count()
                )

                return {
                    "department_id": department_id,
                    "active_students": students_count,
                    "faculty_count": faculty_count,
                    "course_count": course_count,
                }

            @tool
            def hod_low_attendance_students(
                threshold: float = 75
            ):
                """
                Get students with attendance below the given
                threshold in the logged-in HOD's department.
                """

                if threshold < 0 or threshold > 100:
                    return {
                        "error": "Threshold must be between 0 and 100."
                    }

                records = (
                    db.query(Performance, Student, Subject)
                    .join(
                        Student,
                        Student.student_id == Performance.student_id
                    )
                    .join(
                        Subject,
                        Subject.id == Performance.subject_id
                    )
                    .join(
                        Course,
                        Course.id == Student.course_id
                    )
                    .filter(
                        Student.department_id == department_id,
                        Course.department_id == department_id,
                        Subject.course_id == Student.course_id,
                        Subject.semester == Student.semester,
                        Student.is_active.is_(True),
                        Performance.attendance_percentage < threshold,
                    )
                    .order_by(
                        Performance.attendance_percentage.asc()
                    )
                    .limit(100)
                    .all()
                )

                return {
                    "department_id": department_id,
                    "threshold": threshold,
                    "students": [
                        {
                            "student_id": student.student_id,
                            "student_name": student.name,
                            "subject_name": subject.name,
                            "attendance_percentage": float(
                                performance.attendance_percentage or 0
                            ),
                        }
                        for performance, student, subject in records
                    ],
                }

            return [
                hod_department_summary,
                hod_low_attendance_students,
            ]

        # ====================================================
        # ACCOUNTANT: FEE INFORMATION ONLY
        # ====================================================

        if current_user.role == "accountant":

            accountant = db.query(Accountant).filter(
                Accountant.user_id == current_user.id
            ).first()

            if not accountant:
                return []

            @tool
            def fee_summary():
                """
                Get college-wide fee totals for the accountant.
                This tool only reads financial records.
                """

                row = db.query(
                    func.count(StudentFee.id),
                    func.coalesce(func.sum(StudentFee.total_fee), 0),
                    func.coalesce(func.sum(StudentFee.paid_amount), 0),
                    func.coalesce(func.sum(StudentFee.pending_amount), 0),
                    func.coalesce(func.sum(StudentFee.late_fee_amount), 0),
                ).first()

                return {
                    "fee_records": int(row[0] or 0),
                    "total_fee_amount": float(row[1] or 0),
                    "total_paid_amount": float(row[2] or 0),
                    "total_pending_amount": float(row[3] or 0),
                    "recorded_late_fee_amount": float(row[4] or 0),
                }

            @tool
            def student_fee_status(student_id: str):
                """
                Get fee status and recent payment history
                for a specific student.
                """

                student_id = student_id.strip()

                if not student_id:
                    return {"error": "Student ID cannot be empty."}

                student = db.query(Student).filter(
                    Student.student_id == student_id,
                    Student.is_active.is_(True),
                ).first()

                if not student:
                    return {"error": "Active student not found."}

                fee_rows = (
                    db.query(StudentFee, FeeStructure, Course)
                    .join(
                        FeeStructure,
                        FeeStructure.id == StudentFee.fee_structure_id
                    )
                    .join(
                        Course,
                        Course.id == FeeStructure.course_id
                    )
                    .filter(
                        StudentFee.student_id == student_id
                    )
                    .order_by(StudentFee.created_at.desc())
                    .limit(20)
                    .all()
                )

                fees = []

                for fee, structure, course in fee_rows:
                    payments = (
                        db.query(FeePayment)
                        .filter(
                            FeePayment.student_fee_id == fee.id
                        )
                        .order_by(FeePayment.payment_date.desc())
                        .limit(10)
                        .all()
                    )

                    fees.append({
                        "fee_record_id": fee.id,
                        "course_name": course.name,
                        "academic_year": fee.academic_year,
                        "total_fee": float(fee.total_fee or 0),
                        "paid_amount": float(fee.paid_amount or 0),
                        "pending_amount": float(fee.pending_amount or 0),
                        "late_fee_amount": float(fee.late_fee_amount or 0),
                        "payment_status": fee.payment_status,
                        "due_date": str(structure.due_date),
                        "recent_payments": [
                            {
                                "amount": float(payment.amount),
                                "receipt_number": payment.receipt_number,
                                "payment_date": str(payment.payment_date),
                                "payment_method": payment.payment_method,
                            }
                            for payment in payments
                        ],
                    })

                return {
                    "student_id": student.student_id,
                    "student_name": student.name,
                    "fees": fees,
                }

            return [
                fee_summary,
                student_fee_status,
            ]

        # ====================================================
        # LIBRARIAN: BOOKS / LOANS / LIBRARY FINES
        # ====================================================

        if current_user.role == "librarian":

            librarian = db.query(Librarian).filter(
                Librarian.user_id == current_user.id
            ).first()

            if not librarian:
                return []

            @tool
            def search_library_books(search_text: str):
                """
                Search book titles, authors, or categories
                and return copy availability.
                """

                search_text = search_text.strip()

                if not search_text:
                    return {"error": "Search text cannot be empty."}

                escaped = (
                    search_text
                    .replace("\\", "\\\\")
                    .replace("%", "\\%")
                    .replace("_", "\\_")
                )
                pattern = f"%{escaped}%"

                rows = (
                    db.query(
                        Book,
                        func.count(BookCopy.id).label("total_copies"),
                        func.sum(
                            case(
                                (BookCopy.status == "available", 1),
                                else_=0,
                            )
                        ).label("available_copies"),
                    )
                    .outerjoin(
                        BookCopy,
                        BookCopy.book_id == Book.id
                    )
                    .filter(
                        or_(
                            Book.title.ilike(pattern, escape="\\"),
                            Book.author.ilike(pattern, escape="\\"),
                            Book.category.ilike(pattern, escape="\\"),
                        )
                    )
                    .group_by(Book.id)
                    .order_by(Book.title.asc())
                    .limit(20)
                    .all()
                )

                return {
                    "books": [
                        {
                            "book_id": book.id,
                            "title": book.title,
                            "author": book.author,
                            "category": book.category,
                            "total_copies": int(total or 0),
                            "available_copies": int(available or 0),
                        }
                        for book, total, available in rows
                    ]
                }

            @tool
            def student_library_loans(student_id: str):
                """
                Get current issued books for a student.
                """

                student_id = student_id.strip()

                if not student_id:
                    return {"error": "Student ID cannot be empty."}

                student = db.query(Student).filter(
                    Student.student_id == student_id,
                    Student.is_active.is_(True),
                ).first()

                if not student:
                    return {"error": "Active student not found."}

                rows = (
                    db.query(BookIssue, BookCopy, Book)
                    .join(
                        BookCopy,
                        BookCopy.id == BookIssue.book_copy_id
                    )
                    .join(
                        Book,
                        Book.id == BookCopy.book_id
                    )
                    .filter(
                        BookIssue.student_id == student_id,
                        BookIssue.status == "issued",
                    )
                    .order_by(BookIssue.due_date.asc())
                    .limit(50)
                    .all()
                )

                return {
                    "student_id": student.student_id,
                    "student_name": student.name,
                    "issued_books": [
                        {
                            "issue_id": issue.id,
                            "title": book.title,
                            "accession_number": copy.accession_number,
                            "issue_date": str(issue.issue_date),
                            "due_date": str(issue.due_date),
                            "fine_amount": float(issue.fine_amount or 0),
                        }
                        for issue, copy, book in rows
                    ],
                }

            @tool
            def pending_library_fines():
                """
                List pending library fines for the librarian.
                """

                rows = (
                    db.query(LibraryFine, Student)
                    .join(
                        Student,
                        Student.student_id == LibraryFine.student_id
                    )
                    .filter(
                        LibraryFine.status == "pending"
                    )
                    .order_by(LibraryFine.forwarded_at.desc())
                    .limit(100)
                    .all()
                )

                return {
                    "pending_fines": [
                        {
                            "fine_id": fine.id,
                            "student_id": student.student_id,
                            "student_name": student.name,
                            "fine_amount": float(fine.fine_amount),
                            "reason": fine.reason,
                            "status": fine.status,
                            "forwarded_at": str(fine.forwarded_at),
                        }
                        for fine, student in rows
                    ]
                }

            return [
                search_library_books,
                student_library_loans,
                pending_library_fines,
            ]

        # ====================================================
        # ADMISSION OFFICER: ADMISSION RECORDS ONLY
        # ====================================================

        if current_user.role == "admission_officer":

            officer = db.query(AdmissionOfficer).filter(
                AdmissionOfficer.user_id == current_user.id
            ).first()

            if not officer:
                return []

            @tool
            def search_admission_records(search_text: str):
                """
                Search admission records by applicant name
                or application number.
                """

                search_text = search_text.strip()

                if not search_text:
                    return {"error": "Search text cannot be empty."}

                escaped = (
                    search_text
                    .replace("\\", "\\\\")
                    .replace("%", "\\%")
                    .replace("_", "\\_")
                )
                pattern = f"%{escaped}%"

                rows = (
                    db.query(AdmissionApplication, Course)
                    .join(
                        Course,
                        Course.id == AdmissionApplication.course_id
                    )
                    .filter(
                        or_(
                            AdmissionApplication.applicant_name.ilike(
                                pattern, escape="\\"
                            ),
                            AdmissionApplication.application_number.ilike(
                                pattern, escape="\\"
                            ),
                        )
                    )
                    .order_by(
                        AdmissionApplication.submitted_at.desc()
                    )
                    .limit(20)
                    .all()
                )

                return {
                    "admissions": [
                        {
                            "application_number": application.application_number,
                            "applicant_name": application.applicant_name,
                            "course_name": course.name,
                            "semester": application.semester,
                            "academic_year": application.academic_year,
                            "status": application.status,
                            "enrolled_student_id": application.enrolled_student_id,
                        }
                        for application, course in rows
                    ]
                }

            @tool
            def admission_course_summary():
                """
                Count enrolled admission records by course
                and academic year.
                """

                rows = (
                    db.query(
                        Course.name,
                        AdmissionApplication.academic_year,
                        func.count(AdmissionApplication.id),
                    )
                    .join(
                        AdmissionApplication,
                        AdmissionApplication.course_id == Course.id
                    )
                    .group_by(
                        Course.name,
                        AdmissionApplication.academic_year,
                    )
                    .order_by(
                        AdmissionApplication.academic_year.desc(),
                        Course.name.asc(),
                    )
                    .limit(100)
                    .all()
                )

                return {
                    "enrollment_summary": [
                        {
                            "course_name": course_name,
                            "academic_year": academic_year,
                            "enrolled_applications": int(total),
                        }
                        for course_name, academic_year, total in rows
                    ]
                }

            return [
                search_admission_records,
                admission_course_summary,
            ]


    # ========================================================
    # UNKNOWN ROLE
    # ========================================================

    return []