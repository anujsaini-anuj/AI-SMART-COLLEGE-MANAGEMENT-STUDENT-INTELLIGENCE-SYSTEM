from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.database import get_db

from app.database.models import (
    Recommendation,
    Student,
    Subject,
    Performance
)

from app.services.recommendation_service import generate_recommendations

from app.utils.auth import (
    require_faculty,
    require_student
)


router = APIRouter(
    prefix="/recommendations",
    tags=["Personalized Recommendations"]
)


# ==================================================
# GENERATE RECOMMENDATIONS
# ==================================================

@router.post("/generate")
def generate_student_recommendations(
    student_id: str,
    subject_id: int,

    db: Session = Depends(get_db),

    current_faculty=Depends(require_faculty)
):

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
    # GET PERFORMANCE
    # ------------------------------------------------

    performance = db.query(Performance).filter(
        Performance.student_id == student_id,
        Performance.subject_id == subject_id
    ).first()

    if not performance:
        raise HTTPException(
            status_code=404,
            detail="Performance not calculated yet"
        )


    # ------------------------------------------------
    # DELETE OLD RECOMMENDATIONS
    # ------------------------------------------------

    old_recommendations = db.query(
        Recommendation
    ).filter(
        Recommendation.student_id == student_id,
        Recommendation.subject_id == subject_id
    ).all()


    for recommendation in old_recommendations:
        db.delete(recommendation)


    db.flush()


    # ------------------------------------------------
    # GENERATE NEW RECOMMENDATIONS
    # ------------------------------------------------

    recommendations = generate_recommendations(

        attendance_percentage=
            performance.attendance_percentage,

        marks_percentage=
            performance.marks_percentage,

        assignment_percentage=
            performance.assignment_percentage,

        overall_percentage=
            performance.overall_percentage
    )


    # ------------------------------------------------
    # SAVE RECOMMENDATIONS
    # ------------------------------------------------

    saved_recommendations = []


    for recommendation_data in recommendations:

        recommendation = Recommendation(

            student_id=student_id,

            subject_id=subject_id,

            recommendation_text=
                recommendation_data[
                    "recommendation_text"
                ],

            recommendation_type=
                recommendation_data[
                    "recommendation_type"
                ],

            priority=
                recommendation_data[
                    "priority"
                ]
        )

        db.add(recommendation)

        saved_recommendations.append(
            recommendation
        )


    # ------------------------------------------------
    # COMMIT
    # ------------------------------------------------

    db.commit()


    for recommendation in saved_recommendations:
        db.refresh(recommendation)


    # ------------------------------------------------
    # RESPONSE
    # ------------------------------------------------

    return {

        "message":
            "Recommendations generated successfully",

        "student_id":
            student.student_id,

        "student_name":
            student.name,

        "subject_id":
            subject.id,

        "subject_name":
            subject.name,

        "total_recommendations":
            len(saved_recommendations),

        "recommendations": [

            {
                "recommendation_id":
                    recommendation.id,

                "recommendation_text":
                    recommendation.recommendation_text,

                "recommendation_type":
                    recommendation.recommendation_type,

                "priority":
                    recommendation.priority,

                "created_at":
                    recommendation.created_at
            }

            for recommendation
            in saved_recommendations
        ]
    }


# ==================================================
# GET ALL RECOMMENDATIONS - FACULTY
# ==================================================

@router.get("/")
def get_all_recommendations(
    db: Session = Depends(get_db),

    current_faculty=Depends(require_faculty)
):

    recommendations = db.query(
        Recommendation
    ).all()


    result = []


    for recommendation in recommendations:

        result.append({

            "recommendation_id":
                recommendation.id,

            "student_id":
                recommendation.student.student_id,

            "student_name":
                recommendation.student.name,

            "subject_id":
                recommendation.subject.id,

            "subject_name":
                recommendation.subject.name,

            "recommendation_text":
                recommendation.recommendation_text,

            "recommendation_type":
                recommendation.recommendation_type,

            "priority":
                recommendation.priority,

            "created_at":
                recommendation.created_at
        })


    return {

        "total_recommendations":
            len(result),

        "recommendations":
            result
    }


# ==================================================
# GET RECOMMENDATIONS OF ONE STUDENT - FACULTY
# ==================================================

@router.get("/student/{student_id}")
def get_student_recommendations(
    student_id: str,

    db: Session = Depends(get_db),

    current_faculty=Depends(require_faculty)
):

    student = db.query(Student).filter(
        Student.student_id == student_id
    ).first()


    if not student:
        raise HTTPException(
            status_code=404,
            detail="Student not found"
        )


    recommendations = db.query(
        Recommendation
    ).filter(
        Recommendation.student_id == student_id
    ).all()


    return {

        "student_id":
            student.student_id,

        "student_name":
            student.name,

        "total_recommendations":
            len(recommendations),

        "recommendations": [

            {
                "recommendation_id":
                    recommendation.id,

                "subject_id":
                    recommendation.subject.id,

                "subject_name":
                    recommendation.subject.name,

                "recommendation_text":
                    recommendation.recommendation_text,

                "recommendation_type":
                    recommendation.recommendation_type,

                "priority":
                    recommendation.priority,

                "created_at":
                    recommendation.created_at
            }

            for recommendation
            in recommendations
        ]
    }


# ==================================================
# GET MY RECOMMENDATIONS - STUDENT
# ==================================================

@router.get("/my-recommendations")
def get_my_recommendations(
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


    recommendations = db.query(
        Recommendation
    ).filter(
        Recommendation.student_id ==
        student.student_id
    ).all()


    return {

        "student_id":
            student.student_id,

        "student_name":
            student.name,

        "total_recommendations":
            len(recommendations),

        "recommendations": [

            {
                "recommendation_id":
                    recommendation.id,

                "subject_id":
                    recommendation.subject.id,

                "subject_name":
                    recommendation.subject.name,

                "recommendation_text":
                    recommendation.recommendation_text,

                "recommendation_type":
                    recommendation.recommendation_type,

                "priority":
                    recommendation.priority,

                "created_at":
                    recommendation.created_at
            }

            for recommendation
            in recommendations
        ]
    }