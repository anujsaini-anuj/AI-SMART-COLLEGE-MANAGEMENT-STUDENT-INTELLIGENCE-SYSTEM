from fastapi import APIRouter, Depends, HTTPException

from sqlalchemy.orm import Session

from app.database.database import get_db

from app.database.models import (
    HOD,
    Faculty,
    Student,
    Subject,
    Course,
    FacultySubject,
    Performance,
    Attendance,
    Marks,
    Assignment,
    StudentRisk,
    Recommendation
)

from app.utils.auth import get_current_hod


router = APIRouter(
    prefix="/hod",
    tags=["HOD Management"]
)


# ==================================================
# GET HOD PROFILE
# ==================================================

@router.get("/me")
def get_hod_profile(
    current_hod: HOD = Depends(get_current_hod)
):

    return {
        "hod_id": current_hod.hod_id,
        "user_id": current_hod.user_id,
        "name": current_hod.user.name,
        "email": current_hod.user.email,
        "phone": current_hod.phone,
        "department_id": current_hod.department_id,
        "department": current_hod.department.name,
        "role": current_hod.user.role
    }


# ==================================================
# GET FACULTY OF HOD'S DEPARTMENT
# ==================================================

@router.get("/faculties")
def get_department_faculties(
    current_hod: HOD = Depends(get_current_hod),
    db: Session = Depends(get_db)
):

    faculties = db.query(Faculty).filter(
        Faculty.department_id == current_hod.department_id
    ).all()

    result = []

    for faculty in faculties:

        result.append({
            "faculty_id": faculty.faculty_id,
            "name": faculty.name,
            "email": faculty.user.email,
            "phone": faculty.phone,
            "designation": faculty.designation,
            "department_id": faculty.department_id,
            "department": faculty.department.name
        })

    return {
        "department_id": current_hod.department_id,
        "department": current_hod.department.name,
        "total_faculty": len(result),
        "faculties": result
    }




# ==================================================
# GET STUDENTS OF HOD'S DEPARTMENT
# ==================================================

@router.get("/students")
def get_department_students(
    current_hod: HOD = Depends(get_current_hod),
    db: Session = Depends(get_db)
):

    students = db.query(Student).filter(
        Student.department_id == current_hod.department_id
    ).all()

    result = []

    for student in students:

        result.append({
            "student_id": student.student_id,
            "name": student.name,
            "email": student.user.email,
            "phone": student.phone,
            "department_id": student.department_id,
            "department": student.department.name,
            "course_id": student.course_id,
            "course": student.course.name,
            "semester": student.semester
        })

    return {
        "department_id": current_hod.department_id,
        "department": current_hod.department.name,
        "total_students": len(result),
        "students": result
    }


# ==================================================
# GET STUDENT BY ID
# ==================================================

@router.get("/students/{student_id}")
def get_department_student(
    student_id: str,
    current_hod: HOD = Depends(get_current_hod),
    db: Session = Depends(get_db)
):

    student_id = student_id.strip()

    student = db.query(Student).filter(
        Student.student_id == student_id,
        Student.department_id == current_hod.department_id
    ).first()

    if not student:

        raise HTTPException(
            status_code=404,
            detail="Student not found in your department"
        )

    return {
        "student_id": student.student_id,
        "name": student.name,
        "email": student.user.email,
        "phone": student.phone,
        "department_id": student.department_id,
        "department": student.department.name,
        "course_id": student.course_id,
        "course": student.course.name,
        "semester": student.semester
    }





# ==================================================
# GET DEPARTMENT STUDENT PERFORMANCE
# ==================================================

