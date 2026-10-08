from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Form
)

from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.models import (
    Subject,
    Course,
    User
)

from app.utils.auth import (
    require_admin,
    require_faculty
)


router = APIRouter(
    prefix="/subjects",
    tags=["Subject Management"]
)


# ==================================================
# HELPER
# GET MAXIMUM SEMESTER FROM COURSE DURATION
# ==================================================

def get_max_semester(duration_years: int) -> int:

    if duration_years <= 0:
        raise HTTPException(
            status_code=400,
            detail="Course duration must be greater than 0 years."
        )

    return duration_years * 2


# --------------------------------------------------
# CREATE SUBJECT
# --------------------------------------------------

@router.post("/create")
def create_subject(
    name: str = Form(...),
    code: str = Form(...),
    credits: int = Form(...),
    semester: int = Form(..., ge=1),
    course_id: int = Form(...),
    description: str | None = Form(None),

    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin)
):

    # --------------------------------------------------
    # CLEAN INPUT
    # --------------------------------------------------

    name = name.strip()
    code = code.strip().upper()

    if not name:
        raise HTTPException(
            status_code=400,
            detail="Subject name cannot be empty."
        )

    if not code:
        raise HTTPException(
            status_code=400,
            detail="Subject code cannot be empty."
        )

    # --------------------------------------------------
    # CHECK DUPLICATE SUBJECT CODE
    # --------------------------------------------------

    existing_subject = db.query(Subject).filter(
        Subject.code == code
    ).first()

    if existing_subject:
        raise HTTPException(
            status_code=400,
            detail="Subject code already exists."
        )

    # --------------------------------------------------
    # CHECK COURSE
    # --------------------------------------------------

    course = db.query(Course).filter(
        Course.id == course_id
    ).first()

    if not course:
        raise HTTPException(
            status_code=404,
            detail="Course not found."
        )

    # --------------------------------------------------
    # GET MAXIMUM SEMESTER
    # --------------------------------------------------

    max_semester = get_max_semester(
        course.duration
    )

    # --------------------------------------------------
    # VALIDATE CREDITS
    # --------------------------------------------------

    if credits <= 0:
        raise HTTPException(
            status_code=400,
            detail="Credits must be greater than 0."
        )

    # --------------------------------------------------
    # VALIDATE SEMESTER ACCORDING TO COURSE DURATION
    # --------------------------------------------------

    if semester > max_semester:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid semester for this course. "
                f"{course.name} has a duration of "
                f"{course.duration} year(s), so the maximum "
                f"allowed semester is {max_semester}."
            )
        )

    # --------------------------------------------------
    # CREATE SUBJECT
    # --------------------------------------------------

    subject = Subject(
        name=name,
        code=code,
        credits=credits,
        semester=semester,
        course_id=course_id,
        description=description
    )

    db.add(subject)

    try:
        db.commit()
        db.refresh(subject)

    except Exception as e:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Failed to create subject: {str(e)}"
        )

    # --------------------------------------------------
    # RESPONSE
    # --------------------------------------------------

    return {
        "message": "Subject created successfully",
        "subject_id": subject.id,
        "name": subject.name,
        "code": subject.code,
        "credits": subject.credits,
        "semester": subject.semester,
        "course": course.name,
        "course_duration_years": course.duration,
        "maximum_semester": max_semester,
        "description": subject.description
    }


# --------------------------------------------------
# GET ALL SUBJECTS
# --------------------------------------------------

@router.get("/")
def get_all_subjects(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_faculty)
):

    subjects = db.query(Subject).all()

    result = []

    for subject in subjects:

        max_semester = get_max_semester(
            subject.course.duration
        )

        result.append({
            "id": subject.id,
            "name": subject.name,
            "code": subject.code,
            "credits": subject.credits,
            "semester": subject.semester,
            "description": subject.description,
            "course_id": subject.course_id,
            "course": subject.course.name,
            "course_duration_years": subject.course.duration,
            "maximum_semester": max_semester
        })

    return result


# --------------------------------------------------
# GET SUBJECT BY ID
# --------------------------------------------------

