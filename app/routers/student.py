from fastapi import APIRouter, Depends, HTTPException, Form
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.models import Student, User, Department

from app.utils.auth import require_faculty
from app.utils.security import hash_password


router = APIRouter(
    prefix="/students",
    tags=["Student Management"]
)


# --------------------------------------------------
# CREATE STUDENT
# --------------------------------------------------

@router.post("/create")
def create_student(
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    student_id: str = Form(...),
    phone: str | None = Form(None),
    department_id: int = Form(...),
    course: str = Form(...),
    semester: int = Form(...),

    db: Session = Depends(get_db),
    current_faculty: User = Depends(require_faculty)
):

    # Check email
    existing_user = db.query(User).filter(
        User.email == email
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    # Check Student ID
    existing_student = db.query(Student).filter(
        Student.student_id == student_id
    ).first()

    if existing_student:
        raise HTTPException(
            status_code=400,
            detail="Student ID already exists"
        )

    # Check department
    department = db.query(Department).filter(
        Department.id == department_id
    ).first()

    if not department:
        raise HTTPException(
            status_code=404,
            detail="Department not found"
        )

    # Validate semester
    if semester < 1 or semester > 12:
        raise HTTPException(
            status_code=400,
            detail="Semester must be between 1 and 12"
        )

    # Create login account
    user = User(
        name=name,
        email=email,
        password_hash=__import__(
            "app.utils.security",
            fromlist=["hash_password"]
        ).hash_password(password),
        role="student"
    )

    db.add(user)
    db.flush()

    # Create student profile
    student = Student(
        user_id=user.id,
        student_id=student_id,
        name=name,
        phone=phone,
        department_id=department_id,
        course=course,
        semester=semester
    )

    db.add(student)

    db.commit()

    db.refresh(user)
    db.refresh(student)

    return {
        "message": "Student created successfully",
        "student_profile_id": student.id,
        "student_id": student.student_id,
        "name": student.name,
        "email": user.email,
        "department": department.name,
        "course": student.course,
        "semester": student.semester
    }


# --------------------------------------------------
# GET ALL STUDENTS
# --------------------------------------------------

@router.get("/")
def get_all_students(
    db: Session = Depends(get_db),
    current_faculty: User = Depends(require_faculty)
):

    students = db.query(Student).all()

    result = []

    for student in students:

        result.append({
            "id": student.id,
            "student_id": student.student_id,
            "name": student.name,
            "phone": student.phone,
            "email": student.user.email,
            "department": student.department.name,
            "course": student.course,
            "semester": student.semester
        })

    return result


# --------------------------------------------------
# GET STUDENT BY ID
# --------------------------------------------------

@router.get("/{student_id}")
def get_student(
    student_id: int,
    db: Session = Depends(get_db),
    current_faculty: User = Depends(require_faculty)
):

    student = db.query(Student).filter(
        Student.id == student_id
    ).first()

    if not student:
        raise HTTPException(
            status_code=404,
            detail="Student not found"
        )

    return {
        "id": student.id,
        "student_id": student.student_id,
        "name": student.name,
        "phone": student.phone,
        "email": student.user.email,
        "department": student.department.name,
        "course": student.course,
        "semester": student.semester
    }


# --------------------------------------------------
# DELETE STUDENT
# --------------------------------------------------

@router.delete("/{student_id}")
def delete_student(
    student_id: int,
    db: Session = Depends(get_db),
    current_faculty: User = Depends(require_faculty)
):

    student = db.query(Student).filter(
        Student.id == student_id
    ).first()

    if not student:
        raise HTTPException(
            status_code=404,
            detail="Student not found"
        )

    user = db.query(User).filter(
        User.id == student.user_id
    ).first()

    db.delete(student)

    if user:
        db.delete(user)

    db.commit()

    return {
        "message": "Student deleted successfully"
    }