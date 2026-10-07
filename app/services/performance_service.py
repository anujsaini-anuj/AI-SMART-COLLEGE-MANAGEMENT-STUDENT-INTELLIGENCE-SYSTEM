from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.database.models import (
    Student,
    Subject,
    Attendance,
    Marks,
    Assignment,
    Performance,
)

from app.routers.risk import create_or_update_student_risk


# ============================================================
# PERFORMANCE RULES
# ============================================================

MIN_ATTENDANCE_PERCENTAGE = 75
MIN_ACADEMIC_PERCENTAGE = 40

MARKS_WEIGHT = 0.70
ASSIGNMENT_WEIGHT = 0.30


# ============================================================
# CALCULATE AND UPDATE PERFORMANCE
# ============================================================

def calculate_and_update_performance(
    db: Session,
    student_id: str,
    subject_id: int
):

    # ========================================================
    # STUDENT
    # ========================================================

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

    if not student.is_active:

        raise HTTPException(
            status_code=400,
            detail="Student is inactive"
        )

    # ========================================================
    # SUBJECT
    # ========================================================

    subject = (
        db.query(Subject)
        .filter(
            Subject.id == subject_id
        )
        .first()
    )

    if not subject:

        raise HTTPException(
            status_code=404,
            detail="Subject not found"
        )

    # ========================================================
    # COURSE VALIDATION
    # ========================================================

    if subject.course_id != student.course_id:

        raise HTTPException(
            status_code=400,
            detail="Subject does not belong to student's course"
        )

    # ========================================================
    # ATTENDANCE
    # ========================================================

    attendance_records = (
        db.query(Attendance)
        .filter(
            Attendance.student_id == student_id,
            Attendance.subject_id == subject_id
        )
        .all()
    )

    total_classes = len(
        attendance_records
    )

    present_classes = sum(
        1
        for record in attendance_records
        if (
            record.status
            and str(
                record.status
            ).strip().lower() == "present"
        )
    )

    if total_classes > 0:

        attendance_percentage = (
            present_classes
            / total_classes
        ) * 100

    else:

        attendance_percentage = 0.0

    # ========================================================
    # MARKS
    # ========================================================

    marks_records = (
        db.query(Marks)
        .filter(
            Marks.student_id == student_id,
            Marks.subject_id == subject_id
        )
        .all()
    )

    valid_marks_records = [
        record
        for record in marks_records
        if (
            record.marks_obtained is not None
            and record.max_marks is not None
            and record.max_marks > 0
        )
    ]

    total_marks = sum(
        record.marks_obtained
        for record in valid_marks_records
    )

    total_max_marks = sum(
        record.max_marks
        for record in valid_marks_records
    )

    if total_max_marks > 0:

        marks_percentage = (
            total_marks
            / total_max_marks
        ) * 100

    else:

        marks_percentage = 0.0

    # ========================================================
    # ASSIGNMENTS
    # ========================================================

    assignments = (
        db.query(Assignment)
        .filter(
            Assignment.student_id == student_id,
            Assignment.subject_id == subject_id
        )
        .all()
    )

    valid_assignment_records = [
        assignment
        for assignment in assignments
        if (
            assignment.max_marks is not None
            and assignment.max_marks > 0
        )
    ]

    total_assignment_marks = sum(
        assignment.marks_obtained or 0
        for assignment in valid_assignment_records
    )

    total_assignment_max_marks = sum(
        assignment.max_marks
        for assignment in valid_assignment_records
    )

    if total_assignment_max_marks > 0:

        assignment_percentage = (
            total_assignment_marks
            / total_assignment_max_marks
        ) * 100

    else:

        assignment_percentage = 0.0

    # ========================================================
    # ACADEMIC PERCENTAGE
    # ========================================================
    #
    # Marks       = 70%
    # Assignments = 30%
    #
    # Example:
    #
    # Marks = 80%
    # Assignment = 70%
    #
    # Academic =
    # (80 × 0.70) + (70 × 0.30)
    # = 77%
    #
    # ========================================================

    academic_percentage = (
        marks_percentage * MARKS_WEIGHT
    ) + (
        assignment_percentage
        * ASSIGNMENT_WEIGHT
    )


    # ========================================================
    # ATTENDANCE ELIGIBILITY
    # ========================================================

    attendance_eligible = (
        attendance_percentage
        >= MIN_ATTENDANCE_PERCENTAGE
    )


    # ========================================================
    # ACADEMIC PASS
    # ========================================================

    academic_pass = (
        academic_percentage
        >= MIN_ACADEMIC_PERCENTAGE
    )


    # ========================================================
    # FINAL STATUS
    # ========================================================
    #
    # 1. Attendance < 75%
    #       → NOT ELIGIBLE
    #
    # 2. Attendance >= 75%
    #       → Academic percentage check
    #
    # 3. Academic < 40%
    #       → FAIL
    #
    # 4. Academic >= 40%
    #       → PASS
    #
    # ========================================================

    if not attendance_eligible:

        pass_status = "NOT ELIGIBLE"

    elif not academic_pass:

        pass_status = "FAIL"

    else:

        pass_status = "PASS"


    # ========================================================
    # PERFORMANCE LEVEL
    # ========================================================

    if academic_percentage >= 80:

        performance_level = "Excellent"

    elif academic_percentage >= 60:

        performance_level = "Good"

    elif academic_percentage >= 40:

        performance_level = "Average"

    else:

        performance_level = "Poor"

    # ========================================================
    # EXISTING PERFORMANCE
    # ========================================================

    performance = (
        db.query(Performance)
        .filter(
            Performance.student_id == student_id,
            Performance.subject_id == subject_id
        )
        .first()
    )

    # ========================================================
    # UPDATE EXISTING PERFORMANCE
    # ========================================================

    if performance:

        performance.attendance_percentage = round(
            attendance_percentage,
            2
        )

        performance.marks_percentage = round(
            marks_percentage,
            2
        )

        performance.assignment_percentage = round(
            assignment_percentage,
            2
        )

        performance.overall_percentage = round(
            academic_percentage,
            2
        )

        performance.performance_level = (
            performance_level
        )

        performance.pass_status = (
            pass_status
        )

    # ========================================================
    # CREATE NEW PERFORMANCE
    # ========================================================

    else:

        performance = Performance(

            student_id=student_id,

            subject_id=subject_id,

            attendance_percentage=round(
                attendance_percentage,
                2
            ),

            marks_percentage=round(
                marks_percentage,
                2
            ),

            assignment_percentage=round(
                assignment_percentage,
                2
            ),

            overall_percentage=round(
                academic_percentage,
                2
            ),

            performance_level=(
                performance_level
            ),

            pass_status=(
                pass_status
            )
        )

        db.add(
            performance
        )

    # ========================================================
    # FLUSH
    # ========================================================
    #
    # Performance ko database transaction mein
    # temporarily available kar deta hai.
    #
    # Risk calculation mein performance object use hoga.
    #
    # ========================================================

    db.flush()

    # ========================================================
    # STUDENT RISK
    # ========================================================

    risk_record, risk_action = (
        create_or_update_student_risk(
            db=db,
            student_id=student_id,
            subject_id=subject_id,
            performance=performance
        )
    )

    # ========================================================
    # COMMIT
    # ========================================================

    db.commit()

    # ========================================================
    # REFRESH
    # ========================================================

    db.refresh(
        performance
    )

    db.refresh(
        risk_record
    )

    # ========================================================
    # RESULT
    # ========================================================

    return {

        "performance": {

            "student_id":
                performance.student_id,

            "subject_id":
                performance.subject_id,

            "attendance_percentage":
                performance.attendance_percentage,

            "marks_percentage":
                performance.marks_percentage,

            "assignment_percentage":
                performance.assignment_percentage,

            "overall_percentage":
                performance.overall_percentage,

            "performance_level":
                performance.performance_level,

            "pass_status":
                performance.pass_status
        },

        "student_risk": {

            "risk_score":
                risk_record.risk_score,

            "risk_level":
                risk_record.risk_level,

            "risk_reason":
                risk_record.risk_reason
        },

        "risk_action":
            risk_action
    }