@router.get("/{subject_id}")
def get_subject(
    subject_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_faculty)
):

    subject = db.query(Subject).filter(
        Subject.id == subject_id
    ).first()

    if not subject:
        raise HTTPException(
            status_code=404,
            detail="Subject not found"
        )

    max_semester = get_max_semester(
        subject.course.duration
    )

    return {
        "id": subject.id,
        "name": subject.name,
        "code": subject.code,
        "credits": subject.credits,
        "semester": subject.semester,
        "description": subject.description,
        "course_id": subject.course_id,
        "course": subject.course.name,
        "course_duration_years": subject.course.duration,
        "maximum_semester": max_semester
    }


# --------------------------------------------------
# UPDATE SUBJECT
# --------------------------------------------------

@router.put("/{subject_id}")
def update_subject(
    subject_id: int,

    name: str = Form(...),
    code: str = Form(...),
    credits: int = Form(...),
    semester: int = Form(..., ge=1),
    course_id: int = Form(...),
    description: str | None = Form(None),

    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin)
):

    # --------------------------------------------------
    # FIND SUBJECT
    # --------------------------------------------------

    subject = db.query(Subject).filter(
        Subject.id == subject_id
    ).first()

    if not subject:
        raise HTTPException(
            status_code=404,
            detail="Subject not found"
        )

    # --------------------------------------------------
    # CLEAN INPUT
    # --------------------------------------------------

    name = name.strip()
    code = code.strip().upper()

    if not name:
        raise HTTPException(
            status_code=400,
            detail="Subject name cannot be empty."
        )

    if not code:
        raise HTTPException(
            status_code=400,
            detail="Subject code cannot be empty."
        )

    # --------------------------------------------------
    # CHECK DUPLICATE CODE
    # --------------------------------------------------

    existing_subject = db.query(Subject).filter(
        Subject.code == code,
        Subject.id != subject_id
    ).first()

    if existing_subject:
        raise HTTPException(
            status_code=400,
            detail="Subject code already exists."
        )

    # --------------------------------------------------
    # CHECK COURSE
    # --------------------------------------------------

    course = db.query(Course).filter(
        Course.id == course_id
    ).first()

    if not course:
        raise HTTPException(
            status_code=404,
            detail="Course not found."
        )

    # --------------------------------------------------
    # GET MAXIMUM SEMESTER
    # --------------------------------------------------

    max_semester = get_max_semester(
        course.duration
    )

    # --------------------------------------------------
    # VALIDATE CREDITS
    # --------------------------------------------------

    if credits <= 0:
        raise HTTPException(
            status_code=400,
            detail="Credits must be greater than 0."
        )

    # --------------------------------------------------
    # VALIDATE SEMESTER ACCORDING TO COURSE
    # --------------------------------------------------

    if semester > max_semester:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid semester for this course. "
                f"{course.name} has a duration of "
                f"{course.duration} year(s), so the maximum "
                f"allowed semester is {max_semester}."
            )
        )

    # --------------------------------------------------
    # UPDATE SUBJECT
    # --------------------------------------------------

    subject.name = name
    subject.code = code
    subject.credits = credits
    subject.semester = semester
    subject.course_id = course_id
    subject.description = description

    try:
        db.commit()
        db.refresh(subject)

    except Exception as e:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Failed to update subject: {str(e)}"
        )

    # --------------------------------------------------
    # RESPONSE
    # --------------------------------------------------

    return {
        "message": "Subject updated successfully",
        "subject_id": subject.id,
        "name": subject.name,
        "code": subject.code,
        "credits": subject.credits,
        "semester": subject.semester,
        "course": course.name,
        "course_duration_years": course.duration,
        "maximum_semester": max_semester,
        "description": subject.description
    }


# --------------------------------------------------
# DELETE SUBJECT
# --------------------------------------------------

@router.delete("/{subject_id}")
def delete_subject(
    subject_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin)
):

    subject = db.query(Subject).filter(
        Subject.id == subject_id
    ).first()

    if not subject:
        raise HTTPException(
            status_code=404,
            detail="Subject not found"
        )

    db.delete(subject)
    db.commit()

    return {
        "message": "Subject deleted successfully"
    }