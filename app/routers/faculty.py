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


router = APIRouter(
    prefix="/faculties",
    tags=["Faculty Management"]
)


# --------------------------------------------------
# CREATE FACULTY PROFILE
# --------------------------------------------------

@router.post("/create")
def create_faculty(
    user_id: int = Form(...),
    faculty_id: str = Form(...),
    name: str = Form(...),
    phone: str | None = Form(None),
    designation: str | None = Form(None),
    department_id: int = Form(...),

    db: Session = Depends(get_db),

    current_admin: User = Depends(require_admin)
):

    user = db.query(User).filter(
        User.id == user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    if user.role != "faculty":
        raise HTTPException(
            status_code=400,
            detail="Selected user is not a faculty user"
        )

    existing_faculty = db.query(Faculty).filter(
        Faculty.user_id == user_id
    ).first()

    if existing_faculty:
        raise HTTPException(
            status_code=400,
            detail="Faculty profile already exists"
        )

    existing_faculty_id = db.query(Faculty).filter(
        Faculty.faculty_id == faculty_id
    ).first()

    if existing_faculty_id:
        raise HTTPException(
            status_code=400,
            detail="Faculty ID already exists"
        )

    department = db.query(Department).filter(
        Department.id == department_id
    ).first()

    if not department:
        raise HTTPException(
            status_code=404,
            detail="Department not found"
        )

    faculty = Faculty(
        user_id=user_id,
        faculty_id=faculty_id,
        name=name,
        phone=phone,
        designation=designation,
        department_id=department_id
    )

    db.add(faculty)
    db.commit()
    db.refresh(faculty)

    return {
        "message": "Faculty profile created successfully",
        "faculty_id": faculty.id,
        "faculty_code": faculty.faculty_id,
        "name": faculty.name,
        "department": department.name,
        "designation": faculty.designation
    }


# --------------------------------------------------
# GET ALL FACULTIES
# --------------------------------------------------

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
            "faculty_id": faculty.faculty_id,
            "name": faculty.name,
            "phone": faculty.phone,
            "designation": faculty.designation,
            "department_id": faculty.department_id,
            "department": faculty.department.name
        })

    return result


# --------------------------------------------------
# GET FACULTY BY ID
# --------------------------------------------------

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
        "faculty_id": faculty.faculty_id,
        "name": faculty.name,
        "phone": faculty.phone,
        "designation": faculty.designation,
        "department_id": faculty.department_id,
        "department": faculty.department.name
    }


# --------------------------------------------------
# DELETE FACULTY PROFILE
# --------------------------------------------------

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

    db.delete(faculty)
    db.commit()

    return {
        "message": "Faculty profile deleted successfully"
    }