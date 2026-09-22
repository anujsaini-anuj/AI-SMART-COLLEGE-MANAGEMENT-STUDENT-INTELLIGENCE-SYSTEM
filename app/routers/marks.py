from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.models import (
    Marks,
    Student,
    Subject,
    FacultySubject
)
from app.utils.auth import require_faculty, require_student


router = APIRouter(
    prefix="/marks",
    tags=["Marks Management"]
)


# ==================================================
# ADD MARKS
# ==================================================

@router.post("/add")
def add_marks(
    student_id: str,
    subject_id: int,
    exam_type: str,
    marks_obtained: int,
    max_marks: int,
    exam_date: date = None,

    db: Session = Depends(get_db),
    current_faculty=Depends(require_faculty)
):

    # ------------------------------------------------
    # CHECK FACULTY SUBJECT AUTHORIZATION
    # ------------------------------------------------

    faculty_subject = db.query(FacultySubject).filter(
        FacultySubject.subject_id == subject_id,
        FacultySubject.faculty.has(
            user_id=current_faculty.id
        )
    ).first()

    if not faculty_subject:
        raise HTTPException(
            status_code=403,
            detail="You are not assigned to this subject"
        )


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
    # CHECK DUPLICATE
    # ------------------------------------------------

    existing_marks = db.query(Marks).filter(
        Marks.student_id == student_id,
        Marks.subject_id == subject_id,
        Marks.exam_type == exam_type
    ).first()

    if existing_marks:
        raise HTTPException(
            status_code=400,
            detail="Marks already added for this student, subject and exam type"
        )


    # ------------------------------------------------
    # CREATE MARKS
    # ------------------------------------------------

    marks = Marks(
        student_id=student_id,
        subject_id=subject_id,
        exam_type=exam_type,
        marks_obtained=marks_obtained,
        max_marks=max_marks,
        exam_date=exam_date
    )

    db.add(marks)

    try:
        db.commit()
        db.refresh(marks)

    except Exception:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Failed to add marks"
        )


    # ------------------------------------------------
    # RESPONSE
    # ------------------------------------------------

    return {
        "message": "Marks added successfully",
        "marks_id": marks.id,
        "student_id": student.student_id,
        "student_name": student.name,
        "subject_id": subject.id,
        "subject_name": subject.name,
        "exam_type": marks.exam_type,
        "marks_obtained": marks.marks_obtained,
        "max_marks": marks.max_marks,
        "exam_date": marks.exam_date
    }


# ==================================================
# FACULTY - VIEW MARKS
# ==================================================

@router.get("/")
def get_all_marks(
    db: Session = Depends(get_db),
    current_faculty=Depends(require_faculty)
):

    # ------------------------------------------------
    # GET SUBJECTS ASSIGNED TO CURRENT FACULTY
    # ------------------------------------------------

    assigned_subject_ids = db.query(
        FacultySubject.subject_id
    ).filter(
        FacultySubject.faculty.has(
            user_id=current_faculty.id
        )
    ).all()

    assigned_subject_ids = [
        subject_id[0]
        for subject_id in assigned_subject_ids
    ]


    # ------------------------------------------------
    # NO ASSIGNED SUBJECT
    # ------------------------------------------------

    if not assigned_subject_ids:
        return {
            "total_records": 0,
            "marks": []
        }


    # ------------------------------------------------
    # GET ONLY ASSIGNED SUBJECT MARKS
    # ------------------------------------------------

    marks_records = db.query(Marks).filter(
        Marks.subject_id.in_(assigned_subject_ids)
    ).all()


    result = []

    for marks in marks_records:

        result.append({
            "marks_id": marks.id,
            "student_id": marks.student.student_id,
            "student_name": marks.student.name,
            "subject_id": marks.subject.id,
            "subject_name": marks.subject.name,
            "exam_type": marks.exam_type,
            "marks_obtained": marks.marks_obtained,
            "max_marks": marks.max_marks,
            "exam_date": marks.exam_date
        })


    return {
        "total_records": len(result),
        "marks": result
    }


# ==================================================
# STUDENT - VIEW OWN MARKS
# ==================================================

@router.get("/my-marks")
def get_my_marks(
    db: Session = Depends(get_db),
    current_student=Depends(require_student)
):

    # ------------------------------------------------
    # GET CURRENT STUDENT PROFILE
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
    # GET ONLY CURRENT STUDENT MARKS
    # ------------------------------------------------

    marks_records = db.query(Marks).filter(
        Marks.student_id == student.student_id
    ).all()


    result = []

    for marks in marks_records:

        result.append({
            "marks_id": marks.id,
            "subject_id": marks.subject.id,
            "subject_name": marks.subject.name,
            "exam_type": marks.exam_type,
            "marks_obtained": marks.marks_obtained,
            "max_marks": marks.max_marks,
            "exam_date": marks.exam_date
        })


    return {
        "student_id": student.student_id,
        "student_name": student.name,
        "total_records": len(result),
        "marks": result
    }