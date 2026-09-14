from fastapi import APIRouter, Depends, HTTPException, Form

from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.models import Course, Department, User

from app.utils.auth import require_admin


router = APIRouter(
    prefix="/courses",
    tags=["Course Management"]
)


# --------------------------------------------------
# CREATE COURSE
# --------------------------------------------------

@router.post("/create")
def create_course(
    name: str = Form(...),
    code: str = Form(...),
    duration: int = Form(...),
    department_id: int = Form(...),
    description: str | None = Form(None),

    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin)
):

    # Check course code
    existing_course = db.query(Course).filter(
        Course.code == code
    ).first()

    if existing_course:
        raise HTTPException(
            status_code=400,
            detail="Course code already exists"
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

    # Validate duration
    if duration <= 0:
        raise HTTPException(
            status_code=400,
            detail="Course duration must be greater than 0"
        )

    course = Course(
        name=name,
        code=code,
        duration=duration,
        department_id=department_id,
        description=description
    )

    db.add(course)
    db.commit()
    db.refresh(course)

    return {
        "message": "Course created successfully",
        "course_id": course.id,
        "name": course.name,
        "code": course.code,
        "duration": course.duration,
        "department": department.name,
        "description": course.description
    }


# --------------------------------------------------
# GET ALL COURSES
# --------------------------------------------------

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
            "duration": course.duration,
            "description": course.description,
            "department_id": course.department_id,
            "department": course.department.name
        })

    return result


# --------------------------------------------------
# GET COURSE BY ID
# --------------------------------------------------

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
            detail="Course not found"
        )

    return {
        "id": course.id,
        "name": course.name,
        "code": course.code,
        "duration": course.duration,
        "description": course.description,
        "department_id": course.department_id,
        "department": course.department.name
    }


# --------------------------------------------------
# UPDATE COURSE
# --------------------------------------------------

@router.put("/{course_id}")
def update_course(
    course_id: int,

    name: str = Form(...),
    code: str = Form(...),
    duration: int = Form(...),
    department_id: int = Form(...),
    description: str | None = Form(None),

    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin)
):

    course = db.query(Course).filter(
        Course.id == course_id
    ).first()

    if not course:
        raise HTTPException(
            status_code=404,
            detail="Course not found"
        )

    # Check code belongs to another course
    existing_course = db.query(Course).filter(
        Course.code == code,
        Course.id != course_id
    ).first()

    if existing_course:
        raise HTTPException(
            status_code=400,
            detail="Course code already exists"
        )

    department = db.query(Department).filter(
        Department.id == department_id
    ).first()

    if not department:
        raise HTTPException(
            status_code=404,
            detail="Department not found"
        )

    if duration <= 0:
        raise HTTPException(
            status_code=400,
            detail="Course duration must be greater than 0"
        )

    course.name = name
    course.code = code
    course.duration = duration
    course.department_id = department_id
    course.description = description

    db.commit()
    db.refresh(course)

    return {
        "message": "Course updated successfully",
        "course_id": course.id,
        "name": course.name,
        "code": course.code,
        "duration": course.duration,
        "department": department.name,
        "description": course.description
    }


# --------------------------------------------------
# DELETE COURSE
# --------------------------------------------------

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
            detail="Course not found"
        )

    db.delete(course)
    db.commit()

    return {
        "message": "Course deleted successfully"
    }