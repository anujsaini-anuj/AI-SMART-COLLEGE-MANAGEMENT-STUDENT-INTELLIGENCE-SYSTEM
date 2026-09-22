from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.database import get_db

from app.database.models import (
    StudentRisk,
    Student,
    Subject,
    Performance,
    FacultySubject
)

from app.utils.auth import (
    require_faculty,
    require_student
)


router = APIRouter(
    prefix="/risk",
    tags=["Student Risk Detection"]
)


# ==================================================
# CALCULATE STUDENT RISK
# ==================================================

@router.post("/calculate")
def calculate_student_risk(
    student_id: str,
    subject_id: int,

    db: Session = Depends(get_db),

    current_faculty=Depends(require_faculty)
):

    # ------------------------------------------------
    # CLEAN STUDENT ID
    # ------------------------------------------------

    student_id = student_id.strip()


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


    # ==================================================
    # RISK SCORE CALCULATION
    # ==================================================

    attendance_risk = (
        100 - performance.attendance_percentage
    )

    marks_risk = (
        100 - performance.marks_percentage
    )

    assignment_risk = (
        100 - performance.assignment_percentage
    )


    risk_score = (
        (attendance_risk * 0.30) +
        (marks_risk * 0.50) +
        (assignment_risk * 0.20)
    )

    risk_score = round(risk_score)


    # ==================================================
    # RISK LEVEL
    # ==================================================

    if (
        performance.attendance_percentage < 60
        or performance.marks_percentage < 40
        or risk_score >= 60
    ):

        risk_level = "High"

    elif (
        performance.attendance_percentage < 75
        or performance.marks_percentage < 50
        or performance.assignment_percentage < 50
        or risk_score >= 30
    ):

        risk_level = "Medium"

    else:

        risk_level = "Low"


    # ==================================================
    # RISK REASON
    # ==================================================

    reasons = []


    if performance.attendance_percentage < 75:

        reasons.append(
            f"Low attendance ({performance.attendance_percentage}%)"
        )


    if performance.marks_percentage < 50:

        reasons.append(
            f"Low marks ({performance.marks_percentage}%)"
        )


    if performance.assignment_percentage < 50:

        reasons.append(
            f"Weak assignment performance "
            f"({performance.assignment_percentage}%)"
        )


    if not reasons:

        reasons.append(
            "No major risk indicators detected"
        )


    risk_reason = ", ".join(reasons)


    # ==================================================
    # CHECK EXISTING RISK
    # ==================================================

    existing_risk = db.query(StudentRisk).filter(
        StudentRisk.student_id == student_id,
        StudentRisk.subject_id == subject_id
    ).first()


    # ==================================================
    # UPDATE EXISTING RISK
    # ==================================================

    if existing_risk:

        existing_risk.risk_score = risk_score

        existing_risk.risk_level = risk_level

        existing_risk.risk_reason = risk_reason

        db.commit()

        db.refresh(existing_risk)

        risk = existing_risk


    # ==================================================
    # CREATE NEW RISK
    # ==================================================

    else:

        risk = StudentRisk(

            student_id=student_id,

            subject_id=subject_id,

            risk_score=risk_score,

            risk_level=risk_level,

            risk_reason=risk_reason
        )

        db.add(risk)

        db.commit()

        db.refresh(risk)


    # ==================================================
    # RESPONSE
    # ==================================================

    return {

        "message":
            "Student risk calculated successfully",

        "risk_id":
            risk.id,

        "student_id":
            student.student_id,

        "student_name":
            student.name,

        "subject_id":
            subject.id,

        "subject_name":
            subject.name,

        "risk_score":
            risk.risk_score,

        "risk_level":
            risk.risk_level,

        "risk_reason":
            risk.risk_reason
    }


# ==================================================
# GET ALL STUDENT RISKS - FACULTY
# ==================================================

@router.get("/")
def get_all_risks(

    db: Session = Depends(get_db),

    current_faculty=Depends(require_faculty)
):

    # ------------------------------------------------
    # GET ASSIGNED SUBJECTS
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

            "risks": []
        }


    # ------------------------------------------------
    # GET ONLY ASSIGNED SUBJECT RISKS
    # ------------------------------------------------

    risk_records = db.query(StudentRisk).filter(

        StudentRisk.subject_id.in_(
            assigned_subject_ids
        )

    ).all()


    # ------------------------------------------------
    # BUILD RESPONSE
    # ------------------------------------------------

    result = []

    for risk in risk_records:

        result.append({

            "risk_id":
                risk.id,

            "student_id":
                risk.student.student_id,

            "student_name":
                risk.student.name,

            "subject_id":
                risk.subject.id,

            "subject_name":
                risk.subject.name,

            "risk_score":
                risk.risk_score,

            "risk_level":
                risk.risk_level,

            "risk_reason":
                risk.risk_reason
        })


    return {

        "total_records":
            len(result),

        "risks":
            result
    }


