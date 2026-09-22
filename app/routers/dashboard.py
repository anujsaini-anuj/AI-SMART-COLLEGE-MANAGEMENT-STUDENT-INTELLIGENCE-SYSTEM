from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.models import (
    Student,
    Faculty,
    Course,
    Subject,
    Attendance,
    Marks,
    StudentRisk,
    Performance,
    Prediction,
    Recommendation
)
from app.utils.auth import require_admin, require_faculty, require_student


router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard & Analytics"]
)


# =========================================================
# ADMIN DASHBOARD
# =========================================================

@router.get("/admin")
def admin_dashboard(
    db: Session = Depends(get_db),
    current_user=Depends(require_admin)
):

    total_students = db.query(Student).count()
    total_faculty = db.query(Faculty).count()
    total_courses = db.query(Course).count()
    total_subjects = db.query(Subject).count()

    # Average attendance
    attendance_records = db.query(Attendance).all()

    if attendance_records:
        present_count = sum(
            1 for record in attendance_records
            if record.status.lower() == "present"
        )

        average_attendance = round(
            (present_count / len(attendance_records)) * 100,
            2
        )
    else:
        average_attendance = 0

    # Average marks
    marks_records = db.query(Marks).all()

    if marks_records:
        total_marks_percentage = sum(
            (record.marks_obtained / record.max_marks) * 100
            for record in marks_records
            if record.max_marks > 0
        )

        average_marks = round(
            total_marks_percentage / len(marks_records),
            2
        )
    else:
        average_marks = 0

    # Risk distribution
    high_risk = db.query(StudentRisk).filter(
        StudentRisk.risk_level == "High"
    ).count()

    medium_risk = db.query(StudentRisk).filter(
        StudentRisk.risk_level == "Medium"
    ).count()

    low_risk = db.query(StudentRisk).filter(
        StudentRisk.risk_level == "Low"
    ).count()

    # Performance distribution
    excellent = db.query(Performance).filter(
        Performance.performance_level == "Excellent"
    ).count()

    good = db.query(Performance).filter(
        Performance.performance_level == "Good"
    ).count()

    average = db.query(Performance).filter(
        Performance.performance_level == "Average"
    ).count()

    poor = db.query(Performance).filter(
        Performance.performance_level == "Poor"
    ).count()

    return {
        "dashboard": "Admin Dashboard",

        "college_overview": {
            "total_students": total_students,
            "total_faculty": total_faculty,
            "total_courses": total_courses,
            "total_subjects": total_subjects
        },

        "academic_overview": {
            "average_attendance": average_attendance,
            "average_marks": average_marks
        },

        "risk_overview": {
            "high_risk_students": high_risk,
            "medium_risk_students": medium_risk,
            "low_risk_students": low_risk
        },

        "performance_distribution": {
            "excellent": excellent,
            "good": good,
            "average": average,
            "poor": poor
        }
    }


# =========================================================
# FACULTY DASHBOARD
# =========================================================

@router.get("/faculty")
def faculty_dashboard(
    db: Session = Depends(get_db),
    current_user=Depends(require_faculty)
):

    faculty = db.query(Faculty).filter(
        Faculty.user_id == current_user.id
    ).first()

    if not faculty:
        return {
            "dashboard": "Faculty Dashboard",
            "message": "Faculty profile not found"
        }

    # Assigned subjects
    assigned_subjects = [
        assignment.subject
        for assignment in faculty.faculty_subjects
    ]

    subject_ids = [
        subject.id
        for subject in assigned_subjects
    ]

    # Performance only for assigned subjects
    performance_records = []

    if subject_ids:
        performance_records = db.query(Performance).filter(
            Performance.subject_id.in_(subject_ids)
        ).all()

    # Risk only for assigned subjects
    risk_records = []

    if subject_ids:
        risk_records = db.query(StudentRisk).filter(
            StudentRisk.subject_id.in_(subject_ids)
        ).all()

    # Students represented in faculty's assigned subjects
    student_ids = list(
        set(record.student_id for record in performance_records)
    )

    return {
        "dashboard": "Faculty Dashboard",

        "faculty": {
            "faculty_id": faculty.faculty_id,
            "faculty_name": faculty.name
        },

        "assigned_subjects": [
            {
                "subject_id": subject.id,
                "subject_name": subject.name,
                "subject_code": subject.code
            }
            for subject in assigned_subjects
        ],

        "overview": {
            "total_students": len(student_ids),
            "total_subjects": len(assigned_subjects),
            "total_performance_records": len(performance_records)
        },

        "risk_overview": {
            "high_risk": sum(
                1 for record in risk_records
                if record.risk_level == "High"
            ),
            "medium_risk": sum(
                1 for record in risk_records
                if record.risk_level == "Medium"
            ),
            "low_risk": sum(
                1 for record in risk_records
                if record.risk_level == "Low"
            )
        },

        "performance_overview": {
            "excellent": sum(
                1 for record in performance_records
                if record.performance_level == "Excellent"
            ),
            "good": sum(
                1 for record in performance_records
                if record.performance_level == "Good"
            ),
            "average": sum(
                1 for record in performance_records
                if record.performance_level == "Average"
            ),
            "poor": sum(
                1 for record in performance_records
                if record.performance_level == "Poor"
            )
        }
    }


