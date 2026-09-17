from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.models import (
    Student,
    Subject,
    Performance,
    Prediction
)
from app.services.prediction_service import predict_performance
from app.utils.auth import require_faculty, require_student


router = APIRouter(
    prefix="/prediction",
    tags=["Student Performance Prediction"]
)


@router.post("/calculate")
def calculate_prediction(
    student_id: str,
    subject_id: int,
    db: Session = Depends(get_db),
    current_faculty=Depends(require_faculty)
):

    # -------------------------
    # Check Student
    # -------------------------

    student = db.query(Student).filter(
        Student.student_id == student_id
    ).first()

    if not student:
        raise HTTPException(
            status_code=404,
            detail="Student not found"
        )


    # -------------------------
    # Check Subject
    # -------------------------

    subject = db.query(Subject).filter(
        Subject.id == subject_id
    ).first()

    if not subject:
        raise HTTPException(
            status_code=404,
            detail="Subject not found"
        )


    # -------------------------
    # Get Performance
    # -------------------------

    performance = db.query(Performance).filter(
        Performance.student_id == student_id,
        Performance.subject_id == subject_id
    ).first()

    if not performance:
        raise HTTPException(
            status_code=404,
            detail="Performance not calculated yet"
        )


    # -------------------------
    # ML Prediction
    # -------------------------

    predicted_performance = predict_performance(
        performance.attendance_percentage,
        performance.marks_percentage,
        performance.assignment_percentage
    )


    # -------------------------
    # Prediction Level
    # -------------------------

    if predicted_performance >= 80:
        predicted_level = "Excellent"

    elif predicted_performance >= 60:
        predicted_level = "Good"

    elif predicted_performance >= 40:
        predicted_level = "Average"

    else:
        predicted_level = "Poor"


    # -------------------------
    # Check Existing Prediction
    # -------------------------

    existing_prediction = db.query(Prediction).filter(
        Prediction.student_id == student_id,
        Prediction.subject_id == subject_id
    ).first()


    # -------------------------
    # Update Existing
    # -------------------------

    if existing_prediction:

        existing_prediction.predicted_performance = (
            predicted_performance
        )

        existing_prediction.predicted_level = (
            predicted_level
        )

        existing_prediction.model_name = (
            "Random Forest Regressor"
        )

        prediction = existing_prediction


    # -------------------------
    # Create New Prediction
    # -------------------------

    else:

        prediction = Prediction(
            student_id=student_id,
            subject_id=subject_id,
            predicted_performance=predicted_performance,
            predicted_level=predicted_level,
            model_name="Random Forest Regressor"
        )

        db.add(prediction)


    # -------------------------
    # Save Database
    # -------------------------

    db.commit()
    db.refresh(prediction)


    # -------------------------
    # Response
    # -------------------------

    return {
        "message": "Performance prediction saved successfully",

        "prediction_id": prediction.id,

        "student_id": student.student_id,
        "student_name": student.name,

        "subject_id": subject.id,
        "subject_name": subject.name,

        "attendance_percentage":
            performance.attendance_percentage,

        "marks_percentage":
            performance.marks_percentage,

        "assignment_percentage":
            performance.assignment_percentage,

        "predicted_performance":
            prediction.predicted_performance,

        "predicted_level":
            prediction.predicted_level,

        "model_name":
            prediction.model_name
    }




@router.get("/")
def get_all_predictions(
    db: Session = Depends(get_db),
    current_faculty=Depends(require_faculty)
):
    predictions = db.query(Prediction).all()

    result = []

    for prediction in predictions:

        result.append({
            "prediction_id": prediction.id,

            "student_id": prediction.student.student_id,
            "student_name": prediction.student.name,

            "subject_id": prediction.subject.id,
            "subject_name": prediction.subject.name,

            "predicted_performance":
                prediction.predicted_performance,

            "predicted_level":
                prediction.predicted_level,

            "model_name":
                prediction.model_name,

            "created_at":
                prediction.created_at
        })

    return {
        "total_predictions": len(result),
        "predictions": result
    }




@router.get("/my-prediction")
def get_my_prediction(
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

    predictions = db.query(Prediction).filter(
        Prediction.student_id == student.student_id
    ).all()

    result = []

    for prediction in predictions:

        result.append({
            "prediction_id": prediction.id,

            "student_id": student.student_id,
            "student_name": student.name,

            "subject_id": prediction.subject.id,
            "subject_name": prediction.subject.name,

            "predicted_performance":
                prediction.predicted_performance,

            "predicted_level":
                prediction.predicted_level,

            "model_name":
                prediction.model_name,

            "created_at":
                prediction.created_at
        })

    return {
        "student_id": student.student_id,
        "student_name": student.name,
        "total_predictions": len(result),
        "predictions": result
    }