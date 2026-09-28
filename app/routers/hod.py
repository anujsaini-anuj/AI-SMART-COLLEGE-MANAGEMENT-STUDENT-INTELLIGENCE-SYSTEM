from fastapi import APIRouter, Depends, HTTPException

from sqlalchemy.orm import Session

from app.database.database import get_db

from app.database.models import (
    HOD,
    Faculty,
    User
)

from app.utils.auth import get_current_hod


router = APIRouter(
    prefix="/hod",
    tags=["HOD Management"]
)


# ==================================================
# GET HOD PROFILE
# ==================================================

@router.get("/me")
def get_hod_profile(
    current_hod: HOD = Depends(get_current_hod)
):

    return {
        "hod_id": current_hod.hod_id,
        "user_id": current_hod.user_id,
        "name": current_hod.user.name,
        "email": current_hod.user.email,
        "phone": current_hod.phone,
        "department_id": current_hod.department_id,
        "department": current_hod.department.name,
        "role": current_hod.user.role
    }


# ==================================================
# GET FACULTY OF HOD'S DEPARTMENT
# ==================================================

@router.get("/faculties")
def get_department_faculties(
    current_hod: HOD = Depends(get_current_hod),
    db: Session = Depends(get_db)
):

    faculties = db.query(Faculty).filter(
        Faculty.department_id == current_hod.department_id
    ).all()

    result = []

    for faculty in faculties:

        result.append({
            "faculty_id": faculty.faculty_id,
            "name": faculty.name,
            "email": faculty.user.email,
            "phone": faculty.phone,
            "designation": faculty.designation,
            "department_id": faculty.department_id,
            "department": faculty.department.name
        })

    return {
        "department_id": current_hod.department_id,
        "department": current_hod.department.name,
        "total_faculty": len(result),
        "faculties": result
    }