@router.get("/performance")
def get_department_performance(
    current_hod: HOD = Depends(get_current_hod),
    db: Session = Depends(get_db)
):

    performance_records = db.query(Performance).join(
        Student,
        Performance.student_id == Student.student_id
    ).filter(
        Student.department_id == current_hod.department_id
    ).all()

    result = []

    for performance in performance_records:

        result.append({
            "student_id": performance.student.student_id,
            "student_name": performance.student.name,
            "subject_id": performance.subject.id,
            "subject_name": performance.subject.name,
            "attendance_percentage": performance.attendance_percentage,
            "marks_percentage": performance.marks_percentage,
            "assignment_percentage": performance.assignment_percentage,
            "overall_percentage": performance.overall_percentage,
            "performance_level": performance.performance_level
        })

    return {
        "department_id": current_hod.department_id,
        "department": current_hod.department.name,
        "total_records": len(result),
        "performance": result
    }





@router.get("/attendance")
def get_department_attendance(
    current_hod: HOD = Depends(get_current_hod),
    db: Session = Depends(get_db)
):

    attendance_records = db.query(Attendance).join(
        Student,
        Attendance.student_id == Student.student_id
    ).filter(
        Student.department_id == current_hod.department_id
    ).all()

    result = []

    for record in attendance_records:

        result.append({
            "student_id": record.student.student_id,
            "student_name": record.student.name,
            "subject_id": record.subject.id,
            "subject_name": record.subject.name,
            "date": record.date,
            "status": record.status
        })

    return {
        "department": current_hod.department.name,
        "total_records": len(result),
        "attendance": result
    }







@router.get("/attendance-summary")
def get_department_attendance_summary(
    current_hod: HOD = Depends(get_current_hod),
    db: Session = Depends(get_db)
):

    students = db.query(Student).filter(
        Student.department_id == current_hod.department_id
    ).all()

    result = []

    for student in students:

        attendance_records = db.query(Attendance).filter(
            Attendance.student_id == student.student_id
        ).all()

        total_classes = len(attendance_records)

        present_classes = sum(
            1 for record in attendance_records
            if record.status.lower() == "present"
        )

        absent_classes = sum(
            1 for record in attendance_records
            if record.status.lower() == "absent"
        )

        if total_classes > 0:
            attendance_percentage = round(
                (present_classes / total_classes) * 100, 2
            )
        else:
            attendance_percentage = 0

        result.append({
            "student_id": student.student_id,
            "student_name": student.name,
            "total_classes": total_classes,
            "present_classes": present_classes,
            "absent_classes": absent_classes,
            "attendance_percentage": attendance_percentage,
            "attendance_status": (
                "Low Attendance"
                if attendance_percentage < 75
                else "Good Attendance"
            )
        })

    return {
        "department": current_hod.department.name,
        "total_students": len(result),
        "attendance_summary": result
    }







@router.get("/marks")
def get_department_marks(
    current_hod: HOD = Depends(get_current_hod),
    db: Session = Depends(get_db)
):

    marks_records = db.query(Marks).join(
        Student,
        Marks.student_id == Student.student_id
    ).filter(
        Student.department_id == current_hod.department_id
    ).all()

    result = []

    for record in marks_records:

        percentage = round(
            (record.marks_obtained / record.max_marks) * 100,
            2
        )

        result.append({
            "student_id": record.student.student_id,
            "student_name": record.student.name,
            "subject_id": record.subject.id,
            "subject_name": record.subject.name,
            "exam_type": record.exam_type,
            "marks_obtained": record.marks_obtained,
            "max_marks": record.max_marks,
            "percentage": percentage,
            "exam_date": record.exam_date
        })

    return {
        "department": current_hod.department.name,
        "total_records": len(result),
        "marks": result
    }







@router.get("/assignments")
def get_department_assignments(
    current_hod: HOD = Depends(get_current_hod),
    db: Session = Depends(get_db)
):

    assignment_records = db.query(Assignment).join(
        Student,
        Assignment.student_id == Student.student_id
    ).filter(
        Student.department_id == current_hod.department_id
    ).all()

    result = []

    for record in assignment_records:

        percentage = None

        if record.marks_obtained is not None:
            percentage = round(
                (record.marks_obtained / record.max_marks) * 100,
                2
            )

        result.append({
            "student_id": record.student.student_id,
            "student_name": record.student.name,
            "subject_id": record.subject.id,
            "subject_name": record.subject.name,
            "assignment_name": record.assignment_name,
            "marks_obtained": record.marks_obtained,
            "max_marks": record.max_marks,
            "percentage": percentage,
            "submission_date": record.submission_date,
            "status": record.status
        })

    return {
        "department": current_hod.department.name,
        "total_records": len(result),
        "assignments": result
    }






