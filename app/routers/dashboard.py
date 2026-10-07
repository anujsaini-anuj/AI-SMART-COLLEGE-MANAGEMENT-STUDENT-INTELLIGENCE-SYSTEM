from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session


from app.database.database import get_db
from app.database.models import (
    HOD,
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
from app.utils.auth import require_admin, require_faculty, require_student, get_current_hod

from app.database.models import Book, BookCopy, BookIssue
from app.utils.auth import require_librarian, require_accountant

from app.database.models import Librarian, LibraryFinePayment, LibraryFine, Accountant, StudentFee

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

    # =====================================================
    # AVERAGE ATTENDANCE
    # =====================================================

    attendance_records = db.query(Attendance).all()

    if attendance_records:

        present_count = sum(
            1
            for record in attendance_records
            if record.status.lower() == "present"
        )

        average_attendance = round(
            (present_count / len(attendance_records)) * 100,
            2
        )

    else:
        average_attendance = 0

    # =====================================================
    # AVERAGE MARKS
    # =====================================================

    marks_records = db.query(Marks).all()

    valid_marks_records = [
        record
        for record in marks_records
        if record.max_marks > 0
    ]

    if valid_marks_records:

        total_marks_percentage = sum(
            (record.marks_obtained / record.max_marks) * 100
            for record in valid_marks_records
        )

        average_marks = round(
            total_marks_percentage / len(valid_marks_records),
            2
        )

    else:
        average_marks = 0

    # =====================================================
    # RISK DISTRIBUTION
    # =====================================================

    high_risk = db.query(StudentRisk).filter(
        StudentRisk.risk_level == "High"
    ).count()

    medium_risk = db.query(StudentRisk).filter(
        StudentRisk.risk_level == "Medium"
    ).count()

    low_risk = db.query(StudentRisk).filter(
        StudentRisk.risk_level == "Low"
    ).count()

    # =====================================================
    # PERFORMANCE DISTRIBUTION
    # =====================================================

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

    # =====================================================
    # ASSIGNED SUBJECTS
    # =====================================================

    assigned_subjects = [
        assignment.subject
        for assignment in faculty.faculty_subjects
    ]

    subject_ids = [
        subject.id
        for subject in assigned_subjects
    ]

    # =====================================================
    # PERFORMANCE
    # Only assigned subjects
    # =====================================================

    performance_records = []

    if subject_ids:

        performance_records = db.query(Performance).filter(
            Performance.subject_id.in_(subject_ids)
        ).all()

    # =====================================================
    # RISK
    # Only assigned subjects
    # =====================================================

    risk_records = []

    if subject_ids:

        risk_records = db.query(StudentRisk).filter(
            StudentRisk.subject_id.in_(subject_ids)
        ).all()

    # =====================================================
    # STUDENTS
    # Students represented in performance records
    # =====================================================

    student_ids = list(
        set(
            record.student_id
            for record in performance_records
        )
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
                1
                for record in risk_records
                if record.risk_level == "High"
            ),

            "medium_risk": sum(
                1
                for record in risk_records
                if record.risk_level == "Medium"
            ),

            "low_risk": sum(
                1
                for record in risk_records
                if record.risk_level == "Low"
            )
        },

        "performance_overview": {
            "excellent": sum(
                1
                for record in performance_records
                if record.performance_level == "Excellent"
            ),

            "good": sum(
                1
                for record in performance_records
                if record.performance_level == "Good"
            ),

            "average": sum(
                1
                for record in performance_records
                if record.performance_level == "Average"
            ),

            "poor": sum(
                1
                for record in performance_records
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

    # =====================================================
    # STUDENT PROFILE
    # =====================================================

    student = db.query(Student).filter(
        Student.user_id == current_user.id
    ).first()

    if not student:
        raise HTTPException(
            status_code=404,
            detail="Student profile not found"
        )

    student_id = student.student_id

    # =====================================================
    # PERFORMANCE
    # =====================================================

    performance_records = db.query(Performance).filter(
        Performance.student_id == student_id
    ).all()

    # =====================================================
    # RISK
    # =====================================================

    risk_records = db.query(StudentRisk).filter(
        StudentRisk.student_id == student_id
    ).all()

    # =====================================================
    # ATTENDANCE
    # =====================================================

    attendance_records = db.query(Attendance).filter(
        Attendance.student_id == student_id
    ).all()

    if attendance_records:

        present_count = sum(
            1
            for record in attendance_records
            if record.status
            and record.status.lower() == "present"
        )

        attendance_percentage = round(
            (present_count / len(attendance_records)) * 100,
            2
        )

    else:

        attendance_percentage = 0

    # =====================================================
    # MARKS
    # =====================================================

    marks_records = db.query(Marks).filter(
        Marks.student_id == student_id
    ).all()

    valid_marks_records = [
        record
        for record in marks_records
        if record.max_marks
        and record.max_marks > 0
    ]

    if valid_marks_records:

        marks_percentage = round(
            sum(
                (
                    record.marks_obtained /
                    record.max_marks
                ) * 100
                for record in valid_marks_records
            ) / len(valid_marks_records),
            2
        )

    else:

        marks_percentage = 0

    # =====================================================
    # SAVED PREDICTIONS
    # =====================================================

    prediction_records = db.query(Prediction).filter(
        Prediction.student_id == student_id,
        Prediction.prediction_type ==
        "Future Final Exam Performance"
    ).order_by(
        Prediction.created_at.desc()
    ).all()

    # =====================================================
    # RECOMMENDATIONS
    # =====================================================

    recommendation_records = db.query(
        Recommendation
    ).filter(
        Recommendation.student_id == student_id
    ).order_by(
        Recommendation.created_at.desc()
    ).all()

    # =====================================================
    # SUBJECT-WISE DASHBOARD
    # =====================================================

    subject_dashboard = []

    for performance in performance_records:

        subject = db.query(Subject).filter(
            Subject.id == performance.subject_id
        ).first()

        if not subject:
            continue

        # =================================================
        # RISK
        # =================================================

        risk = db.query(StudentRisk).filter(
            StudentRisk.student_id == student_id,
            StudentRisk.subject_id == performance.subject_id
        ).first()

        # =================================================
        # PREDICTION
        # =================================================

        prediction = db.query(Prediction).filter(
            Prediction.student_id == student_id,
            Prediction.subject_id == performance.subject_id,
            Prediction.prediction_type ==
            "Future Final Exam Performance"
        ).order_by(
            Prediction.created_at.desc()
        ).first()

        # =================================================
        # FINAL EXAM
        # =================================================

        final_mark = db.query(Marks).filter(
            Marks.student_id == student_id,
            Marks.subject_id == performance.subject_id,
            Marks.exam_type.ilike("%final%")
        ).first()

        # =================================================
        # ACTUAL OR PREDICTED RESULT
        # =================================================

        if final_mark:

            actual_percentage = round(
                (
                    final_mark.marks_obtained /
                    final_mark.max_marks
                ) * 100,
                2
            )

            if actual_percentage >= 40:
                result_level = "Pass"
            else:
                result_level = "Fail"

            final_exam_result = {
                "result_type": "Actual",
                "percentage": actual_percentage,
                "level": result_level
            }

        elif prediction:

            final_exam_result = {
                "result_type": "Predicted",
                "percentage": prediction.predicted_performance,
                "level": prediction.predicted_level
            }

        else:

            final_exam_result = {
                "result_type": "Not Available",
                "percentage": None,
                "level": None
            }

        # =================================================
        # SUBJECT DATA
        # =================================================

        subject_dashboard.append({

            "subject": {
                "subject_id": subject.id,
                "subject_name": subject.name,
                "subject_code": subject.code
            },

            "performance": {
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

            "risk": {
                "risk_score":
                    risk.risk_score
                    if risk else None,

                "risk_level":
                    risk.risk_level
                    if risk else None,

                "risk_reason":
                    risk.risk_reason
                    if risk else None
            },

            "final_exam": final_exam_result
        })

    # =====================================================
    # RESPONSE
    # =====================================================

    return {

        "dashboard": "Student Dashboard",

        # =================================================
        # STUDENT INFORMATION
        # =================================================

        "student": {

            "student_id": student.student_id,

            "student_name": student.name,

            "semester": student.semester,

            "course": {
                "course_id": student.course.id,
                "course_name": student.course.name,
                "course_code": student.course.code
            },

            "department": {
                "department_id": student.department.id,
                "department_name": student.department.name,
                "department_code": student.department.code
            }
        },

        # =================================================
        # OVERALL OVERVIEW
        # =================================================

        "overview": {

            "attendance_percentage":
                attendance_percentage,

            "marks_percentage":
                marks_percentage,

            "performance_records":
                len(performance_records),

            "predictions":
                len(prediction_records),

            "recommendations":
                len(recommendation_records)
        },

        # =================================================
        # SUBJECT-WISE DATA
        # =================================================

        "subjects": subject_dashboard,

        # =================================================
        # PREDICTIONS
        # =================================================

        "predictions": [

            {
                "subject_id":
                    record.subject_id,

                "predicted_performance":
                    record.predicted_performance,

                "predicted_level":
                    record.predicted_level,

                "model_name":
                    record.model_name

            }

            for record in prediction_records
        ],

        # =================================================
        # RECOMMENDATIONS
        # =================================================

        "recommendations": [

            {
                "subject_id":
                    record.subject_id,

                "recommendation":
                    record.recommendation_text,

                "type":
                    record.recommendation_type,

                "priority":
                    record.priority

            }

            for record in recommendation_records
        ]
    }

# =========================================================
# HOD DASHBOARD
# =========================================================

@router.get("/hod")
def hod_dashboard(
    db: Session = Depends(get_db),
    current_hod: HOD = Depends(get_current_hod)
):

    department_id = current_hod.department_id

    # =====================================================
    # TOTAL STUDENTS
    # =====================================================

    total_students = db.query(Student).filter(
        Student.department_id == department_id
    ).count()

    # =====================================================
    # TOTAL FACULTY
    # =====================================================

    total_faculty = db.query(Faculty).filter(
        Faculty.department_id == department_id
    ).count()

    # =====================================================
    # AVERAGE ATTENDANCE
    # =====================================================

    attendance_records = db.query(Attendance).join(
        Student,
        Attendance.student_id == Student.student_id
    ).filter(
        Student.department_id == department_id
    ).all()

    if attendance_records:

        present_count = sum(
            1
            for record in attendance_records
            if record.status.lower() == "present"
        )

        average_attendance = round(
            (present_count / len(attendance_records)) * 100,
            2
        )

    else:
        average_attendance = 0

    # =====================================================
    # AVERAGE MARKS
    # =====================================================

    marks_records = db.query(Marks).join(
        Student,
        Marks.student_id == Student.student_id
    ).filter(
        Student.department_id == department_id
    ).all()

    valid_marks_records = [
        record
        for record in marks_records
        if record.max_marks > 0
    ]

    if valid_marks_records:

        average_marks = round(
            sum(
                (record.marks_obtained / record.max_marks) * 100
                for record in valid_marks_records
            ) / len(valid_marks_records),
            2
        )

    else:
        average_marks = 0

    # =====================================================
    # RISK DISTRIBUTION
    # =====================================================

    risk_records = db.query(StudentRisk).join(
        Student,
        StudentRisk.student_id == Student.student_id
    ).filter(
        Student.department_id == department_id
    ).all()

    high_risk = sum(
        1 for record in risk_records
        if record.risk_level == "High"
    )

    medium_risk = sum(
        1 for record in risk_records
        if record.risk_level == "Medium"
    )

    low_risk = sum(
        1 for record in risk_records
        if record.risk_level == "Low"
    )

    # =====================================================
    # PERFORMANCE DISTRIBUTION
    # =====================================================

    performance_records = db.query(Performance).join(
        Student,
        Performance.student_id == Student.student_id
    ).filter(
        Student.department_id == department_id
    ).all()

    excellent = sum(
        1 for record in performance_records
        if record.performance_level == "Excellent"
    )

    good = sum(
        1 for record in performance_records
        if record.performance_level == "Good"
    )

    average = sum(
        1 for record in performance_records
        if record.performance_level == "Average"
    )

    poor = sum(
        1 for record in performance_records
        if record.performance_level == "Poor"
    )

    # =====================================================
    # RESPONSE
    # =====================================================

    return {
        "dashboard": "HOD Dashboard",

        "department": {
            "department_id": department_id,
            "department_name": current_hod.department.name
        },

        "college_overview": {
            "total_students": total_students,
            "total_faculty": total_faculty
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
# LIBRARIAN DASHBOARD
# =========================================================

@router.get("/librarian")
def librarian_dashboard(
    db: Session = Depends(get_db),
    current_user=Depends(require_librarian)
):

    # =====================================================
    # LIBRARIAN PROFILE
    # =====================================================

    librarian = db.query(Librarian).filter(
        Librarian.user_id == current_user.id
    ).first()

    if not librarian:
        raise HTTPException(
            status_code=404,
            detail="Librarian profile not found"
        )

    # =====================================================
    # BOOK OVERVIEW
    # =====================================================

    total_books = db.query(Book).count()

    total_copies = db.query(BookCopy).count()

    available_copies = db.query(BookCopy).filter(
        BookCopy.status == "available"
    ).count()

    issued_copies = db.query(BookCopy).filter(
        BookCopy.status == "issued"
    ).count()

    # =====================================================
    # ISSUE OVERVIEW
    # =====================================================

    total_issues = db.query(BookIssue).count()

    active_issues = db.query(BookIssue).filter(
        BookIssue.status == "issued"
    ).count()

    returned_books = db.query(BookIssue).filter(
        BookIssue.status == "returned"
    ).count()

    # =====================================================
    # LIBRARY FINE OVERVIEW
    # =====================================================

    fines = db.query(LibraryFine).all()

    total_assessed_fines = len(fines)

    total_fine_amount = sum(
        fine.fine_amount
        for fine in fines
    )

    # =====================================================
    # FETCH ALL FINE PAYMENTS IN ONE QUERY
    # =====================================================

    issue_ids = [
        fine.issue_id
        for fine in fines
    ]

    payments = []

    if issue_ids:
        payments = db.query(LibraryFinePayment).filter(
            LibraryFinePayment.issue_id.in_(issue_ids)
        ).all()

    # =====================================================
    # CREATE PAYMENT LOOKUP
    # =====================================================

    payment_by_issue = {
        payment.issue_id: payment
        for payment in payments
    }

    # =====================================================
    # CALCULATE FINE SUMMARY
    # =====================================================

    total_collected_fine = 0
    total_pending_fine = 0

    paid_fines = 0
    pending_fines = 0

    for fine in fines:

        payment = payment_by_issue.get(
            fine.issue_id
        )

        if payment:

            total_collected_fine += payment.amount
            paid_fines += 1

        else:

            total_pending_fine += fine.fine_amount
            pending_fines += 1

    # =====================================================
    # RESPONSE
    # =====================================================

    return {
        "dashboard": "Librarian Dashboard",

        "librarian": {
            "librarian_id": librarian.librarian_id,
            "librarian_name": current_user.name
        },

        "book_overview": {
            "total_books": total_books,
            "total_physical_copies": total_copies,
            "available_copies": available_copies,
            "issued_copies": issued_copies
        },

        "issue_overview": {
            "total_transactions": total_issues,
            "currently_issued": active_issues,
            "returned_books": returned_books
        },

        "fine_overview": {
            "total_assessed_fines": total_assessed_fines,
            "total_fine_amount": total_fine_amount,
            "total_collected_fine": total_collected_fine,
            "total_pending_fine": total_pending_fine,
            "paid_fines": paid_fines,
            "pending_fines": pending_fines
        }
    }



# =========================================================
# ACCOUNTANT DASHBOARD
# =========================================================

@router.get("/accountant")
def accountant_dashboard(
    db: Session = Depends(get_db),
    current_user=Depends(require_accountant)
):

    # =====================================================
    # ACCOUNTANT PROFILE
    # =====================================================

    accountant = db.query(Accountant).filter(
        Accountant.user_id == current_user.id
    ).first()

    if not accountant:
        raise HTTPException(
            status_code=404,
            detail="Accountant profile not found"
        )

    # =====================================================
    # COLLEGE FEE OVERVIEW
    # =====================================================

    fee_records = db.query(StudentFee).all()

    total_fee_amount = sum(
        fee.total_fee
        for fee in fee_records
    )

    total_fee_collected = sum(
        fee.paid_amount
        for fee in fee_records
    )

    total_pending_fee = sum(
        fee.pending_amount
        for fee in fee_records
    )

    # =====================================================
    # LIBRARY FINE OVERVIEW
    # =====================================================

    fines = db.query(LibraryFine).all()

    total_fines = len(fines)

    total_assessed_fine = sum(
        fine.fine_amount
        for fine in fines
    )

    # =====================================================
    # FETCH ALL FINE PAYMENTS IN ONE QUERY
    # =====================================================

    issue_ids = [
        fine.issue_id
        for fine in fines
    ]

    payments = []

    if issue_ids:
        payments = db.query(LibraryFinePayment).filter(
            LibraryFinePayment.issue_id.in_(issue_ids)
        ).all()

    # =====================================================
    # CREATE PAYMENT LOOKUP
    # =====================================================

    payment_by_issue = {
        payment.issue_id: payment
        for payment in payments
    }

    # =====================================================
    # CALCULATE FINE SUMMARY
    # =====================================================

    total_collected_fine = 0
    total_pending_fine = 0

    paid_fines = 0
    pending_fines = 0

    for fine in fines:

        payment = payment_by_issue.get(
            fine.issue_id
        )

        if payment:

            total_collected_fine += payment.amount
            paid_fines += 1

        else:

            total_pending_fine += fine.fine_amount
            pending_fines += 1

    # =====================================================
    # RESPONSE
    # =====================================================

    return {
        "dashboard": "Accountant Dashboard",

        "accountant": {
            "accountant_id": accountant.accountant_id,
            "accountant_name": current_user.name
        },

        "college_fee_overview": {
            "total_fee_records": len(fee_records),
            "total_fee_amount": total_fee_amount,
            "total_fee_collected": total_fee_collected,
            "total_pending_fee": total_pending_fee
        },

        "library_fine_overview": {
            "total_fines": total_fines,
            "total_assessed_fine": total_assessed_fine,
            "total_collected_fine": total_collected_fine,
            "total_pending_fine": total_pending_fine,
            "paid_fines": paid_fines,
            "pending_fines": pending_fines
        }
    }