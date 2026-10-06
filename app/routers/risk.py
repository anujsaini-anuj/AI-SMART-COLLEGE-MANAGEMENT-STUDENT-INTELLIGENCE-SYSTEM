from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.database.database import get_db
from app.database.models import (
    Student,
    Subject,
    Performance,
    StudentRisk,
    FacultySubject
)
from app.utils.auth import require_faculty, require_student


router = APIRouter(
    prefix="/student-risk",
    tags=["Student Risk / Early Warning"]
)


# ============================================================
# RISK THRESHOLDS
# ============================================================

ATTENDANCE_VERY_LOW = 50
ATTENDANCE_LOW = 60
ATTENDANCE_REQUIRED = 75

ACADEMIC_FAIL = 40
ACADEMIC_WEAK = 50
ACADEMIC_NEEDS_IMPROVEMENT = 60

ASSIGNMENT_LOW = 40
ASSIGNMENT_NEEDS_IMPROVEMENT = 60

LOW_RISK_THRESHOLD = 30
HIGH_RISK_THRESHOLD = 60


# ============================================================
# RISK CALCULATION
# ============================================================

def calculate_risk(
    attendance_percentage: float,
    academic_percentage: float,
    assignment_percentage: float,
    pass_status: str
):
    """
    Calculate student risk score, risk level,
    reason and recommended action.
    """

    # Keep percentages between 0 and 100
    attendance_percentage = max(
        0.0,
        min(100.0, float(attendance_percentage))
    )

    academic_percentage = max(
        0.0,
        min(100.0, float(academic_percentage))
    )

    assignment_percentage = max(
        0.0,
        min(100.0, float(assignment_percentage))
    )

    risk_score = 0
    risk_reasons = []

    # ========================================================
    # 1. ATTENDANCE RISK
    # ========================================================

    if attendance_percentage < ATTENDANCE_VERY_LOW:

        risk_score += 40

        risk_reasons.append(
            f"Very low attendance ({attendance_percentage:.2f}%)"
        )

    elif attendance_percentage < ATTENDANCE_LOW:

        risk_score += 30

        risk_reasons.append(
            f"Low attendance ({attendance_percentage:.2f}%)"
        )

    elif attendance_percentage < ATTENDANCE_REQUIRED:

        risk_score += 20

        risk_reasons.append(
            f"Attendance below required 75% "
            f"({attendance_percentage:.2f}%)"
        )

    # ========================================================
    # 2. ACADEMIC PERFORMANCE RISK
    # ========================================================

    if academic_percentage < ACADEMIC_FAIL:

        risk_score += 35

        risk_reasons.append(
            f"Academic performance is below passing level "
            f"({academic_percentage:.2f}%)"
        )

    elif academic_percentage < ACADEMIC_WEAK:

        risk_score += 25

        risk_reasons.append(
            f"Weak academic performance "
            f"({academic_percentage:.2f}%)"
        )

    elif academic_percentage < ACADEMIC_NEEDS_IMPROVEMENT:

        risk_score += 15

        risk_reasons.append(
            f"Academic performance needs improvement "
            f"({academic_percentage:.2f}%)"
        )

    # ========================================================
    # 3. ASSIGNMENT RISK
    # ========================================================

    if assignment_percentage < ASSIGNMENT_LOW:

        risk_score += 10

        risk_reasons.append(
            f"Low assignment performance "
            f"({assignment_percentage:.2f}%)"
        )

    elif assignment_percentage < ASSIGNMENT_NEEDS_IMPROVEMENT:

        risk_score += 5

        risk_reasons.append(
            f"Assignment performance needs improvement "
            f"({assignment_percentage:.2f}%)"
        )

    # ========================================================
    # 4. FAIL STATUS
    # ========================================================

    if str(pass_status).upper() == "FAIL":

        risk_score += 10

        risk_reasons.append(
            "Student is currently in FAIL status"
        )

    # ========================================================
    # LIMIT SCORE
    # ========================================================

    risk_score = min(risk_score, 100)

    # ========================================================
    # RISK LEVEL
    # ========================================================

    if risk_score >= HIGH_RISK_THRESHOLD:

        risk_level = "High"

    elif risk_score >= LOW_RISK_THRESHOLD:

        risk_level = "Medium"

    else:

        risk_level = "Low"

    # ========================================================
    # NO RISK REASON
    # ========================================================

    if not risk_reasons:

        risk_reasons.append(
            "No major risk indicators detected"
        )

    risk_reason = "; ".join(risk_reasons)

    # ========================================================
    # RECOMMENDED ACTION
    # ========================================================

    if risk_level == "High":

        recommended_action = (
            "Immediate faculty intervention recommended. "
            "Student should receive academic support, "
            "attendance counselling and regular progress monitoring."
        )

    elif risk_level == "Medium":

        recommended_action = (
            "Student should be monitored regularly. "
            "Faculty should focus on attendance and academic "
            "improvement and provide appropriate academic support."
        )

    else:

        recommended_action = (
            "Continue regular academic and attendance monitoring."
        )

    return (
        risk_score,
        risk_level,
        risk_reason,
        recommended_action
    )



