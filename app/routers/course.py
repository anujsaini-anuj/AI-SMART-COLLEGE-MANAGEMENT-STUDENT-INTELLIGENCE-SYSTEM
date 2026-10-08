from fastapi import APIRouter, Depends, HTTPException, Form
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.models import Course, Department, Student, User

from app.utils.auth import require_admin


router = APIRouter(
    prefix="/courses",
    tags=["Course Management"]
)


# ============================================================
# HELPER
# Course duration (years) -> maximum semesters
# ============================================================

def get_max_semester(duration_years: int) -> int:

    if duration_years <= 0:
        raise HTTPException(
            status_code=400,
            detail="Course duration must be greater than 0 years."
        )

    return duration_years * 2


# ============================================================
# CREATE COURSE
# ============================================================

@router.post("/create")
def create_course(

    name: str = Form(...),
    code: str = Form(...),
    duration: int = Form(..., gt=0),
    description: str | None = Form(None),
    department_id: int = Form(...),

    db: Session = Depends(get_db),
    current_user=Depends(require_admin)
):

    # --------------------------------------------------------
    # CLEAN INPUTS
    # --------------------------------------------------------

    name = name.strip()
    code = code.strip().upper()
    description = description.strip() if description else None

    # --------------------------------------------------------
    # VALIDATE COURSE NAME
    # --------------------------------------------------------

    if len(name) < 2:
        raise HTTPException(
            status_code=400,
            detail="Course name must contain at least 2 characters."
        )

    # --------------------------------------------------------
    # VALIDATE COURSE CODE
    # --------------------------------------------------------

    if not code:
        raise HTTPException(
            status_code=400,
            detail="Course code cannot be empty."
        )

    # --------------------------------------------------------
    # CHECK DEPARTMENT
    # --------------------------------------------------------

    department = db.query(Department).filter(
        Department.id == department_id
    ).first()

    if not department:
        raise HTTPException(
            status_code=404,
            detail="Department not found."
        )

    # --------------------------------------------------------
    # CHECK DUPLICATE COURSE CODE
    # --------------------------------------------------------

    existing_course = (
        db.query(Course)
        .filter(Course.code == code)
        .first()
    )

    if existing_course:
        raise HTTPException(
            status_code=409,
            detail="Course with this code already exists."
        )

    # --------------------------------------------------------
    # GET MAXIMUM SEMESTER
    # --------------------------------------------------------

    max_semester = get_max_semester(duration)

    # --------------------------------------------------------
    # CREATE COURSE
    # --------------------------------------------------------

    course = Course(
        name=name,
        code=code,
        duration=duration,
        description=description,
        department_id=department_id
    )

    db.add(course)
    db.commit()
    db.refresh(course)

    return {

        "message": "Course created successfully",

        "course": {

            "id": course.id,

            "name": course.name,

            "code": course.code,

            "duration_years": course.duration,

            "maximum_semester": max_semester,

            "description": course.description,

            "department_id": course.department_id,

            "department": department.name
        }
    }


# ============================================================
# GET ALL COURSES
# ============================================================

@router.get("/")
def get_all_courses(

    db: Session = Depends(get_db),

    current_admin: User = Depends(require_admin)

):

    courses = db.query(Course).all()

    result = []

    for course in courses:

        result.append({

            "id": course.id,

            "name": course.name,

            "code": course.code,

            "duration_years": course.duration,

            "maximum_semester":
                get_max_semester(course.duration),

            "description": course.description,

            "department_id": course.department_id,

            "department": course.department.name
        })

    return result


# ============================================================
# GET COURSE BY ID
# ============================================================

@router.get("/{course_id}")
def get_course(

    course_id: int,

    db: Session = Depends(get_db),

    current_admin: User = Depends(require_admin)

):

    course = db.query(Course).filter(
        Course.id == course_id
    ).first()

    if not course:
        raise HTTPException(
            status_code=404,
            detail="Course not found."
        )

    return {

        "id": course.id,

        "name": course.name,

        "code": course.code,

        "duration_years": course.duration,

        "maximum_semester":
            get_max_semester(course.duration),

        "description": course.description,

        "department_id": course.department_id,

        "department": course.department.name
    }


