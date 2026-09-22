from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.database import get_db

from app.database.models import (
    Performance,
    Student,
    Subject,
    Attendance,
    Marks,
    Assignment,
    FacultySubject
)

from app.utils.auth import (
    require_faculty,
    require_student
)


router = APIRouter(
    prefix="/performance",
    tags=["Performance Management"]
)


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
    # CHECK FACULTY SUBJECT ASSIGNMENT
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


    # ==================================================
    # ATTENDANCE CALCULATION
    # ==================================================

    attendance_records = db.query(Attendance).filter(
        Attendance.student_id == student_id,
        Attendance.subject_id == subject_id
    ).all()

    total_attendance = len(attendance_records)

    present_attendance = len([
        record
        for record in attendance_records
        if record.status == "Present"
    ])

    if total_attendance > 0:

        attendance_percentage = (
            present_attendance / total_attendance
        ) * 100

    else:

        attendance_percentage = 0


    # ==================================================
    # MARKS CALCULATION
    # ==================================================

    marks_records = db.query(Marks).filter(
        Marks.student_id == student_id,
        Marks.subject_id == subject_id
    ).all()

    total_marks_obtained = sum(
        mark.marks_obtained
        for mark in marks_records
    )

    total_max_marks = sum(
        mark.max_marks
        for mark in marks_records
    )

    if total_max_marks > 0:

        marks_percentage = (
            total_marks_obtained / total_max_marks
        ) * 100

    else:

        marks_percentage = 0


    # ==================================================
    # ASSIGNMENT CALCULATION
    # ==================================================

    assignment_records = db.query(Assignment).filter(
        Assignment.student_id == student_id,
        Assignment.subject_id == subject_id
    ).all()

    total_assignment_obtained = sum(
        assignment.marks_obtained or 0
        for assignment in assignment_records
    )

    total_assignment_marks = sum(
        assignment.max_marks
        for assignment in assignment_records
    )

    if total_assignment_marks > 0:

        assignment_percentage = (
            total_assignment_obtained /
            total_assignment_marks
        ) * 100

    else:

        assignment_percentage = 0


    # ==================================================
    # OVERALL PERFORMANCE
    # ==================================================

    overall_percentage = (
        attendance_percentage +
        marks_percentage +
        assignment_percentage
    ) / 3


    # ==================================================
    # PERFORMANCE LEVEL
    # ==================================================

    if overall_percentage >= 80:

        performance_level = "Excellent"

    elif overall_percentage >= 60:

        performance_level = "Good"

    elif overall_percentage >= 40:

        performance_level = "Average"

    else:

        performance_level = "Poor"


    # ==================================================
    # CHECK EXISTING PERFORMANCE
    # ==================================================

    existing_performance = db.query(Performance).filter(
        Performance.student_id == student_id,
        Performance.subject_id == subject_id
    ).first()


    # ==================================================
    # UPDATE EXISTING PERFORMANCE
    # ==================================================

    if existing_performance:

        existing_performance.attendance_percentage = round(
            attendance_percentage
        )

        existing_performance.marks_percentage = round(
            marks_percentage
        )

        existing_performance.assignment_percentage = round(
            assignment_percentage
        )

        existing_performance.overall_percentage = round(
            overall_percentage
        )

        existing_performance.performance_level = (
            performance_level
        )

        db.commit()
        db.refresh(existing_performance)

        performance = existing_performance


    # ==================================================
    # CREATE PERFORMANCE
    # ==================================================

    else:

        performance = Performance(

            student_id=student_id,

            subject_id=subject_id,

            attendance_percentage=round(
                attendance_percentage
            ),

            marks_percentage=round(
                marks_percentage
            ),

            assignment_percentage=round(
                assignment_percentage
            ),

            overall_percentage=round(
                overall_percentage
            ),

            performance_level=performance_level
        )

        db.add(performance)

        db.commit()
        db.refresh(performance)


    # ==================================================
    # RESPONSE
    # ==================================================

    return {

        "message": "Performance calculated successfully",

        "performance_id": performance.id,

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

        "overall_percentage":
            performance.overall_percentage,

        "performance_level":
            performance.performance_level
    }


# ==================================================
# GET ALL PERFORMANCE - FACULTY
# ==================================================

@router.get("/")
def get_all_performance(
    db: Session = Depends(get_db),
    current_faculty=Depends(require_faculty)
):

    # ------------------------------------------------
    # GET FACULTY ASSIGNED SUBJECTS
    # ------------------------------------------------

    assigned_subject_ids = [
        item.subject_id
        for item in db.query(FacultySubject).filter(
            FacultySubject.faculty.has(
                user_id=current_faculty.id
            )
        ).all()
    ]


    # ------------------------------------------------
    # NO ASSIGNED SUBJECTS
    # ------------------------------------------------

    if not assigned_subject_ids:

        return {
            "total_records": 0,
            "performance": []
        }


    # ------------------------------------------------
    # GET PERFORMANCE ONLY FOR ASSIGNED SUBJECTS
    # ------------------------------------------------

    performance_records = db.query(Performance).filter(
        Performance.subject_id.in_(assigned_subject_ids)
    ).all()


    # ------------------------------------------------
    # BUILD RESPONSE
    # ------------------------------------------------

    result = []

    for performance in performance_records:

        result.append({

            "performance_id": performance.id,

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

            "overall_percentage":
                performance.overall_percentage,

            "performance_level":
                performance.performance_level
        })


    return {

        "total_records": len(result),

        "performance": result
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
    # GET FACULTY ASSIGNED SUBJECTS
    # ------------------------------------------------

    assigned_subject_ids = [
        item.subject_id
        for item in db.query(FacultySubject).filter(
            FacultySubject.faculty.has(
                user_id=current_faculty.id
            )
        ).all()
    ]


    # ------------------------------------------------
    # NO ASSIGNED SUBJECTS
    # ------------------------------------------------

    if not assigned_subject_ids:

        return {

            "student_id":
                student.student_id,

            "student_name":
                student.name,

            "total_subjects": 0,

            "performance": []
        }


    # ------------------------------------------------
    # GET ONLY ASSIGNED SUBJECT PERFORMANCE
    # ------------------------------------------------

    performance_records = db.query(Performance).filter(

        Performance.student_id == student_id,

        Performance.subject_id.in_(
            assigned_subject_ids
        )

    ).all()


    # ------------------------------------------------
    # RESPONSE
    # ------------------------------------------------

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

                "overall_percentage":
                    performance.overall_percentage,

                "performance_level":
                    performance.performance_level
            }

            for performance in performance_records
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
    # GET ONLY CURRENT STUDENT PERFORMANCE
    # ------------------------------------------------

    performance_records = db.query(Performance).filter(
        Performance.student_id == student.student_id
    ).all()


    # ------------------------------------------------
    # RESPONSE
    # ------------------------------------------------

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

                "overall_percentage":
                    performance.overall_percentage,

                "performance_level":
                    performance.performance_level
            }

            for performance in performance_records
        ]
    }