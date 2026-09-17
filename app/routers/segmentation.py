from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.models import Performance, Student, Subject
from app.services.segmentation_service import segment_students
from app.utils.auth import require_faculty


router = APIRouter(
    prefix="/segmentation",
    tags=["Student Segmentation"]
)


@router.post("/calculate")
def calculate_segmentation(
    db: Session = Depends(get_db),
    current_faculty=Depends(require_faculty)
):

    # Get all performance records
    performances = db.query(Performance).all()

    if not performances:
        raise HTTPException(
            status_code=404,
            detail="No performance data found"
        )

    student_data = []

    for performance in performances:

        student = db.query(Student).filter(
            Student.student_id == performance.student_id
        ).first()

        if not student:
            continue

        student_data.append({
            "student_id": student.student_id,
            "student_name": student.name,

            "attendance_percentage":
                performance.attendance_percentage,

            "marks_percentage":
                performance.marks_percentage,

            "assignment_percentage":
                performance.assignment_percentage
        })

    # Need at least 3 students
    if len(student_data) < 3:
        raise HTTPException(
            status_code=400,
            detail="At least 3 students are required for segmentation"
        )

    # Run K-Means
    segmented_students = segment_students(student_data)

    return {
        "message": "Student segmentation calculated successfully",
        "total_students": len(segmented_students),
        "students": segmented_students
    }