def create_or_update_student_risk(
    db: Session,
    student_id: str,
    subject_id: int,
    performance: Performance
):
    """
    Performance record ke basis par StudentRisk
    create ya update karta hai.
    """

    (
        risk_score,
        risk_level,
        risk_reason,
        recommended_action
    ) = calculate_risk(
        attendance_percentage=performance.attendance_percentage,
        academic_percentage=performance.overall_percentage,
        assignment_percentage=performance.assignment_percentage,
        pass_status=performance.pass_status
    )

    existing_risk = (
        db.query(StudentRisk)
        .filter(
            StudentRisk.student_id == student_id,
            StudentRisk.subject_id == subject_id
        )
        .first()
    )

    if existing_risk:

        existing_risk.risk_score = risk_score
        existing_risk.risk_level = risk_level
        existing_risk.risk_reason = risk_reason

        risk_record = existing_risk
        action = "updated"

    else:

        risk_record = StudentRisk(
            student_id=student_id,
            subject_id=subject_id,
            risk_score=risk_score,
            risk_level=risk_level,
            risk_reason=risk_reason
        )

        db.add(risk_record)

        action = "created"

    return risk_record, action


# ============================================================
# RISK SUMMARY
# ============================================================

def get_risk_summary(risk_records):

    if not risk_records:

        return {
            "overall_risk_level": "Low",
            "highest_risk_score": 0,
            "high_risk_subjects": 0,
            "medium_risk_subjects": 0,
            "low_risk_subjects": 0
        }

    high_count = sum(
        1
        for risk in risk_records
        if risk.risk_level == "High"
    )

    medium_count = sum(
        1
        for risk in risk_records
        if risk.risk_level == "Medium"
    )

    low_count = sum(
        1
        for risk in risk_records
        if risk.risk_level == "Low"
    )

    highest_score = max(
        risk.risk_score
        for risk in risk_records
    )

    if highest_score >= HIGH_RISK_THRESHOLD:

        overall_risk = "High"

    elif highest_score >= LOW_RISK_THRESHOLD:

        overall_risk = "Medium"

    else:

        overall_risk = "Low"

    return {
        "overall_risk_level": overall_risk,
        "highest_risk_score": highest_score,
        "high_risk_subjects": high_count,
        "medium_risk_subjects": medium_count,
        "low_risk_subjects": low_count
    }


# ============================================================
# RECOMMENDED ACTION
# ============================================================

def get_recommended_action(risk_level: str):

    if risk_level == "High":

        return (
            "Immediate faculty intervention, counselling "
            "and close academic monitoring recommended."
        )

    if risk_level == "Medium":

        return (
            "Regular monitoring and academic support recommended."
        )

    return (
        "Continue regular monitoring."
    )


# ============================================================
# CALCULATE STUDENT RISK
# ============================================================

