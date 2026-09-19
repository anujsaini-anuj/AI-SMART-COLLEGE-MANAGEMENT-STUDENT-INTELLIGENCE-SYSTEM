from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.models import (
    FacultySubject,
    Faculty,
    Subject
)

from app.utils.auth import require_admin


router = APIRouter(
    prefix="/faculty-subjects",
    tags=["Faculty Subject Assignment"]
)


# ============================================================
# ASSIGN SUBJECT TO FACULTY
# ADMIN ONLY
# ============================================================

@router.post("/assign")
def assign_subject_to_faculty(
    faculty_id: int,
    subject_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin)
):

    # --------------------------------------------------------
    # CHECK FACULTY
    # --------------------------------------------------------

    faculty = db.query(Faculty).filter(
        Faculty.id == faculty_id
    ).first()

    if not faculty:
        raise HTTPException(
            status_code=404,
            detail="Faculty not found"
        )

    # --------------------------------------------------------
    # CHECK SUBJECT
    # --------------------------------------------------------

    subject = db.query(Subject).filter(
        Subject.id == subject_id
    ).first()

    if not subject:
        raise HTTPException(
            status_code=404,
            detail="Subject not found"
        )

    # --------------------------------------------------------
    # CHECK DEPARTMENT
    # --------------------------------------------------------

    if faculty.department_id != subject.course.department_id:

        raise HTTPException(
            status_code=400,
            detail="Faculty and subject belong to different departments"
        )

    # --------------------------------------------------------
    # CHECK DUPLICATE ASSIGNMENT
    # --------------------------------------------------------

    existing = db.query(FacultySubject).filter(
        FacultySubject.faculty_id == faculty.id,
        FacultySubject.subject_id == subject.id
    ).first()

    if existing:

        raise HTTPException(
            status_code=400,
            detail="This subject is already assigned to this faculty"
        )

    # --------------------------------------------------------
    # CREATE ASSIGNMENT
    # --------------------------------------------------------

    assignment = FacultySubject(
        faculty_id=faculty.id,
        subject_id=subject.id
    )

    db.add(assignment)
    db.commit()
    db.refresh(assignment)

    return {
        "message": "Subject assigned to faculty successfully",

        "assignment_id":
            assignment.id,

        "faculty_id":
            faculty.faculty_id,

        "faculty_name":
            faculty.name,

        "subject_id":
            subject.id,

        "subject_name":
            subject.name,

        "subject_code":
            subject.code
    }


# ============================================================
# GET ALL FACULTY-SUBJECT ASSIGNMENTS
# ADMIN ONLY
# ============================================================

@router.get("/")
def get_all_assignments(
    db: Session = Depends(get_db),
    current_user=Depends(require_admin)
):

    assignments = db.query(
        FacultySubject
    ).all()

    result = []

    for assignment in assignments:

        faculty = assignment.faculty
        subject = assignment.subject

        result.append({
            "assignment_id":
                assignment.id,

            "faculty_id":
                faculty.faculty_id,

            "faculty_name":
                faculty.name,

            "subject_id":
                subject.id,

            "subject_name":
                subject.name,

            "subject_code":
                subject.code
        })

    return {
        "total_assignments":
            len(result),

        "assignments":
            result
    }


# ============================================================
# GET SUBJECTS ASSIGNED TO A FACULTY
# ADMIN ONLY
# ============================================================

@router.get("/faculty/{faculty_id}")
def get_faculty_subjects(
    faculty_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin)
):

    faculty = db.query(Faculty).filter(
        Faculty.id == faculty_id
    ).first()

    if not faculty:

        raise HTTPException(
            status_code=404,
            detail="Faculty not found"
        )

    assignments = db.query(
        FacultySubject
    ).filter(
        FacultySubject.faculty_id == faculty.id
    ).all()

    result = []

    for assignment in assignments:

        subject = assignment.subject

        result.append({
            "subject_id":
                subject.id,

            "subject_name":
                subject.name,

            "subject_code":
                subject.code
        })

    return {
        "faculty_id":
            faculty.faculty_id,

        "faculty_name":
            faculty.name,

        "subjects":
            result
    }


# ============================================================
# DELETE FACULTY-SUBJECT ASSIGNMENT
# ADMIN ONLY
# ============================================================

@router.delete("/{assignment_id}")
def delete_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin)
):

    assignment = db.query(
        FacultySubject
    ).filter(
        FacultySubject.id == assignment_id
    ).first()

    if not assignment:

        raise HTTPException(
            status_code=404,
            detail="Assignment not found"
        )

    db.delete(assignment)
    db.commit()

    return {
        "message":
            "Faculty subject assignment deleted successfully"
    }