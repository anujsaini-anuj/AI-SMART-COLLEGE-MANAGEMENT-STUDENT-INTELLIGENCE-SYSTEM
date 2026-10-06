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

# Automatic Student Risk calculation
from app.routers.risk import (
    create_or_update_student_risk
)


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

    # ==================================================
    # CHECK STUDENT
    # ==================================================

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
            detail="Performance calculation is not allowed for an inactive student."
        )


    # ==================================================
    # CHECK SUBJECT
    # ==================================================

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


    # ==================================================
    # CHECK SUBJECT BELONGS TO STUDENT COURSE
    # ==================================================

    if subject.course_id != student.course_id:

        raise HTTPException(
            status_code=400,
            detail="This subject does not belong to the student's course."
        )


    # ==================================================
    # CHECK FACULTY SUBJECT ASSIGNMENT
    # ==================================================

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


    # ==================================================
    # ATTENDANCE CALCULATION
    # ==================================================

    attendance_records = (
        db.query(Attendance)
        .filter(
            Attendance.student_id == student_id,
            Attendance.subject_id == subject_id
        )
        .all()
    )

    total_attendance = len(
        attendance_records
    )

    present_attendance = len([
        record
        for record in attendance_records
        if str(record.status).strip().lower() == "present"
    ])

    if total_attendance > 0:

        attendance_percentage = (
            present_attendance /
            total_attendance
        ) * 100

    else:

        attendance_percentage = 0.0


    attendance_percentage = round(
        attendance_percentage,
        2
    )


    # ==================================================
    # MARKS CALCULATION
    # ==================================================

    marks_records = (
        db.query(Marks)
        .filter(
            Marks.student_id == student_id,
            Marks.subject_id == subject_id
        )
        .all()
    )

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
            total_marks_obtained /
            total_max_marks
        ) * 100

    else:

        marks_percentage = 0.0


    marks_percentage = round(
        marks_percentage,
        2
    )


    # ==================================================
    # ASSIGNMENT CALCULATION
    # ==================================================

    assignment_records = (
        db.query(Assignment)
        .filter(
            Assignment.student_id == student_id,
            Assignment.subject_id == subject_id
        )
        .all()
    )

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

        assignment_percentage = 0.0


    assignment_percentage = round(
        assignment_percentage,
        2
    )


    # ==================================================
    # ACADEMIC PERFORMANCE
    # ==================================================

    # Marks = 70%
    # Assignments = 30%

    academic_percentage = (
        (marks_percentage * MARKS_WEIGHT)
        +
        (assignment_percentage * ASSIGNMENT_WEIGHT)
    )

    academic_percentage = round(
        academic_percentage,
        2
    )


    # ==================================================
    # PASS / FAIL
    # ==================================================

    attendance_pass = (
        attendance_percentage >=
        MIN_ATTENDANCE_PERCENTAGE
    )

    academic_pass = (
        academic_percentage >=
        MIN_ACADEMIC_PERCENTAGE
    )


    # Student must satisfy BOTH conditions

    if attendance_pass and academic_pass:

        pass_status = "PASS"

    else:

        pass_status = "FAIL"


    # ==================================================
    # PERFORMANCE LEVEL
    # ==================================================

    if pass_status == "FAIL":

        performance_level = "Poor"

    elif academic_percentage >= 80:

        performance_level = "Excellent"

    elif academic_percentage >= 60:

        performance_level = "Good"

    else:

        performance_level = "Average"


    # ==================================================
    # CHECK EXISTING PERFORMANCE
    # ==================================================

    existing_performance = (
        db.query(Performance)
        .filter(
            Performance.student_id == student_id,
            Performance.subject_id == subject_id
        )
        .first()
    )


    # ==================================================
    # CREATE / UPDATE PERFORMANCE
    # ==================================================

    if existing_performance:

        existing_performance.attendance_percentage = (
            attendance_percentage
        )

        existing_performance.marks_percentage = (
            marks_percentage
        )

        existing_performance.assignment_percentage = (
            assignment_percentage
        )

        existing_performance.overall_percentage = (
            academic_percentage
        )

        existing_performance.pass_status = (
            pass_status
        )

        existing_performance.performance_level = (
            performance_level
        )

        performance = existing_performance
        performance_action = "updated"

    else:

        performance = Performance(

            student_id=student_id,

            subject_id=subject_id,

            attendance_percentage=(
                attendance_percentage
            ),

            marks_percentage=(
                marks_percentage
            ),

            assignment_percentage=(
                assignment_percentage
            ),

            overall_percentage=(
                academic_percentage
            ),

            pass_status=(
                pass_status
            ),

            performance_level=(
                performance_level
            )
        )

        db.add(performance)

        performance_action = "created"


    # ==================================================
    # FLUSH PERFORMANCE
    # ==================================================

    # Performance ko database session mein bhej deta hai
    # bina final commit kiye.
    db.flush()


    # ==================================================
    # AUTOMATIC STUDENT RISK
    # ==================================================

    risk_record, risk_action = create_or_update_student_risk(

        db=db,

        student_id=student_id,

        subject_id=subject_id,

        performance=performance
    )


    # ==================================================
    # FINAL COMMIT
    # ==================================================

    db.commit()

    db.refresh(performance)

    db.refresh(risk_record)


    # ==================================================
    # RESPONSE
    # ==================================================

    return {

        "message":
            "Performance and student risk calculated successfully",

        "performance_action":
            performance_action,

        "risk_action":
            risk_action,

        "performance_id":
            performance.id,

        "student": {

            "student_id":
                student.student_id,

            "student_name":
                student.name
        },

        "subject": {

            "subject_id":
                subject.id,

            "subject_name":
                subject.name,

            "subject_code":
                subject.code
        },

        "performance": {

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
        },

        "student_risk": {

            "risk_score":
                risk_record.risk_score,

            "risk_level":
                risk_record.risk_level,

            "risk_reason":
                risk_record.risk_reason
        },

        "rules": {

            "minimum_attendance":
                MIN_ATTENDANCE_PERCENTAGE,

            "minimum_academic_percentage":
                MIN_ACADEMIC_PERCENTAGE,

            "marks_weight":
                "70%",

            "assignment_weight":
                "30%"
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