@router.post("/calculate")
def calculate_student_risk(
    student_id: str,
    subject_id: int,
    current_faculty=Depends(require_faculty),
    db: Session = Depends(get_db)
):

    # --------------------------------------------------------
    # STUDENT
    # --------------------------------------------------------

    student = (
        db.query(Student)
        .filter(Student.student_id == student_id)
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
            detail="Risk calculation is not allowed for an inactive student."
        )

    # --------------------------------------------------------
    # SUBJECT
    # --------------------------------------------------------

    subject = (
        db.query(Subject)
        .filter(Subject.id == subject_id)
        .first()
    )

    if not subject:

        raise HTTPException(
            status_code=404,
            detail="Subject not found"
        )

    # --------------------------------------------------------
    # COURSE VALIDATION
    # --------------------------------------------------------

    if subject.course_id != student.course_id:

        raise HTTPException(
            status_code=400,
            detail="This subject does not belong to the student's course."
        )

    # --------------------------------------------------------
    # FACULTY AUTHORIZATION
    # --------------------------------------------------------

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
            detail=(
                "You are not authorized to calculate "
                "risk for this subject."
            )
        )

    # --------------------------------------------------------
    # PERFORMANCE
    # --------------------------------------------------------

    performance = (
        db.query(Performance)
        .filter(
            Performance.student_id == student_id,
            Performance.subject_id == subject_id
        )
        .first()
    )

    if not performance:

        raise HTTPException(
            status_code=404,
            detail=(
                "Performance record not found. "
                "Calculate student performance first."
            )
        )

    # --------------------------------------------------------
    # CALCULATE RISK
    # --------------------------------------------------------

    (
        risk_score,
        risk_level,
        risk_reason,
        recommended_action
    ) = calculate_risk(
        attendance_percentage=performance.attendance_percentage,
        academic_percentage=performance.overall_percentage,
        assignment_percentage=performance.assignment_percentage,
        pass_status=performance.pass_status
    )

    # --------------------------------------------------------
    # EXISTING RISK
    # --------------------------------------------------------

    existing_risk = (
        db.query(StudentRisk)
        .filter(
            StudentRisk.student_id == student_id,
            StudentRisk.subject_id == subject_id
        )
        .first()
    )

    if existing_risk:

        existing_risk.risk_score = risk_score
        existing_risk.risk_level = risk_level
        existing_risk.risk_reason = risk_reason

        db.commit()
        db.refresh(existing_risk)

        risk_record = existing_risk
        action = "updated"

    else:

        risk_record = StudentRisk(
            student_id=student_id,
            subject_id=subject_id,
            risk_score=risk_score,
            risk_level=risk_level,
            risk_reason=risk_reason
        )

        db.add(risk_record)

        db.commit()
        db.refresh(risk_record)

        action = "created"

    # --------------------------------------------------------
    # RESPONSE
    # --------------------------------------------------------

    return {
        "message": f"Student risk {action} successfully",

        "student": {
            "student_id": student.student_id,
            "name": student.name
        },

        "subject": {
            "subject_id": subject.id,
            "subject_name": subject.name,
            "subject_code": subject.code
        },

        "performance": {
            "attendance_percentage": round(
                performance.attendance_percentage,
                2
            ),
            "academic_percentage": round(
                performance.overall_percentage,
                2
            ),
            "assignment_percentage": round(
                performance.assignment_percentage,
                2
            ),
            "performance_level": performance.performance_level,
            "pass_status": performance.pass_status
        },

        "risk": {
            "risk_score": risk_score,
            "risk_level": risk_level,
            "risk_reason": risk_reason,
            "recommended_action": recommended_action
        }
    }


# ============================================================
# GET ALL FACULTY RISKS
# ============================================================

@router.get("/")
def get_all_student_risks(
    current_faculty=Depends(require_faculty),
    db: Session = Depends(get_db)
):

    assigned_subject_ids = (
        db.query(FacultySubject.subject_id)
        .filter(
            FacultySubject.faculty.has(
                user_id=current_faculty.id
            )
        )
        .subquery()
    )

    risks = (
        db.query(StudentRisk)
        .options(
            joinedload(StudentRisk.student),
            joinedload(StudentRisk.subject)
        )
        .filter(
            StudentRisk.subject_id.in_(assigned_subject_ids)
        )
        .order_by(
            StudentRisk.risk_score.desc()
        )
        .all()
    )

    high_count = sum(
        1
        for risk in risks
        if risk.risk_level == "High"
    )

    medium_count = sum(
        1
        for risk in risks
        if risk.risk_level == "Medium"
    )

    low_count = sum(
        1
        for risk in risks
        if risk.risk_level == "Low"
    )

    # Unique students
    unique_student_ids = {
        risk.student.student_id
        for risk in risks
    }

    return {

        "total_students": len(unique_student_ids),

        "total_risk_records": len(risks),

        "risk_summary": {
            "high": high_count,
            "medium": medium_count,
            "low": low_count
        },

        "risks": [
            {
                "student_id": risk.student.student_id,
                "student_name": risk.student.name,

                "subject_id": risk.subject.id,
                "subject_name": risk.subject.name,
                "subject_code": risk.subject.code,

                "risk_score": risk.risk_score,
                "risk_level": risk.risk_level,
                "risk_reason": risk.risk_reason,

                "recommended_action": get_recommended_action(
                    risk.risk_level
                ),

                "created_at": risk.created_at
            }
            for risk in risks
        ]
    }


# ============================================================
# EARLY WARNINGS
# ============================================================

