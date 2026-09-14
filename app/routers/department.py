from fastapi import APIRouter, Depends, HTTPException, Form

from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.models import Department, User

from app.utils.auth import require_admin


router = APIRouter(
    prefix="/departments",
    tags=["Departments"]
)


# --------------------------------------------------
# CREATE DEPARTMENT
# --------------------------------------------------

@router.post("/create")
def create_department(
    name: str = Form(...),
    code: str = Form(...),
    description: str | None = Form(None),

    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin)
):

    existing_department = db.query(Department).filter(
        (Department.name == name) |
        (Department.code == code)
    ).first()

    if existing_department:
        raise HTTPException(
            status_code=400,
            detail="Department name or code already exists"
        )

    department = Department(
        name=name,
        code=code,
        description=description
    )

    db.add(department)
    db.commit()
    db.refresh(department)

    return {
        "message": "Department created successfully",
        "department_id": department.id,
        "name": department.name,
        "code": department.code,
        "description": department.description
    }


# --------------------------------------------------
# GET ALL DEPARTMENTS
# --------------------------------------------------

@router.get("/")
def get_departments(
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin)
):

    departments = db.query(Department).all()

    return departments


# --------------------------------------------------
# GET DEPARTMENT BY ID
# --------------------------------------------------

@router.get("/{department_id}")
def get_department(
    department_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin)
):

    department = db.query(Department).filter(
        Department.id == department_id
    ).first()

    if not department:
        raise HTTPException(
            status_code=404,
            detail="Department not found"
        )

    return department


# --------------------------------------------------
# DELETE DEPARTMENT
# --------------------------------------------------

@router.delete("/{department_id}")
def delete_department(
    department_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin)
):

    department = db.query(Department).filter(
        Department.id == department_id
    ).first()

    if not department:
        raise HTTPException(
            status_code=404,
            detail="Department not found"
        )

    db.delete(department)
    db.commit()

    return {
        "message": "Department deleted successfully"
    }