# ==================================================
# HOD STUDENT RISK MONITORING
# ==================================================

@router.get("/student-risks")
def get_student_risks(
    current_hod: HOD = Depends(get_current_hod),
    db: Session = Depends(get_db)
):

    risks = (
        db.query(StudentRisk)
        .join(
            Student,
            StudentRisk.student_id == Student.student_id
        )
        .filter(
            Student.department_id == current_hod.department_id
        )
        .all()
    )

    result = []

    for risk in risks:

        result.append({
            "student_id": risk.student.student_id,
            "student_name": risk.student.name,
            "subject_id": risk.subject.id,
            "subject_name": risk.subject.name,
            "risk_score": risk.risk_score,
            "risk_level": risk.risk_level,
            "risk_reason": risk.risk_reason
        })

    return {
        "department": current_hod.department.name,
        "total_risk_records": len(result),
        "student_risks": result
    }





# ==================================================
# HOD STUDENT ACADEMIC REPORT
# ==================================================

@router.get("/students/{student_id}/report")
def get_student_academic_report(
    student_id: str,
    current_hod: HOD = Depends(get_current_hod),
    db: Session = Depends(get_db)
):

    student_id = student_id.strip()

    # ==================================================
    # GET STUDENT
    # ==================================================

    student = db.query(Student).filter(
        Student.student_id == student_id,
        Student.department_id == current_hod.department_id
    ).first()

    if not student:
        raise HTTPException(
            status_code=404,
            detail="Student not found in your department"
        )

    # ==================================================
    # ATTENDANCE
    # ==================================================

    attendance_records = db.query(Attendance).filter(
        Attendance.student_id == student_id
    ).all()

    attendance_summary = []

    for record in attendance_records:

        attendance_summary.append({
            "subject_id": record.subject.id,
            "subject_name": record.subject.name,
            "date": record.date,
            "status": record.status
        })

    total_classes = len(attendance_records)

    present_classes = sum(
        1 for record in attendance_records
        if record.status.lower() == "present"
    )

    attendance_percentage = (
        round((present_classes / total_classes) * 100, 2)
        if total_classes > 0
        else 0
    )

    # ==================================================
    # MARKS
    # ==================================================

    marks_records = db.query(Marks).filter(
        Marks.student_id == student_id
    ).all()

    marks_summary = []

    for record in marks_records:

        percentage = (
            round(
                (record.marks_obtained / record.max_marks) * 100,
                2
            )
            if record.max_marks > 0
            else None
        )

        marks_summary.append({
            "subject_id": record.subject.id,
            "subject_name": record.subject.name,
            "exam_type": record.exam_type,
            "marks_obtained": record.marks_obtained,
            "max_marks": record.max_marks,
            "percentage": percentage,
            "exam_date": record.exam_date
        })

    # ==================================================
    # ASSIGNMENTS
    # ==================================================

    assignment_records = db.query(Assignment).filter(
        Assignment.student_id == student_id
    ).all()

    assignments = []

    for record in assignment_records:

        percentage = None

        if (
            record.marks_obtained is not None
            and record.max_marks > 0
        ):
            percentage = round(
                (record.marks_obtained / record.max_marks) * 100,
                2
            )

        assignments.append({
            "subject_id": record.subject.id,
            "subject_name": record.subject.name,
            "assignment_name": record.assignment_name,
            "marks_obtained": record.marks_obtained,
            "max_marks": record.max_marks,
            "percentage": percentage,
            "status": record.status
        })

    # ==================================================
    # PERFORMANCE
    # ==================================================

    performance_records = db.query(Performance).filter(
        Performance.student_id == student_id
    ).all()

    performance = []

    for record in performance_records:

        performance.append({
            "subject_id": record.subject.id,
            "subject_name": record.subject.name,
            "attendance_percentage": record.attendance_percentage,
            "marks_percentage": record.marks_percentage,
            "assignment_percentage": record.assignment_percentage,
            "overall_percentage": record.overall_percentage,
            "performance_level": record.performance_level
        })

    # ==================================================
    # STUDENT RISK
    # ==================================================

    risk_records = db.query(StudentRisk).filter(
        StudentRisk.student_id == student_id
    ).all()

    risks = []

    for record in risk_records:

        risks.append({
            "subject_id": record.subject.id,
            "subject_name": record.subject.name,
            "risk_score": record.risk_score,
            "risk_level": record.risk_level,
            "risk_reason": record.risk_reason
        })

    # ==================================================
    # FINAL RESPONSE
    # ==================================================

    return {
        "report": "Student Academic Report",

        "student": {
            "student_id": student.student_id,
            "name": student.name,
            "email": student.user.email,
            "department": student.department.name,
            "course": student.course.name,
            "semester": student.semester
        },

        "attendance": {
            "total_classes": total_classes,
            "present_classes": present_classes,
            "attendance_percentage": attendance_percentage,
            "records": attendance_summary
        },

        "marks": marks_summary,

        "assignments": assignments,

        "performance": performance,

        "risk": risks
    }