@router.get("/early-warnings")
def get_early_warnings(
    current_faculty=Depends(require_faculty),
    db: Session = Depends(get_db)
):

    assigned_subject_ids = (
        db.query(FacultySubject.subject_id)
        .filter(
            FacultySubject.faculty.has(
                user_id=current_faculty.id
            )
        )
        .subquery()
    )

    warnings = (
        db.query(StudentRisk)
        .options(
            joinedload(StudentRisk.student),
            joinedload(StudentRisk.subject)
        )
        .filter(
            StudentRisk.subject_id.in_(assigned_subject_ids),
            StudentRisk.risk_level.in_(["High", "Medium"])
        )
        .order_by(
            StudentRisk.risk_score.desc()
        )
        .all()
    )

    high_count = sum(
        1
        for warning in warnings
        if warning.risk_level == "High"
    )

    medium_count = sum(
        1
        for warning in warnings
        if warning.risk_level == "Medium"
    )

    return {

        "message": "Early warning records retrieved successfully",

        "total_warnings": len(warnings),

        "summary": {
            "high_risk": high_count,
            "medium_risk": medium_count
        },

        "warnings": [
            {
                "student_id": warning.student.student_id,
                "student_name": warning.student.name,

                "subject_id": warning.subject.id,
                "subject_name": warning.subject.name,
                "subject_code": warning.subject.code,

                "risk_score": warning.risk_score,
                "risk_level": warning.risk_level,
                "risk_reason": warning.risk_reason,

                "recommended_action": get_recommended_action(
                    warning.risk_level
                ),

                "created_at": warning.created_at
            }
            for warning in warnings
        ]
    }


# ============================================================
# FACULTY → PARTICULAR STUDENT RISK
# ============================================================

@router.get("/student/{student_id}")
def get_student_risk(
    student_id: str,
    current_faculty=Depends(require_faculty),
    db: Session = Depends(get_db)
):

    student = (
        db.query(Student)
        .filter(Student.student_id == student_id)
        .first()
    )

    if not student:

        raise HTTPException(
            status_code=404,
            detail="Student not found"
        )

    assigned_subject_ids = (
        db.query(FacultySubject.subject_id)
        .filter(
            FacultySubject.faculty.has(
                user_id=current_faculty.id
            )
        )
        .subquery()
    )

    risks = (
        db.query(StudentRisk)
        .options(
            joinedload(StudentRisk.subject)
        )
        .filter(
            StudentRisk.student_id == student_id,
            StudentRisk.subject_id.in_(assigned_subject_ids)
        )
        .order_by(
            StudentRisk.risk_score.desc()
        )
        .all()
    )

    summary = get_risk_summary(risks)

    return {

        "student": {
            "student_id": student.student_id,
            "name": student.name,
            "course_id": student.course_id,
            "semester": student.semester
        },

        "risk_summary": summary,

        "risks": [
            {
                "subject_id": risk.subject.id,
                "subject_name": risk.subject.name,
                "subject_code": risk.subject.code,

                "risk_score": risk.risk_score,
                "risk_level": risk.risk_level,
                "risk_reason": risk.risk_reason,

                "recommended_action": get_recommended_action(
                    risk.risk_level
                ),

                "created_at": risk.created_at
            }
            for risk in risks
        ]
    }


# ============================================================
# STUDENT → MY RISK
# ============================================================

@router.get("/my-risk")
def get_my_risk(
    current_student=Depends(require_student),
    db: Session = Depends(get_db)
):

    student = (
        db.query(Student)
        .filter(Student.user_id == current_student.id)
        .first()
    )

    if not student:

        raise HTTPException(
            status_code=404,
            detail="Student profile not found"
        )

    risks = (
        db.query(StudentRisk)
        .options(
            joinedload(StudentRisk.subject)
        )
        .filter(
            StudentRisk.student_id == student.student_id
        )
        .order_by(
            StudentRisk.risk_score.desc()
        )
        .all()
    )

    summary = get_risk_summary(risks)

    return {

        "student": {
            "student_id": student.student_id,
            "name": student.name,
            "course_id": student.course_id,
            "semester": student.semester
        },

        "risk_summary": summary,

        "risks": [
            {
                "subject_id": risk.subject.id,
                "subject_name": risk.subject.name,
                "subject_code": risk.subject.code,

                "risk_score": risk.risk_score,
                "risk_level": risk.risk_level,
                "risk_reason": risk.risk_reason,

                "recommended_action": get_recommended_action(
                    risk.risk_level
                ),

                "created_at": risk.created_at
            }
            for risk in risks
        ]
    }