# ============================================================
# UPDATE COURSE
# ============================================================

@router.put("/{course_id}")
def update_course(

    course_id: int,

    name: str = Form(...),
    code: str = Form(...),
    duration: int = Form(..., gt=0),
    department_id: int = Form(...),
    description: str | None = Form(None),

    db: Session = Depends(get_db),

    current_admin: User = Depends(require_admin)

):

    # --------------------------------------------------------
    # FIND COURSE
    # --------------------------------------------------------

    course = db.query(Course).filter(
        Course.id == course_id
    ).first()

    if not course:
        raise HTTPException(
            status_code=404,
            detail="Course not found."
        )

    # --------------------------------------------------------
    # CLEAN INPUTS
    # --------------------------------------------------------

    name = name.strip()
    code = code.strip().upper()
    description = description.strip() if description else None

    # --------------------------------------------------------
    # VALIDATE COURSE NAME
    # --------------------------------------------------------

    if len(name) < 2:
        raise HTTPException(
            status_code=400,
            detail="Course name must contain at least 2 characters."
        )

    # --------------------------------------------------------
    # CHECK DUPLICATE COURSE CODE
    # --------------------------------------------------------

    existing_course = db.query(Course).filter(
        Course.code == code,
        Course.id != course_id
    ).first()

    if existing_course:
        raise HTTPException(
            status_code=409,
            detail="Course code already exists."
        )

    # --------------------------------------------------------
    # CHECK DEPARTMENT
    # --------------------------------------------------------

    department = db.query(Department).filter(
        Department.id == department_id
    ).first()

    if not department:
        raise HTTPException(
            status_code=404,
            detail="Department not found."
        )

    # --------------------------------------------------------
    # GET NEW MAXIMUM SEMESTER
    # --------------------------------------------------------

    max_semester = get_max_semester(duration)

    # --------------------------------------------------------
    # IMPORTANT:
    # CHECK EXISTING STUDENTS
    #
    # If course duration is reduced, existing students
    # must still fit inside the new maximum semester.
    # --------------------------------------------------------

    students = db.query(Student).filter(
        Student.course_id == course_id
    ).all()

    invalid_students = [
        student
        for student in students
        if student.semester > max_semester
    ]

    if invalid_students:

        raise HTTPException(
            status_code=400,
            detail=(
                f"Course duration cannot be changed to "
                f"{duration} years because "
                f"{len(invalid_students)} student(s) are already "
                f"above the maximum allowed semester "
                f"{max_semester}."
            )
        )

    # --------------------------------------------------------
    # UPDATE COURSE
    # --------------------------------------------------------

    course.name = name
    course.code = code
    course.duration = duration
    course.department_id = department_id
    course.description = description

    db.commit()
    db.refresh(course)

    return {

        "message": "Course updated successfully",

        "course": {

            "id": course.id,

            "name": course.name,

            "code": course.code,

            "duration_years": course.duration,

            "maximum_semester": max_semester,

            "department_id": course.department_id,

            "department": department.name,

            "description": course.description
        }
    }


# ============================================================
# DELETE COURSE
# ============================================================

@router.delete("/{course_id}")
def delete_course(

    course_id: int,

    db: Session = Depends(get_db),

    current_admin: User = Depends(require_admin)

):

    course = db.query(Course).filter(
        Course.id == course_id
    ).first()

    if not course:
        raise HTTPException(
            status_code=404,
            detail="Course not found."
        )

    # --------------------------------------------------------
    # CHECK STUDENTS
    # --------------------------------------------------------

    student_count = db.query(Student).filter(
        Student.course_id == course_id
    ).count()

    if student_count > 0:

        raise HTTPException(
            status_code=400,
            detail=(
                f"Course cannot be deleted because "
                f"{student_count} student(s) are enrolled in this course."
            )
        )

    # --------------------------------------------------------
    # DELETE COURSE
    # --------------------------------------------------------

    db.delete(course)
    db.commit()

    return {
        "message": "Course deleted successfully"
    }