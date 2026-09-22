from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.models import (
    Attendance,
    Student,
    Subject,
    FacultySubject
)
from app.utils.auth import require_faculty, require_student


router = APIRouter(
    prefix="/attendance",
    tags=["Attendance"]
)


# ==================================================
# MARK ATTENDANCE
# ==================================================

@router.post("/mark")
def mark_attendance(
    student_id: str,
    subject_id: int,
    status: str = "Present",
    attendance_date: date = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_faculty)
):
    # Clean input values
    student_id = student_id.strip()
    status = status.strip()


    # Validate status
    if status not in ["Present", "Absent"]:
        raise HTTPException(
            status_code=400,
            detail="Status must be Present or Absent"
        )

    # --------------------------------------------------
    # Get faculty profile
    # --------------------------------------------------

    faculty = db.query(FacultySubject).filter(
        FacultySubject.faculty.has(
            user_id=current_user.id
        ),
        FacultySubject.subject_id == subject_id
    ).first()

    if not faculty:
        raise HTTPException(
            status_code=403,
            detail="You are not assigned to this subject"
        )

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

    # Use today's date if date is not provided
    if attendance_date is None:
        attendance_date = date.today()

    # Check duplicate attendance
    existing_attendance = db.query(Attendance).filter(
        Attendance.student_id == student_id,
        Attendance.subject_id == subject_id,
        Attendance.date == attendance_date
    ).first()

    if existing_attendance:
        raise HTTPException(
            status_code=400,
            detail="Attendance already marked for this student, subject and date"
        )

    # Create attendance
    attendance = Attendance(
        student_id=student_id,
        subject_id=subject_id,
        date=attendance_date,
        status=status
    )

    db.add(attendance)

    try:
        db.commit()
        db.refresh(attendance)

    except Exception:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Failed to mark attendance"
        )

    return {
        "message": "Attendance marked successfully",
        "attendance_id": attendance.id,
        "student_id": student.student_id,
        "student_name": student.name,
        "subject_id": subject.id,
        "subject_name": subject.name,
        "date": attendance.date,
        "status": attendance.status
    }


# ==================================================
# FACULTY - VIEW ATTENDANCE
# ==================================================

@router.get("/")
def get_all_attendance(
    db: Session = Depends(get_db),
    current_user=Depends(require_faculty)
):

    # Get subjects assigned to current faculty
    assigned_subject_ids = db.query(
        FacultySubject.subject_id
    ).join(
        FacultySubject.faculty
    ).filter(
        FacultySubject.faculty.has(
            user_id=current_user.id
        )
    ).all()

    assigned_subject_ids = [
        subject_id[0]
        for subject_id in assigned_subject_ids
    ]

    if not assigned_subject_ids:
        return {
            "total_records": 0,
            "attendance": []
        }

    # Get only attendance of assigned subjects
    attendance_records = db.query(Attendance).filter(
        Attendance.subject_id.in_(assigned_subject_ids)
    ).all()

    result = []

    for attendance in attendance_records:

        result.append({
            "attendance_id": attendance.id,
            "student_id": attendance.student.student_id,
            "student_name": attendance.student.name,
            "subject_id": attendance.subject.id,
            "subject_name": attendance.subject.name,
            "date": attendance.date,
            "status": attendance.status
        })

    return {
        "total_records": len(result),
        "attendance": result
    }


# ==================================================
# STUDENT - VIEW OWN ATTENDANCE
# ==================================================

@router.get("/my-attendance")
def get_my_attendance(
    db: Session = Depends(get_db),
    current_user=Depends(require_student)
):

    student = db.query(Student).filter(
        Student.user_id == current_user.id
    ).first()

    if not student:
        raise HTTPException(
            status_code=404,
            detail="Student profile not found"
        )

    attendance_records = db.query(Attendance).filter(
        Attendance.student_id == student.student_id
    ).all()

    result = []

    for attendance in attendance_records:

        result.append({
            "attendance_id": attendance.id,
            "subject_id": attendance.subject.id,
            "subject_name": attendance.subject.name,
            "date": attendance.date,
            "status": attendance.status
        })

    return {
        "student_id": student.student_id,
        "student_name": student.name,
        "total_records": len(result),
        "attendance": result
    }