# ==================================================
# HOD STUDENT EARLY WARNING SYSTEM
# ==================================================

@router.get("/early-warning")
def get_student_early_warnings(
    current_hod: HOD = Depends(get_current_hod),
    db: Session = Depends(get_db)
):

    # ==================================================
    # GET DEPARTMENT STUDENTS
    # ==================================================

    students = db.query(Student).filter(
        Student.department_id == current_hod.department_id
    ).all()

    warning_students = []

    # ==================================================
    # CHECK EACH STUDENT
    # ==================================================

    for student in students:

        warning_reasons = []

        # ----------------------------------------------
        # ATTENDANCE CHECK
        # ----------------------------------------------

        attendance_records = db.query(Attendance).filter(
            Attendance.student_id == student.student_id
        ).all()

        total_classes = len(attendance_records)

        present_classes = sum(
            1 for record in attendance_records
            if record.status.lower() == "present"
        )

        attendance_percentage = (
            round((present_classes / total_classes) * 100, 2)
            if total_classes > 0
            else None
        )

        if (
            attendance_percentage is not None
            and attendance_percentage < 75
        ):
            warning_reasons.append("Low Attendance")

        # ----------------------------------------------
        # PERFORMANCE CHECK
        # ----------------------------------------------

        performance_records = db.query(Performance).filter(
            Performance.student_id == student.student_id
        ).all()

        poor_subjects = []

        for record in performance_records:

            if record.performance_level == "Poor":
                poor_subjects.append(record.subject.name)

        if poor_subjects:
            warning_reasons.append("Poor Academic Performance")

        # ----------------------------------------------
        # RISK CHECK
        # ----------------------------------------------

        risk_records = db.query(StudentRisk).filter(
            StudentRisk.student_id == student.student_id
        ).all()

        high_risk_subjects = []

        for record in risk_records:

            if record.risk_level == "High":
                high_risk_subjects.append(record.subject.name)

        if high_risk_subjects:
            warning_reasons.append("High Student Risk")

        # ----------------------------------------------
        # ADD STUDENT IF ANY WARNING EXISTS
        # ----------------------------------------------

        if warning_reasons:

            warning_students.append({
                "student_id": student.student_id,
                "student_name": student.name,
                "attendance_percentage": attendance_percentage,
                "poor_performance_subjects": poor_subjects,
                "high_risk_subjects": high_risk_subjects,
                "warning_reasons": warning_reasons
            })

    # ==================================================
    # RESPONSE
    # ==================================================

    return {
        "department": current_hod.department.name,
        "total_students": len(students),
        "total_students_requiring_attention": len(warning_students),
        "early_warning_students": warning_students
    }






