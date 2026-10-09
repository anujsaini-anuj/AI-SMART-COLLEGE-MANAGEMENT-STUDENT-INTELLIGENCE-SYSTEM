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

from app.services.performance_service import calculate_and_update_performance
from app.services.prediction_service import create_historical_ml_record


router = APIRouter(
    prefix="/marks",
    tags=["Marks Management"]
)


# ============================================================
# ADD / UPDATE MARKS
# ============================================================

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

    # 1. Faculty-subject authorization

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

    # 2. Student validation

    student = db.query(Student).filter(
        Student.student_id == student_id
    ).first()

    if not student:
        raise HTTPException(
            status_code=404,
            detail="Student not found"
        )

    if hasattr(student, "is_active") and not student.is_active:
        raise HTTPException(
            status_code=400,
            detail="Student is inactive"
        )

    # 3. Subject validation

    subject = db.query(Subject).filter(
        Subject.id == subject_id
    ).first()

    if not subject:
        raise HTTPException(
            status_code=404,
            detail="Subject not found"
        )

    # 4. Student-course and semester validation

    if student.course_id != subject.course_id:
        raise HTTPException(
            status_code=400,
            detail=(
                "Student is not enrolled in this subject. "
                "Student belongs to a different course."
            )
        )

    if student.semester != subject.semester:
        raise HTTPException(
            status_code=400,
            detail=(
                "Student is not enrolled in this subject. "
                "The student's current semester does not match "
                "the subject semester."
            )
        )

    # 5. Exam type validation

    exam_type = exam_type.strip()

    if not exam_type:
        raise HTTPException(
            status_code=400,
            detail="Exam type is required"
        )

    # 6. Marks validation

    if max_marks <= 0:
        raise HTTPException(
            status_code=400,
            detail="Maximum marks must be greater than 0"
        )

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

    # 7. Final exam date validation

    is_final_exam = "final" in exam_type.lower()

    if is_final_exam and exam_date is None:
        raise HTTPException(
            status_code=400,
            detail="Exam date is required for Final Exam marks"
        )

    # 8. Add or update marks

    existing_marks = db.query(Marks).filter(
        Marks.student_id == student_id,
        Marks.subject_id == subject_id,
        Marks.exam_type == exam_type
    ).first()

    action = "added"

    if existing_marks:
        existing_marks.marks_obtained = marks_obtained
        existing_marks.max_marks = max_marks
        existing_marks.exam_date = exam_date

        marks = existing_marks
        action = "updated"

    else:
        marks = Marks(
            student_id=student_id,
            subject_id=subject_id,
            exam_type=exam_type,
            marks_obtained=marks_obtained,
            max_marks=max_marks,
            exam_date=exam_date
        )

        db.add(marks)

    # 9. Save marks first

    try:
        db.commit()
        db.refresh(marks)

    except Exception as e:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Failed to save marks: {str(e)}"
        )

    # ========================================================
    # AUTOMATIC ACADEMIC PIPELINE
    # ========================================================

    automation = {
        "performance": {
            "status": "not_run"
        },
        "risk": {
            "status": "not_run"
        },
        "ml_record": {
            "status": "not_required"
        },
        "model_training": {
            "status": "not_required"
        }
    }

    # 10. Automatically calculate performance and risk

    try:
        performance_result = calculate_and_update_performance(
            db=db,
            student_id=student_id,
            subject_id=subject_id
        )

        automation["performance"] = {
            "status": "updated",
            "data": performance_result
        }

        automation["risk"] = {
            "status": "updated",
            "message": "Student risk updated automatically"
        }

    except Exception as e:
        automation["performance"] = {
            "status": "failed",
            "error": str(e)
        }

        automation["risk"] = {
            "status": "failed",
            "error": (
                "Risk was not updated because "
                "performance calculation failed"
            )
        }

    # 11. Final exam -> historical ML record
    # This function returns exactly 3 values.
    # Retraining is handled separately by the ML scheduler.

    if is_final_exam:
        try:
            ml_record, features, final_percentage = (
                create_historical_ml_record(
                    db=db,
                    student_id=student_id,
                    subject_id=subject_id
                )
            )

            automation["ml_record"] = {
                "status": "updated",
                "ml_record_id": ml_record.id,
                "final_exam_percentage": final_percentage,
                "features": features
            }

            automation["model_training"] = {
                "status": "pending_scheduler_check",
                "message": (
                    "Historical ML record saved successfully. "
                    "The automatic scheduler will check whether "
                    "model retraining is required."
                )
            }

        except Exception as e:
            automation["ml_record"] = {
                "status": "failed",
                "error": str(e)
            }

            automation["model_training"] = {
                "status": "not_completed",
                "message": (
                    "Marks were saved successfully, but automatic "
                    "ML processing could not be completed."
                )
            }

    # 12. Response

    return {
        "message": f"Marks {action} successfully",

        "marks": {
            "marks_id": marks.id,
            "student_id": student.student_id,
            "student_name": student.name,
            "subject_id": subject.id,
            "subject_name": subject.name,
            "exam_type": marks.exam_type,
            "marks_obtained": marks.marks_obtained,
            "max_marks": marks.max_marks,
            "percentage": round(
                (marks.marks_obtained / marks.max_marks) * 100,
                2
            ),
            "exam_date": marks.exam_date
        },

        "automatic_processing": automation
    }


# ============================================================
# FACULTY VIEW MARKS
# ============================================================

@router.get("/")
def get_all_marks(
    db: Session = Depends(get_db),
    current_faculty=Depends(require_faculty)
):

    assigned_subject_ids = db.query(
        FacultySubject.subject_id
    ).filter(
        FacultySubject.faculty.has(
            user_id=current_faculty.id
        )
    ).all()

    assigned_subject_ids = [
        item[0] for item in assigned_subject_ids
    ]

    if not assigned_subject_ids:
        return {
            "total_records": 0,
            "marks": []
        }

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
            "percentage": round(
                (marks.marks_obtained / marks.max_marks) * 100,
                2
            ),
            "exam_date": marks.exam_date
        })

    return {
        "total_records": len(result),
        "marks": result
    }


# ============================================================
# STUDENT VIEW OWN MARKS
# ============================================================

@router.get("/my-marks")
def get_my_marks(
    db: Session = Depends(get_db),
    current_student=Depends(require_student)
):

    student = db.query(Student).filter(
        Student.user_id == current_student.id
    ).first()

    if not student:
        raise HTTPException(
            status_code=404,
            detail="Student profile not found"
        )

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
            "percentage": round(
                (marks.marks_obtained / marks.max_marks) * 100,
                2
            ),
            "exam_date": marks.exam_date
        })

    return {
        "student_id": student.student_id,
        "student_name": student.name,
        "total_records": len(result),
        "marks": result
    }