# =========================================================
# STUDENT DASHBOARD
# =========================================================

@router.get("/student")
def student_dashboard(
    db: Session = Depends(get_db),
    current_user=Depends(require_student)
):

    student = db.query(Student).filter(
        Student.user_id == current_user.id
    ).first()

    if not student:
        return {
            "dashboard": "Student Dashboard",
            "message": "Student profile not found"
        }

    student_id = student.student_id

    performance_records = db.query(Performance).filter(
        Performance.student_id == student_id
    ).all()

    risk_records = db.query(StudentRisk).filter(
        StudentRisk.student_id == student_id
    ).all()

    prediction_records = db.query(Prediction).filter(
        Prediction.student_id == student_id
    ).all()

    recommendation_records = db.query(Recommendation).filter(
        Recommendation.student_id == student_id
    ).all()

    attendance_records = db.query(Attendance).filter(
        Attendance.student_id == student_id
    ).all()

    marks_records = db.query(Marks).filter(
        Marks.student_id == student_id
    ).all()

    # Overall attendance
    if attendance_records:

        present_count = sum(
            1 for record in attendance_records
            if record.status.lower() == "present"
        )

        attendance_percentage = round(
            (present_count / len(attendance_records)) * 100,
            2
        )

    else:
        attendance_percentage = 0

    # Overall marks
    if marks_records:

        marks_percentage = round(
            sum(
                (record.marks_obtained / record.max_marks) * 100
                for record in marks_records
                if record.max_marks > 0
            ) / len(marks_records),
            2
        )

    else:
        marks_percentage = 0

    return {
        "dashboard": "Student Dashboard",

        "student": {
            "student_id": student.student_id,
            "student_name": student.name,
            "semester": student.semester
        },

        "overview": {
            "attendance_percentage": attendance_percentage,
            "marks_percentage": marks_percentage,
            "performance_records": len(performance_records),
            "predictions": len(prediction_records),
            "recommendations": len(recommendation_records)
        },

        "performance": [
            {
                "subject_id": record.subject_id,
                "attendance_percentage": record.attendance_percentage,
                "marks_percentage": record.marks_percentage,
                "assignment_percentage": record.assignment_percentage,
                "overall_percentage": record.overall_percentage,
                "performance_level": record.performance_level
            }
            for record in performance_records
        ],

        "risk": [
            {
                "subject_id": record.subject_id,
                "risk_score": record.risk_score,
                "risk_level": record.risk_level,
                "risk_reason": record.risk_reason
            }
            for record in risk_records
        ],

        "predictions": [
            {
                "subject_id": record.subject_id,
                "predicted_performance": record.predicted_performance,
                "predicted_level": record.predicted_level,
                "model_name": record.model_name
            }
            for record in prediction_records
        ],

        "recommendations": [
            {
                "subject_id": record.subject_id,
                "recommendation": record.recommendation_text,
                "type": record.recommendation_type,
                "priority": record.priority
            }
            for record in recommendation_records
        ]
    }