# ==================================================
# HOD VIEW RECOMMENDATIONS
# ==================================================

@router.get("/recommendations")
def get_department_recommendations(
    db: Session = Depends(get_db),
    current_hod: HOD = Depends(get_current_hod)
):

    records = (
        db.query(Recommendation, Student.name)
        .join(
            Student,
            Recommendation.student_id == Student.student_id
        )
        .filter(
            Student.department_id == current_hod.department_id
        )
        .all()
    )

    recommendations = []

    for recommendation, student_name in records:

        recommendations.append({
            "student_id": recommendation.student_id,
            "student_name": student_name,
            "subject_id": recommendation.subject_id,
            "recommendation_text": recommendation.recommendation_text,
            "recommendation_type": recommendation.recommendation_type,
            "priority": recommendation.priority,
            "created_at": recommendation.created_at
        })

    return {
        "department": current_hod.department.name,
        "total_recommendations": len(recommendations),
        "recommendations": recommendations
    }





# ==================================================
# HOD FACULTY PERFORMANCE MONITORING
# ==================================================

@router.get("/faculty-performance")
def get_faculty_performance(
    current_hod: HOD = Depends(get_current_hod),
    db: Session = Depends(get_db)
):

    faculties = db.query(Faculty).filter(
        Faculty.department_id == current_hod.department_id
    ).all()

    result = []

    for faculty in faculties:

        faculty_subject_records = db.query(FacultySubject).filter(
            FacultySubject.faculty_id == faculty.id
        ).all()

        subject_ids = [
            record.subject_id
            for record in faculty_subject_records
        ]

        subjects_data = []
        all_student_ids = set()

        for subject_id in subject_ids:

            subject = db.query(Subject).filter(
                Subject.id == subject_id
            ).first()

            if not subject:
                continue

            students = db.query(Student).join(
                Course,
                Student.course_id == Course.id
            ).filter(
                Course.id == subject.course_id,
                Student.department_id == current_hod.department_id,
                Student.semester == subject.semester
            ).all()

            student_ids = [
                student.student_id
                for student in students
            ]

            all_student_ids.update(student_ids)

            attendance_records = db.query(Attendance).filter(
                Attendance.subject_id == subject_id,
                Attendance.student_id.in_(student_ids)
            ).all() if student_ids else []

            total_classes = len(attendance_records)

            present_classes = sum(
                1 for record in attendance_records
                if record.status.lower() == "present"
            )

            attendance_percentage = (
                round(
                    (present_classes / total_classes) * 100,
                    2
                )
                if total_classes > 0
                else 0
            )

            marks_records = db.query(Marks).filter(
                Marks.subject_id == subject_id,
                Marks.student_id.in_(student_ids)
            ).all() if student_ids else []

            marks_percentages = [
                (record.marks_obtained / record.max_marks) * 100
                for record in marks_records
                if record.max_marks > 0
            ]

            average_marks = (
                round(
                    sum(marks_percentages) / len(marks_percentages),
                    2
                )
                if marks_percentages
                else 0
            )

            subjects_data.append({
                "subject_id": subject.id,
                "subject_name": subject.name,
                "total_students": len(student_ids),
                "average_attendance": attendance_percentage,
                "average_marks": average_marks
            })

        result.append({
            "faculty_id": faculty.faculty_id,
            "faculty_name": faculty.name,
            "designation": faculty.designation,
            "total_assigned_subjects": len(subject_ids),
            "total_students": len(all_student_ids),
            "subjects": subjects_data
        })

    return {
        "department": current_hod.department.name,
        "total_faculty": len(result),
        "faculty_performance": result
    }