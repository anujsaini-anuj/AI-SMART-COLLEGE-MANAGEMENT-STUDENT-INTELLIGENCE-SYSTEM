from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.database import get_db

from app.database.models import (
    Performance,
    Student,
    Faculty,
    FacultySubject
)

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

    # --------------------------------------------------
    # FIND FACULTY PROFILE
    # --------------------------------------------------

    faculty = db.query(Faculty).filter(
        Faculty.user_id == current_faculty.id
    ).first()

    if not faculty:
        raise HTTPException(
            status_code=404,
            detail="Faculty profile not found"
        )

    # --------------------------------------------------
    # GET ASSIGNED SUBJECTS
    # --------------------------------------------------

    faculty_subjects = db.query(FacultySubject).filter(
        FacultySubject.faculty_id == faculty.id
    ).all()

    subject_ids = [
        item.subject_id
        for item in faculty_subjects
    ]

    if not subject_ids:
        raise HTTPException(
            status_code=404,
            detail="No subjects assigned to this faculty"
        )

    # --------------------------------------------------
    # GET PERFORMANCE ONLY FOR ASSIGNED SUBJECTS
    # --------------------------------------------------

    performances = db.query(Performance).filter(
        Performance.subject_id.in_(subject_ids)
    ).all()

    if not performances:
        raise HTTPException(
            status_code=404,
            detail="No performance data found for assigned subjects"
        )

    # --------------------------------------------------
    # GROUP PERFORMANCE BY STUDENT
    # --------------------------------------------------

    student_performance = {}

    for performance in performances:

        student = db.query(Student).filter(
            Student.student_id == performance.student_id
        ).first()

        if not student:
            continue

        if student.student_id not in student_performance:
            student_performance[student.student_id] = {
                "student_id": student.student_id,
                "student_name": student.name,
                "attendance": [],
                "marks": [],
                "assignments": []
            }

        student_performance[
            student.student_id
        ]["attendance"].append(
            performance.attendance_percentage
        )

        student_performance[
            student.student_id
        ]["marks"].append(
            performance.marks_percentage
        )

        student_performance[
            student.student_id
        ]["assignments"].append(
            performance.assignment_percentage
        )

    # --------------------------------------------------
    # CREATE ONE RECORD PER STUDENT
    # --------------------------------------------------

    student_data = []

    for data in student_performance.values():

        student_data.append({
            "student_id": data["student_id"],
            "student_name": data["student_name"],

            "attendance_percentage": round(
                sum(data["attendance"]) /
                len(data["attendance"]),
                2
            ),

            "marks_percentage": round(
                sum(data["marks"]) /
                len(data["marks"]),
                2
            ),

            "assignment_percentage": round(
                sum(data["assignments"]) /
                len(data["assignments"]),
                2
            )
        })

    # --------------------------------------------------
    # MINIMUM STUDENTS
    # --------------------------------------------------

    if len(student_data) < 3:
        raise HTTPException(
            status_code=400,
            detail="At least 3 students are required for segmentation"
        )

    # --------------------------------------------------
    # RUN K-MEANS
    # --------------------------------------------------

    segmented_students = segment_students(
        student_data
    )

    return {
        "message": "Student segmentation calculated successfully",
        "faculty": {
            "faculty_id": faculty.faculty_id,
            "faculty_name": faculty.name
        },
        "assigned_subjects": len(subject_ids),
        "total_students": len(segmented_students),
        "students": segmented_students
    }