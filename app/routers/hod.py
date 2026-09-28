from fastapi import APIRouter, Depends, HTTPException

from sqlalchemy.orm import Session

from app.database.database import get_db

from app.database.models import (
    HOD,
    Faculty,
    Student,
    Performance,
    Attendance,
    Marks,
    Assignment,
    StudentRisk,
    User
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