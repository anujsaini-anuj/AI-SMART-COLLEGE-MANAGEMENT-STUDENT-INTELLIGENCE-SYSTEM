from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.models import Student, Subject, Performance
from app.services.prediction_service import predict_performance
from app.utils.auth import require_faculty


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

    # Check student
    student = db.query(Student).filter(
        Student.student_id == student_id
    ).first()

    if not student:
        raise HTTPException(
            status_code=404,
            detail="Student not found"
        )

    # Check subject
    subject = db.query(Subject).filter(
        Subject.id == subject_id
    ).first()

    if not subject:
        raise HTTPException(
            status_code=404,
            detail="Subject not found"
        )

    # Get calculated performance
    performance = db.query(Performance).filter(
        Performance.student_id == student_id,
        Performance.subject_id == subject_id
    ).first()

    if not performance:
        raise HTTPException(
            status_code=404,
            detail="Performance not calculated yet"
        )

    # ML prediction
    predicted_performance = predict_performance(
        performance.attendance_percentage,
        performance.marks_percentage,
        performance.assignment_percentage
    )

    # Performance level
    if predicted_performance >= 80:
        predicted_level = "Excellent"

    elif predicted_performance >= 60:
        predicted_level = "Good"

    elif predicted_performance >= 40:
        predicted_level = "Average"

    else:
        predicted_level = "Poor"

    return {
        "message": "Performance prediction calculated successfully",
        "student_id": student.student_id,
        "student_name": student.name,
        "subject_id": subject.id,
        "subject_name": subject.name,
        "attendance_percentage": performance.attendance_percentage,
        "marks_percentage": performance.marks_percentage,
        "assignment_percentage": performance.assignment_percentage,
        "predicted_performance": predicted_performance,
        "predicted_level": predicted_level
    }