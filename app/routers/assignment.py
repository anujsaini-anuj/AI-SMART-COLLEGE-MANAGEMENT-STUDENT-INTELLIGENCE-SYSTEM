from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.models import (
    Assignment,
    Student,
    Subject
)

from app.utils.auth import (
    require_faculty,
    require_student
)


router = APIRouter(
    prefix="/assignments",
    tags=["Assignment Management"]
)


# ==================================================
# ADD ASSIGNMENT
# ==================================================

@router.post("/add")
def add_assignment(

    student_id: str,
    subject_id: int,
    assignment_name: str,
    max_marks: int,
    marks_obtained: int | None = None,
    submission_date: date | None = None,
    status: str = "Pending",

    db: Session = Depends(get_db),

    current_faculty=Depends(require_faculty)
):

    status = status.strip().lower()

    if status not in ["pending", "submitted", "late"]:
        raise HTTPException(
            status_code=400,
            detail="Status must be Pending, Submitted or Late"
        )

    # Convert to standard format
    status_map = {
        "pending": "Pending",
        "submitted": "Submitted",
        "late": "Late"
    }

    status = status_map[status]


    # ------------------------------------------------
    # CHECK STUDENT
    # ------------------------------------------------

    student = db.query(Student).filter(
        Student.student_id == student_id
    ).first()

    if not student:

        raise HTTPException(
            status_code=404,
            detail="Student not found"
        )


    # ------------------------------------------------
    # CHECK SUBJECT
    # ------------------------------------------------

    subject = db.query(Subject).filter(
        Subject.id == subject_id
    ).first()

    if not subject:

        raise HTTPException(
            status_code=404,
            detail="Subject not found"
        )


    # ------------------------------------------------
    # VALIDATE MAX MARKS
    # ------------------------------------------------

    if max_marks <= 0:

        raise HTTPException(
            status_code=400,
            detail="Maximum marks must be greater than 0"
        )


    # ------------------------------------------------
    # VALIDATE OBTAINED MARKS
    # ------------------------------------------------

    if marks_obtained is not None:

        if marks_obtained < 0:

            raise HTTPException(
                status_code=400,
                detail="Marks cannot be negative"
            )

        if marks_obtained > max_marks:

            raise HTTPException(
                status_code=400,
                detail="Obtained marks cannot be greater than maximum marks"
            )


    # ------------------------------------------------
    # STATUS / MARKS VALIDATION
    # ------------------------------------------------

    if status in ["Submitted", "Late"]:

        if marks_obtained is None:

            raise HTTPException(
                status_code=400,
                detail="Marks are required for submitted assignment"
            )


    # ------------------------------------------------
    # CHECK DUPLICATE
    # ------------------------------------------------

    existing_assignment = db.query(Assignment).filter(
        Assignment.student_id == student_id,
        Assignment.subject_id == subject_id,
        Assignment.assignment_name == assignment_name
    ).first()

    if existing_assignment:

        raise HTTPException(
            status_code=400,
            detail="This assignment already exists for this student and subject"
        )


    # ------------------------------------------------
    # CREATE ASSIGNMENT
    # ------------------------------------------------

    assignment = Assignment(

        student_id=student_id,

        subject_id=subject_id,

        assignment_name=assignment_name,

        marks_obtained=marks_obtained,

        max_marks=max_marks,

        submission_date=submission_date,

        status=status
    )

    db.add(assignment)


    # ------------------------------------------------
    # SAVE
    # ------------------------------------------------

    try:

        db.commit()

        db.refresh(assignment)

    except Exception:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Failed to add assignment"
        )


    # ------------------------------------------------
    # RESPONSE
    # ------------------------------------------------

    return {

        "message": "Assignment added successfully",

        "assignment_id": assignment.id,

        "student_id": student.student_id,

        "student_name": student.name,

        "subject_id": subject.id,

        "subject_name": subject.name,

        "assignment_name": assignment.assignment_name,

        "marks_obtained": assignment.marks_obtained,

        "max_marks": assignment.max_marks,

        "submission_date": assignment.submission_date,

        "status": assignment.status
    }


# ==================================================
# FACULTY - VIEW ALL ASSIGNMENTS
# ==================================================

@router.get("/")
def get_all_assignments(

    db: Session = Depends(get_db),

    current_faculty=Depends(require_faculty)
):

    assignments = db.query(
        Assignment
    ).all()

    result = []

    for assignment in assignments:

        result.append({

            "assignment_id": assignment.id,

            "student_id": assignment.student.student_id,

            "student_name": assignment.student.name,

            "subject_id": assignment.subject.id,

            "subject_name": assignment.subject.name,

            "assignment_name": assignment.assignment_name,

            "marks_obtained": assignment.marks_obtained,

            "max_marks": assignment.max_marks,

            "submission_date": assignment.submission_date,

            "status": assignment.status
        })


    return {

        "total_records": len(result),

        "assignments": result
    }


# ==================================================
# STUDENT - VIEW OWN ASSIGNMENTS
# ==================================================

@router.get("/my-assignments")
def get_my_assignments(

    db: Session = Depends(get_db),

    current_student=Depends(require_student)
):

    # ------------------------------------------------
    # FIND STUDENT PROFILE
    # ------------------------------------------------

    student = db.query(Student).filter(
        Student.user_id == current_student.id
    ).first()

    if not student:

        raise HTTPException(
            status_code=404,
            detail="Student profile not found"
        )


    # ------------------------------------------------
    # GET OWN ASSIGNMENTS
    # ------------------------------------------------

    assignments = db.query(
        Assignment
    ).filter(
        Assignment.student_id == student.student_id
    ).all()


    result = []

    for assignment in assignments:

        result.append({

            "assignment_id": assignment.id,

            "subject_id": assignment.subject.id,

            "subject_name": assignment.subject.name,

            "assignment_name": assignment.assignment_name,

            "marks_obtained": assignment.marks_obtained,

            "max_marks": assignment.max_marks,

            "submission_date": assignment.submission_date,

            "status": assignment.status
        })


    return {

        "student_id": student.student_id,

        "student_name": student.name,

        "total_records": len(result),

        "assignments": result
    }