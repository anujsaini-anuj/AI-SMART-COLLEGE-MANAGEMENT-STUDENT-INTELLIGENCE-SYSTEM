from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Form
)

from sqlalchemy.orm import Session

from app.database.database import get_db

from app.database.models import (
    Faculty,
    User,
    Department
)

from app.utils.auth import require_admin
from app.utils.security import hash_password


router = APIRouter(
    prefix="/faculties",
    tags=["Faculty Management"]
)


# ==================================================
# CREATE FACULTY
# ==================================================

@router.post("/create")
def create_faculty(
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    faculty_id: str = Form(...),
    phone: str | None = Form(None),
    designation: str | None = Form(None),
    department_id: int = Form(...),

    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin)
):

    # ------------------------------------------------
    # CHECK EMAIL
    # ------------------------------------------------

    existing_user = db.query(User).filter(
        User.email == email
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )


    # ------------------------------------------------
    # CHECK FACULTY ID
    # ------------------------------------------------

    existing_faculty = db.query(Faculty).filter(
        Faculty.faculty_id == faculty_id
    ).first()

    if existing_faculty:
        raise HTTPException(
            status_code=400,
            detail="Faculty ID already exists"
        )


    # ------------------------------------------------
    # CHECK DEPARTMENT
    # ------------------------------------------------

    department = db.query(Department).filter(
        Department.id == department_id
    ).first()

    if not department:
        raise HTTPException(
            status_code=404,
            detail="Department not found"
        )


    # ------------------------------------------------
    # CREATE USER ACCOUNT
    # ------------------------------------------------

    user = User(
        name=name,
        email=email,
        password_hash=hash_password(password),
        role="faculty"
    )

    db.add(user)

    # Generate user ID before creating Faculty
    db.flush()


    # ------------------------------------------------
    # CREATE FACULTY PROFILE
    # ------------------------------------------------

    faculty = Faculty(
        user_id=user.id,
        faculty_id=faculty_id,
        name=name,
        phone=phone,
        designation=designation,
        department_id=department_id
    )

    db.add(faculty)


    # ------------------------------------------------
    # SAVE BOTH RECORDS
    # ------------------------------------------------

    try:

        db.commit()

    except Exception:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Failed to create faculty"
        )


    db.refresh(user)
    db.refresh(faculty)


    # ------------------------------------------------
    # RESPONSE
    # ------------------------------------------------

    return {
        "message": "Faculty created successfully",

        "user_id": user.id,

        "id": faculty.id,

        "faculty_id": faculty.faculty_id,

        "name": faculty.name,

        "email": user.email,

        "phone": faculty.phone,

        "designation": faculty.designation,

        "department_id": department.id,

        "department": department.name,

        "role": user.role
    }


# ==================================================
# GET ALL FACULTIES
# ==================================================

@router.get("/")
def get_faculties(
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin)
):

    faculties = db.query(Faculty).all()

    result = []

    for faculty in faculties:

        result.append({
            "id": faculty.id,
            "user_id": faculty.user_id,
            "faculty_id": faculty.faculty_id,
            "name": faculty.name,
            "email": faculty.user.email,
            "phone": faculty.phone,
            "designation": faculty.designation,
            "department_id": faculty.department_id,
            "department": faculty.department.name
        })

    return result


# ==================================================
# GET FACULTY BY ID
# ==================================================

@router.get("/{faculty_id}")
def get_faculty(
    faculty_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin)
):

    faculty = db.query(Faculty).filter(
        Faculty.id == faculty_id
    ).first()

    if not faculty:
        raise HTTPException(
            status_code=404,
            detail="Faculty not found"
        )

    return {
        "id": faculty.id,
        "user_id": faculty.user_id,
        "faculty_id": faculty.faculty_id,
        "name": faculty.name,
        "email": faculty.user.email,
        "phone": faculty.phone,
        "designation": faculty.designation,
        "department_id": faculty.department_id,
        "department": faculty.department.name
    }


# ==================================================
# DELETE FACULTY
# ==================================================

@router.delete("/{faculty_id}")
def delete_faculty(
    faculty_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin)
):

    faculty = db.query(Faculty).filter(
        Faculty.id == faculty_id
    ).first()

    if not faculty:
        raise HTTPException(
            status_code=404,
            detail="Faculty not found"
        )


    # Find linked user account
    user = db.query(User).filter(
        User.id == faculty.user_id
    ).first()


    # Delete faculty profile
    db.delete(faculty)

    # Delete login account
    if user:
        db.delete(user)

    db.commit()

    return {
        "message": "Faculty deleted successfully"
    }