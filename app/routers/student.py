from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Form
)

from sqlalchemy.orm import Session

from app.database.database import get_db

from app.database.models import (
    Student,
    User,
    Department,
    Course
)

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
    course_id: int = Form(...),
    semester: int = Form(...),

    db: Session = Depends(get_db),
    current_faculty: User = Depends(require_faculty)
):


    
    # -----------------------------------------
    # CLEAN INPUT
    # -----------------------------------------

    student_id = student_id.strip()
    name = name.strip()
    email = email.strip().lower()

    if phone:
        phone = phone.strip()

    # -----------------------------------------
    # VALIDATION
    # -----------------------------------------

    if not student_id:
        raise HTTPException(
            status_code=400,
            detail="Student ID cannot be empty"
        )

    if not name:
        raise HTTPException(
            status_code=400,
            detail="Student name cannot be empty"
        )

    if not email:
        raise HTTPException(
            status_code=400,
            detail="Email cannot be empty"
        )

    if not password:
        raise HTTPException(
            status_code=400,
            detail="Password cannot be empty"
        )



    # ----------------------------------------------
    # CHECK EMAIL
    # ----------------------------------------------

    existing_user = db.query(User).filter(
        User.email == email
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )


    # ----------------------------------------------
    # CHECK STUDENT ID
    # ----------------------------------------------

    existing_student = db.query(Student).filter(
        Student.student_id == student_id
    ).first()

    if existing_student:
        raise HTTPException(
            status_code=400,
            detail="Student ID already exists"
        )


    # ----------------------------------------------
    # CHECK DEPARTMENT
    # ----------------------------------------------

    department = db.query(Department).filter(
        Department.id == department_id
    ).first()

    if not department:
        raise HTTPException(
            status_code=404,
            detail="Department not found"
        )


    # ----------------------------------------------
    # CHECK COURSE
    # ----------------------------------------------

    course = db.query(Course).filter(
        Course.id == course_id
    ).first()

    if not course:
        raise HTTPException(
            status_code=404,
            detail="Course not found"
        )


    # ----------------------------------------------
    # COURSE MUST BELONG TO DEPARTMENT
    # ----------------------------------------------

    if course.department_id != department_id:
        raise HTTPException(
            status_code=400,
            detail="Selected course does not belong to selected department"
        )


    # ----------------------------------------------
    # VALIDATE SEMESTER
    # ----------------------------------------------

    if semester < 1 or semester > 12:
        raise HTTPException(
            status_code=400,
            detail="Semester must be between 1 and 12"
        )


    # ----------------------------------------------
    # CREATE USER ACCOUNT
    # ----------------------------------------------

    user = User(
        name=name,
        email=email,
        password_hash=hash_password(password),
        role="student"
    )

    db.add(user)

    # Generate user.id before creating Student
    db.flush()


    # ----------------------------------------------
    # CREATE STUDENT PROFILE
    # ----------------------------------------------

    student = Student(
        user_id=user.id,
        student_id=student_id,
        name=name,
        phone=phone,
        department_id=department_id,
        course_id=course_id,
        semester=semester
    )

    db.add(student)

    db.commit()

    db.refresh(user)
    db.refresh(student)


    # ----------------------------------------------
    # RESPONSE
    # ----------------------------------------------

    return {
        "message": "Student created successfully",
        "id": student.id,
        "student_id": student.student_id,
        "name": student.name,
        "email": user.email,
        "phone": student.phone,
        "department_id": department.id,
        "department": department.name,
        "course_id": course.id,
        "course": course.name,
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
            "department_id": student.department_id,
            "department": student.department.name,
            "course_id": student.course_id,
            "course": student.course.name,
            "semester": student.semester
        })

    return result


# --------------------------------------------------
# GET STUDENT BY ID
# --------------------------------------------------

@router.get("/{student_id}")
def get_student(
    student_id: str,
    db: Session = Depends(get_db),
    current_faculty: User = Depends(require_faculty)
):

    student_id = student_id.strip()


    student = db.query(Student).filter(
        Student.student_id == student_id
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
        "department_id": student.department_id,
        "department": student.department.name,
        "course_id": student.course_id,
        "course": student.course.name,
        "semester": student.semester
    }


# --------------------------------------------------
# DELETE STUDENT
# --------------------------------------------------

@router.delete("/{student_id}")
def delete_student(
    student_id: str,
    db: Session = Depends(get_db),
    current_faculty: User = Depends(require_faculty)
):

    student_id = student_id.strip()

    student = db.query(Student).filter(
        Student.student_id == student_id
    ).first()

    if not student:
        raise HTTPException(
            status_code=404,
            detail="Student not found"
        )


    # Find linked user
    user = db.query(User).filter(
        User.id == student.user_id
    ).first()


    # Delete student profile
    db.delete(student)

    # Delete login account
    if user:
        db.delete(user)

    db.commit()

    return {
        "message": "Student deleted successfully"
    }