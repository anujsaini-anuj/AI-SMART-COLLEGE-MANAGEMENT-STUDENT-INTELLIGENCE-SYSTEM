
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status
)

from sqlalchemy.orm import Session

from app.database.database import get_db

from app.database.models import (
    Student,
    User,
    Faculty
)

from app.utils.auth import (
    require_admin,
    get_current_user
)


router = APIRouter(
    prefix="/students",
    tags=["Student Management"]
)


# ==================================================
# ADMIN OR FACULTY ACCESS
# ==================================================

def require_admin_or_faculty(
    current_user: User = Depends(get_current_user)
):

    if current_user.role not in ["admin", "faculty"]:

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin or Faculty can access student records."
        )

    return current_user


# ==================================================
# GET FACULTY DEPARTMENT
# ==================================================

def get_faculty_department(
    current_user: User,
    db: Session
):

    faculty = db.query(Faculty).filter(
        Faculty.user_id == current_user.id
    ).first()

    if not faculty:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Faculty profile not found."
        )

    return faculty.department_id


# ==================================================
# GET ALL ACTIVE STUDENTS
# ADMIN OR FACULTY
# ==================================================

@router.get("/")
def get_all_students(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_faculty)
):

    query = db.query(Student).filter(
        Student.is_active.is_(True)
    )

    # Faculty can view only their department students
    if current_user.role == "faculty":

        department_id = get_faculty_department(
            current_user,
            db
        )

        query = query.filter(
            Student.department_id == department_id
        )

    students = query.all()

    result = []

    for student in students:

        result.append({
            "id": student.id,
            "student_id": student.student_id,
            "name": student.name,
            "phone": student.phone,
            "email": student.user.email,
            "department_id": student.department_id,
            "department": student.department.name,
            "course_id": student.course_id,
            "course": student.course.name,
            "semester": student.semester,
            "is_active": student.is_active
        })

    return result


# ==================================================
# GET STUDENT BY STUDENT ID
# ADMIN OR FACULTY
# ==================================================

@router.get("/{student_id}")
def get_student(
    student_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_faculty)
):

    student_id = student_id.strip()

    student = db.query(Student).filter(
        Student.student_id == student_id,
        Student.is_active.is_(True)
    ).first()

    if not student:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found."
        )

    # Faculty department restriction
    if current_user.role == "faculty":

        department_id = get_faculty_department(
            current_user,
            db
        )

        if student.department_id != department_id:

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You cannot access students from another department."
            )

    return {
        "id": student.id,
        "student_id": student.student_id,
        "name": student.name,
        "phone": student.phone,
        "email": student.user.email,
        "department_id": student.department_id,
        "department": student.department.name,
        "course_id": student.course_id,
        "course": student.course.name,
        "semester": student.semester,
        "is_active": student.is_active
    }


# ==================================================
# DEACTIVATE STUDENT
# ADMIN ONLY
# ==================================================

@router.delete("/{student_id}")
def deactivate_student(
    student_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):

    student_id = student_id.strip()

    student = db.query(Student).filter(
        Student.student_id == student_id
    ).first()

    if not student:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found."
        )

    if not student.is_active:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Student is already deactivated."
        )

    user = db.query(User).filter(
        User.id == student.user_id
    ).first()

    if not user:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student user account not found."
        )

    try:

        student.is_active = False
        user.is_active = False

        db.commit()

    except Exception:

        db.rollback()
        raise

    return {
        "message": "Student deactivated successfully.",
        "student_id": student.student_id,
        "name": student.name,
        "is_active": False
    }


# ==================================================
# REACTIVATE STUDENT
# ADMIN ONLY
# ==================================================

@router.put("/{student_id}/reactivate")
def reactivate_student(
    student_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):

    student_id = student_id.strip()

    student = db.query(Student).filter(
        Student.student_id == student_id
    ).first()

    if not student:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found."
        )

    if student.is_active:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Student is already active."
        )

    user = db.query(User).filter(
        User.id == student.user_id
    ).first()

    if not user:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student user account not found."
        )

    try:

        student.is_active = True
        user.is_active = True

        db.commit()

    except Exception:

        db.rollback()
        raise

    return {
        "message": "Student reactivated successfully.",
        "student_id": student.student_id,
        "name": student.name,
        "is_active": True
    }