# ==================================================
# GET RISK OF ONE STUDENT - FACULTY
# ==================================================

@router.get("/student/{student_id}")
def get_student_risk(

    student_id: str,

    db: Session = Depends(get_db),

    current_faculty=Depends(require_faculty)
):

    # ------------------------------------------------
    # CLEAN STUDENT ID
    # ------------------------------------------------

    student_id = student_id.strip()


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
    # GET ASSIGNED SUBJECTS
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

            "risks": []
        }


    # ------------------------------------------------
    # GET ONLY ASSIGNED SUBJECT RISKS
    # ------------------------------------------------

    risk_records = db.query(StudentRisk).filter(

        StudentRisk.student_id == student_id,

        StudentRisk.subject_id.in_(
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
            len(risk_records),

        "risks": [

            {

                "risk_id":
                    risk.id,

                "subject_id":
                    risk.subject.id,

                "subject_name":
                    risk.subject.name,

                "risk_score":
                    risk.risk_score,

                "risk_level":
                    risk.risk_level,

                "risk_reason":
                    risk.risk_reason
            }

            for risk in risk_records
        ]
    }


# ==================================================
# STUDENT CAN SEE ONLY OWN RISK
# ==================================================

@router.get("/my-risk")
def get_my_risk(

    db: Session = Depends(get_db),

    current_student=Depends(require_student)
):

    # ------------------------------------------------
    # GET CURRENT STUDENT
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
    # GET OWN RISKS ONLY
    # ------------------------------------------------

    risk_records = db.query(StudentRisk).filter(

        StudentRisk.student_id ==
        student.student_id

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
            len(risk_records),

        "risks": [

            {

                "risk_id":
                    risk.id,

                "subject_id":
                    risk.subject.id,

                "subject_name":
                    risk.subject.name,

                "risk_score":
                    risk.risk_score,

                "risk_level":
                    risk.risk_level,

                "risk_reason":
                    risk.risk_reason
            }

            for risk in risk_records
        ]
    }


# ==================================================
# EARLY WARNING FOR ONE STUDENT - FACULTY
# ==================================================

@router.get("/student/{student_id}/warning")
def get_student_warning(

    student_id: str,

    db: Session = Depends(get_db),

    current_faculty=Depends(require_faculty)
):

    # ------------------------------------------------
    # CLEAN STUDENT ID
    # ------------------------------------------------

    student_id = student_id.strip()


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

            "early_warning": []
        }


    # ------------------------------------------------
    # GET ONLY ASSIGNED SUBJECT RISKS
    # ------------------------------------------------

    risk_records = db.query(StudentRisk).filter(

        StudentRisk.student_id == student_id,

        StudentRisk.subject_id.in_(
            assigned_subject_ids
        )

    ).all()


    # ------------------------------------------------
    # CHECK RISK DATA
    # ------------------------------------------------

    if not risk_records:

        raise HTTPException(
            status_code=404,
            detail="Risk has not been calculated yet"
        )


    # ------------------------------------------------
    # BUILD EARLY WARNINGS
    # ------------------------------------------------

    warnings = []


    for risk in risk_records:

        if risk.risk_level == "High":

            warning = (
                "Immediate attention required"
            )

        elif risk.risk_level == "Medium":

            warning = (
                "Student needs academic attention"
            )

        else:

            warning = (
                "No immediate warning"
            )


        warnings.append({

            "subject_id":
                risk.subject.id,

            "subject_name":
                risk.subject.name,

            "risk_score":
                risk.risk_score,

            "risk_level":
                risk.risk_level,

            "risk_reason":
                risk.risk_reason,

            "warning":
                warning
        })


    # ------------------------------------------------
    # RESPONSE
    # ------------------------------------------------

    return {

        "student_id":
            student.student_id,

        "student_name":
            student.name,

        "early_warning":
            warnings
    }