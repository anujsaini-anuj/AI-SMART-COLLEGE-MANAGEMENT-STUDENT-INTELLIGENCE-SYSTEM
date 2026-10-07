from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.database import get_db

from app.database.models import (
    Performance,
    Student,
    FacultySubject
)

from app.utils.auth import (
    require_faculty,
    require_student
)

from app.services.performance_service import calculate_and_update_performance


router = APIRouter(
    prefix="/performance",
    tags=["Performance Management"]
)


# ==================================================
# PERFORMANCE RULES
# ==================================================

# Minimum attendance required to be eligible
MIN_ATTENDANCE_PERCENTAGE = 75

# Minimum academic percentage required to PASS
MIN_ACADEMIC_PERCENTAGE = 40

# Academic performance weights
MARKS_WEIGHT = 0.70
ASSIGNMENT_WEIGHT = 0.30


# ==================================================
# CALCULATE STUDENT PERFORMANCE
# ==================================================
@router.post("/calculate")
def calculate_performance(
    student_id: str,
    subject_id: int,
    db: Session = Depends(get_db),
    current_faculty=Depends(require_faculty)
):
    # ==========================================
    # FACULTY SUBJECT AUTHORIZATION
    # ==========================================

    faculty_subject = (
        db.query(FacultySubject)
        .filter(
            FacultySubject.subject_id == subject_id,
            FacultySubject.faculty.has(
                user_id=current_faculty.id
            )
        )
        .first()
    )

    if not faculty_subject:
        raise HTTPException(
            status_code=403,
            detail="You are not assigned to this subject"
        )

    # ==========================================
    # CALCULATE PERFORMANCE
    # ==========================================

    try:
        result = calculate_and_update_performance(
            db=db,
            student_id=student_id,
            subject_id=subject_id
        )

    except HTTPException:
        raise

    except Exception as e:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Failed to calculate performance: {str(e)}"
        )

    # ==========================================
    # RESPONSE
    # ==========================================

    return {
        "message": "Performance and student risk calculated successfully",

        **result,

        "rules": {
            "minimum_attendance": MIN_ATTENDANCE_PERCENTAGE,
            "minimum_academic_percentage": MIN_ACADEMIC_PERCENTAGE,
            "marks_weight": "70%",
            "assignment_weight": "30%"
        }
    }


# ==================================================
# GET ALL PERFORMANCE - FACULTY
# ==================================================

@router.get("/")
def get_all_performance(

    db: Session = Depends(get_db),

    current_faculty=Depends(require_faculty)
):

    assigned_subject_ids = [

        item.subject_id

        for item in (
            db.query(FacultySubject)
            .filter(
                FacultySubject.faculty.has(
                    user_id=current_faculty.id
                )
            )
            .all()
        )
    ]


    if not assigned_subject_ids:

        return {

            "total_records": 0,

            "performance": []
        }


    performance_records = (
        db.query(Performance)
        .filter(
            Performance.subject_id.in_(
                assigned_subject_ids
            )
        )
        .all()
    )


    result = []

    for performance in performance_records:

        result.append({

            "performance_id":
                performance.id,

            "student_id":
                performance.student.student_id,

            "student_name":
                performance.student.name,

            "subject_id":
                performance.subject.id,

            "subject_name":
                performance.subject.name,

            "attendance_percentage":
                performance.attendance_percentage,

            "marks_percentage":
                performance.marks_percentage,

            "assignment_percentage":
                performance.assignment_percentage,

            "academic_percentage":
                performance.overall_percentage,

            "pass_status":
                performance.pass_status,

            "performance_level":
                performance.performance_level

        })


    return {

        "total_records":
            len(result),

        "performance":
            result
    }


# ==================================================
# GET PARTICULAR STUDENT PERFORMANCE - FACULTY
# ==================================================

@router.get("/student/{student_id}")
def get_student_performance(

    student_id: str,

    db: Session = Depends(get_db),

    current_faculty=Depends(require_faculty)
):

    student = (
        db.query(Student)
        .filter(
            Student.student_id == student_id
        )
        .first()
    )

    if not student:

        raise HTTPException(
            status_code=404,
            detail="Student not found"
        )


    assigned_subject_ids = [

        item.subject_id

        for item in (
            db.query(FacultySubject)
            .filter(
                FacultySubject.faculty.has(
                    user_id=current_faculty.id
                )
            )
            .all()
        )
    ]


    if not assigned_subject_ids:

        return {

            "student_id":
                student.student_id,

            "student_name":
                student.name,

            "total_subjects":
                0,

            "performance":
                []
        }


    performance_records = (
        db.query(Performance)
        .filter(

            Performance.student_id == student_id,

            Performance.subject_id.in_(
                assigned_subject_ids
            )

        )
        .all()
    )


    return {

        "student_id":
            student.student_id,

        "student_name":
            student.name,

        "total_subjects":
            len(performance_records),

        "performance": [

            {

                "performance_id":
                    performance.id,

                "subject_id":
                    performance.subject.id,

                "subject_name":
                    performance.subject.name,

                "attendance_percentage":
                    performance.attendance_percentage,

                "marks_percentage":
                    performance.marks_percentage,

                "assignment_percentage":
                    performance.assignment_percentage,

                "academic_percentage":
                    performance.overall_percentage,

                "pass_status":
                    performance.pass_status,

                "performance_level":
                    performance.performance_level

            }

            for performance
            in performance_records

        ]
    }


# ==================================================
# GET MY PERFORMANCE - STUDENT
# ==================================================

@router.get("/my-performance")
def get_my_performance(

    db: Session = Depends(get_db),

    current_student=Depends(require_student)
):

    student = (
        db.query(Student)
        .filter(
            Student.user_id == current_student.id
        )
        .first()
    )

    if not student:

        raise HTTPException(
            status_code=404,
            detail="Student profile not found"
        )


    performance_records = (
        db.query(Performance)
        .filter(
            Performance.student_id ==
            student.student_id
        )
        .all()
    )


    return {

        "student_id":
            student.student_id,

        "student_name":
            student.name,

        "total_subjects":
            len(performance_records),

        "performance": [

            {

                "performance_id":
                    performance.id,

                "subject_id":
                    performance.subject.id,

                "subject_name":
                    performance.subject.name,

                "attendance_percentage":
                    performance.attendance_percentage,

                "marks_percentage":
                    performance.marks_percentage,

                "assignment_percentage":
                    performance.assignment_percentage,

                "academic_percentage":
                    performance.overall_percentage,

                "pass_status":
                    performance.pass_status,

                "performance_level":
                    performance.performance_level

            }

            for performance
            in performance_records

        ]
    }