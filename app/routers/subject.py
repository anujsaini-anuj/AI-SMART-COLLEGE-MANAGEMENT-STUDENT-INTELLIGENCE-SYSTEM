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


# --------------------------------------------------
# CREATE SUBJECT
# --------------------------------------------------

@router.post("/create")
def create_subject(
    name: str = Form(...),
    code: str = Form(...),
    credits: int = Form(...),
    semester: int = Form(...),
    course_id: int = Form(...),
    description: str | None = Form(None),

    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin)
):

    # Check subject code
    existing_subject = db.query(Subject).filter(
        Subject.code == code
    ).first()

    if existing_subject:
        raise HTTPException(
            status_code=400,
            detail="Subject code already exists"
        )

    # Check course
    course = db.query(Course).filter(
        Course.id == course_id
    ).first()

    if not course:
        raise HTTPException(
            status_code=404,
            detail="Course not found"
        )

    # Validate credits
    if credits <= 0:
        raise HTTPException(
            status_code=400,
            detail="Credits must be greater than 0"
        )

    # Validate semester
    if semester < 1 or semester > 12:
        raise HTTPException(
            status_code=400,
            detail="Semester must be between 1 and 12"
        )

    subject = Subject(
        name=name,
        code=code,
        credits=credits,
        semester=semester,
        course_id=course_id,
        description=description
    )

    db.add(subject)
    db.commit()
    db.refresh(subject)

    return {
        "message": "Subject created successfully",
        "subject_id": subject.id,
        "name": subject.name,
        "code": subject.code,
        "credits": subject.credits,
        "semester": subject.semester,
        "course": course.name,
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

        result.append({
            "id": subject.id,
            "name": subject.name,
            "code": subject.code,
            "credits": subject.credits,
            "semester": subject.semester,
            "description": subject.description,
            "course_id": subject.course_id,
            "course": subject.course.name
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

    return {
        "id": subject.id,
        "name": subject.name,
        "code": subject.code,
        "credits": subject.credits,
        "semester": subject.semester,
        "description": subject.description,
        "course_id": subject.course_id,
        "course": subject.course.name
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
    semester: int = Form(...),
    course_id: int = Form(...),
    description: str | None = Form(None),

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

    # Check duplicate code
    existing_subject = db.query(Subject).filter(
        Subject.code == code,
        Subject.id != subject_id
    ).first()

    if existing_subject:
        raise HTTPException(
            status_code=400,
            detail="Subject code already exists"
        )

    # Check course
    course = db.query(Course).filter(
        Course.id == course_id
    ).first()

    if not course:
        raise HTTPException(
            status_code=404,
            detail="Course not found"
        )

    if credits <= 0:
        raise HTTPException(
            status_code=400,
            detail="Credits must be greater than 0"
        )

    if semester < 1 or semester > 12:
        raise HTTPException(
            status_code=400,
            detail="Semester must be between 1 and 12"
        )

    subject.name = name
    subject.code = code
    subject.credits = credits
    subject.semester = semester
    subject.course_id = course_id
    subject.description = description

    db.commit()
    db.refresh(subject)

    return {
        "message": "Subject updated successfully",
        "subject_id": subject.id,
        "name": subject.name,
        "code": subject.code,
        "credits": subject.credits,
        "semester": subject.semester,
        "course": course.name,
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