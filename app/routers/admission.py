import re
from uuid import uuid4
from datetime import date

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    Form
)

from pydantic import EmailStr
from sqlalchemy.orm import Session

from app.database.database import get_db

from app.database.models import (
    AdmissionApplication,
    Course,
    Student,
    User,
    StudentSemesterHistory
)

from app.utils.auth import get_current_user
from app.utils.security import hash_password


router = APIRouter(
    prefix="/admissions",
    tags=["Admission Management"]
)


# ==================================================
# ROLE CHECK
# ==================================================

def require_admission_access(current_user):

    if current_user.role not in ["admin", "admission_officer"]:

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin or Admission Officer can access this endpoint."
        )


# ==================================================
# GENERATE STUDENT ID
# ==================================================

def generate_student_id(db: Session):

    existing_ids = db.query(Student.student_id).all()

    highest_number = 0

    for row in existing_ids:

        match = re.fullmatch(r"STU(\d+)", row[0])

        if match:

            highest_number = max(
                highest_number,
                int(match.group(1))
            )

    return f"STU{highest_number + 1:03d}"


# ==================================================
# VALIDATE ACADEMIC YEAR
# ==================================================

def validate_academic_year(academic_year: str):

    pattern = r"^(\d{4})-(\d{4})$"

    match = re.fullmatch(pattern, academic_year)

    if not match:

        raise HTTPException(
            status_code=400,
            detail="Academic year must be in YYYY-YYYY format."
        )

    start_year = int(match.group(1))
    end_year = int(match.group(2))

    if end_year != start_year + 1:

        raise HTTPException(
            status_code=400,
            detail="Academic year must contain consecutive years."
        )


# ==================================================
# DIRECT STUDENT ENROLLMENT
# ==================================================

@router.post(
    "/enroll",
    status_code=status.HTTP_201_CREATED
)
def enroll_student(

    applicant_name: str = Form(...),

    email: EmailStr = Form(...),

    phone: str = Form(...),

    date_of_birth: date | None = Form(None),

    previous_qualification: str = Form(...),

    previous_percentage: float = Form(...),

    course_id: int = Form(...),

    semester: int = Form(..., ge=1, le=8),

    academic_year: str = Form(...),

    initial_password: str = Form(..., min_length=8),

    gender: str | None = Form(None),

    blood_group: str | None = Form(None),

    category: str | None = Form(None),

    nationality: str | None = Form(None),

    father_name: str | None = Form(None),

    mother_name: str | None = Form(None),

    address: str | None = Form(None),

    city: str | None = Form(None),

    state: str | None = Form(None),

    postal_code: str | None = Form(None),

    previous_board: str | None = Form(None),

    passing_year: int | None = Form(None),

    db: Session = Depends(get_db),

    current_user: User = Depends(get_current_user)

):

    require_admission_access(current_user)

    # -----------------------------------------
    # CLEAN INPUTS
    # -----------------------------------------

    applicant_name = applicant_name.strip()
    email = str(email).strip().lower()
    phone = phone.strip()
    previous_qualification = previous_qualification.strip()
    academic_year = academic_year.strip()
    gender = gender.strip() if gender else None

    blood_group = blood_group.strip() if blood_group else None

    category = category.strip() if category else None

    nationality = nationality.strip() if nationality else None

    father_name = father_name.strip() if father_name else None

    mother_name = mother_name.strip() if mother_name else None

    address = address.strip() if address else None

    city = city.strip() if city else None

    state = state.strip() if state else None

    postal_code = postal_code.strip() if postal_code else None

    previous_board = previous_board.strip() if previous_board else None

    # -----------------------------------------
    # VALIDATE NAME
    # -----------------------------------------

    if len(applicant_name) < 2:

        raise HTTPException(
            status_code=400,
            detail="Applicant name must contain at least 2 characters."
        )

    # -----------------------------------------
    # VALIDATE PHONE
    # -----------------------------------------

    normalized_phone = re.sub(r"[\s()-]", "", phone)

    if not re.fullmatch(r"\+?\d{10,15}", normalized_phone):

        raise HTTPException(
            status_code=400,
            detail="Enter a valid phone number containing 10 to 15 digits."
        )

    # -----------------------------------------
    # VALIDATE DATE OF BIRTH
    # -----------------------------------------

    if date_of_birth and date_of_birth > date.today():

        raise HTTPException(
            status_code=400,
            detail="Date of birth cannot be in the future."
        )

    # -----------------------------------------
    # VALIDATE QUALIFICATION
    # -----------------------------------------

    if not previous_qualification:

        raise HTTPException(
            status_code=400,
            detail="Previous qualification cannot be empty."
        )

    # -----------------------------------------
    # VALIDATE PERCENTAGE
    # -----------------------------------------

    if not 0 <= previous_percentage <= 100:

        raise HTTPException(
            status_code=400,
            detail="Previous percentage must be between 0 and 100."
        )

    # -----------------------------------------
    # VALIDATE ACADEMIC YEAR
    # -----------------------------------------

    validate_academic_year(academic_year)

    # -----------------------------------------
    # CHECK COURSE
    # -----------------------------------------

    course = db.query(Course).filter(
        Course.id == course_id
    ).first()

    if not course:

        raise HTTPException(
            status_code=404,
            detail="Course not found."
        )

    # -----------------------------------------
    # CHECK EXISTING USER
    # -----------------------------------------

    existing_user = db.query(User).filter(
        User.email == email
    ).first()

    if existing_user:

        raise HTTPException(
            status_code=409,
            detail="A user account with this email already exists."
        )

    # -----------------------------------------
    # CHECK DUPLICATE ADMISSION
    # -----------------------------------------

    existing_application = db.query(
        AdmissionApplication
    ).filter(
        AdmissionApplication.email == email,
        AdmissionApplication.course_id == course_id,
        AdmissionApplication.academic_year == academic_year
    ).first()

    if existing_application:

        raise HTTPException(
            status_code=409,
            detail="Admission record already exists for this course and academic year."
        )

    # -----------------------------------------
    # GENERATE IDS
    # -----------------------------------------

    application_number = (
        f"APP-{uuid4().hex[:10].upper()}"
    )

    new_student_id = generate_student_id(db)

    try:

        # -------------------------------------
        # CREATE USER ACCOUNT
        # -------------------------------------

        new_user = User(
            name=applicant_name,
            email=email,
            password_hash=hash_password(initial_password),
            role="student"
        )

        db.add(new_user)
        db.flush()

        # -------------------------------------
        # CREATE STUDENT PROFILE
        # -------------------------------------

        new_student = Student(
            user_id=new_user.id,
            student_id=new_student_id,
            name=applicant_name,
            phone=normalized_phone,
            department_id=course.department_id,
            course_id=course_id,
            semester=semester
        )

        db.add(new_student)
        db.flush()

        # -------------------------------------
        # CREATE ADMISSION RECORD
        # -------------------------------------
        new_application = AdmissionApplication(

        application_number=application_number,

        # PERSONAL INFORMATION

        applicant_name=applicant_name,
        email=email,
        phone=normalized_phone,
        date_of_birth=date_of_birth,
        gender=gender,
        blood_group=blood_group,
        category=category,
        nationality=nationality,

        # PARENT INFORMATION

        father_name=father_name,
        mother_name=mother_name,

        # ADDRESS INFORMATION

        address=address,
        city=city,
        state=state,
        postal_code=postal_code,

        # ACADEMIC INFORMATION

        previous_qualification=previous_qualification,
        previous_percentage=previous_percentage,
        previous_board=previous_board,
        passing_year=passing_year,

        course_id=course_id,
        semester=semester,
        academic_year=academic_year,

        # ENROLLMENT INFORMATION

        status="enrolled",
        admitted_by=current_user.id,

        admission_remarks=(
            "Eligibility verified by authorized admission staff. "
            "Student enrolled successfully."
        ),

        enrolled_student_id=new_student_id
        )

        db.add(new_application)

        # -------------------------------------
        # SAVE ALL RECORDS
        # -------------------------------------

        db.commit()

        db.refresh(new_user)
        db.refresh(new_student)
        db.refresh(new_application)

        return {

            "message": "Student successfully admitted and enrolled.",

            "application_id": new_application.id,

            "application_number": new_application.application_number,

            "student_database_id": new_student.id,

            "student_id": new_student.student_id,

            "user_id": new_user.id,

            "name": new_student.name,

            "email": new_user.email,

            "phone": new_student.phone,

            "course_id": new_student.course_id,

            "course": course.name,

            "department_id": new_student.department_id,

            "semester": new_student.semester,

            "academic_year": new_application.academic_year,

            "previous_percentage": new_application.previous_percentage,

            "status": new_application.status

        }

    except Exception:

        db.rollback()
        raise


# ==================================================
# GET ALL ADMISSION RECORDS
# ==================================================

@router.get("/")
def get_all_admissions(

    db: Session = Depends(get_db),

    current_user: User = Depends(get_current_user)

):

    require_admission_access(current_user)

    admissions = (
        db.query(AdmissionApplication)
        .order_by(AdmissionApplication.submitted_at.desc())
        .all()
    )

    return admissions


# ==================================================
# GET ADMISSION BY ID
# ==================================================

@router.get("/{application_id}")
def get_admission(

    application_id: int,

    db: Session = Depends(get_db),

    current_user: User = Depends(get_current_user)

):

    require_admission_access(current_user)

    application = db.query(AdmissionApplication).filter(
        AdmissionApplication.id == application_id
    ).first()

    if not application:

        raise HTTPException(
            status_code=404,
            detail="Admission record not found."
        )

    return application





# ==================================================
# GET COMPLETE STUDENT ADMISSION DETAILS
# ==================================================

@router.get("/students/{student_id}")
def get_student_admission_details(
    student_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    require_admission_access(current_user)

    # ----------------------------------------------
    # FIND STUDENT
    # ----------------------------------------------

    student = db.query(Student).filter(
        Student.student_id == student_id
    ).first()

    if not student:
        raise HTTPException(
            status_code=404,
            detail="Student not found."
        )

    # ----------------------------------------------
    # FIND ADMISSION RECORD
    # ----------------------------------------------

    admission = db.query(AdmissionApplication).filter(
        AdmissionApplication.enrolled_student_id == student.student_id
    ).order_by(
        AdmissionApplication.submitted_at.desc()
    ).first()

    if not admission:
        raise HTTPException(
            status_code=404,
            detail="Admission record not found for this student."
        )

    # ----------------------------------------------
    # RETURN COMPLETE DETAILS
    # ----------------------------------------------

    return {
        "student": {
            "student_id": student.student_id,
            "name": student.name,
            "phone": student.phone,
            "course_id": student.course_id,
            "department_id": student.department_id,
            "current_semester": student.semester
        },

        "admission": {
            "application_id": admission.id,
            "application_number": admission.application_number,
            "status": admission.status,
            "academic_year": admission.academic_year,

            "date_of_birth": admission.date_of_birth,
            "gender": admission.gender,
            "blood_group": admission.blood_group,
            "category": admission.category,
            "nationality": admission.nationality,

            "father_name": admission.father_name,
            "mother_name": admission.mother_name,

            "address": admission.address,
            "city": admission.city,
            "state": admission.state,
            "postal_code": admission.postal_code,

            "previous_qualification": admission.previous_qualification,
            "previous_percentage": admission.previous_percentage,
            "previous_board": admission.previous_board,
            "passing_year": admission.passing_year,

            "admission_semester": admission.semester,

            "admitted_by": admission.admitted_by,
            "admission_remarks": admission.admission_remarks,
            "submitted_at": admission.submitted_at
        }
    }




# ==================================================
# CHANGE STUDENT SEMESTER
# ==================================================

@router.put(
    "/students/{student_id}/semester",
    tags=["Admission Management"]
)
def change_student_semester(
    student_id: str,

    new_semester: int = Form(
        ...,
        ge=1,
        le=8
    ),

    reason: str | None = Form(
        None,
        max_length=300
    ),

    current_user=Depends(get_current_user),

    db: Session = Depends(get_db)
):

    # ----------------------------------------------
    # ROLE CHECK
    # ----------------------------------------------

    if current_user.role not in [
        "admin",
        "admission_officer"
    ]:
        raise HTTPException(
            status_code=403,
            detail=(
                "Only admin or admission officer "
                "can change student semester"
            )
        )

    # ----------------------------------------------
    # FIND STUDENT
    # ----------------------------------------------

    student = db.query(Student).filter(
        Student.student_id == student_id
    ).first()

    if not student:
        raise HTTPException(
            status_code=404,
            detail="Student not found"
        )

    # ----------------------------------------------
    # CHECK SAME SEMESTER
    # ----------------------------------------------

    if student.semester == new_semester:
        raise HTTPException(
            status_code=400,
            detail=(
                "Student is already in "
                f"semester {new_semester}"
            )
        )

    # ----------------------------------------------
    # OLD SEMESTER
    # ----------------------------------------------

    old_semester = student.semester

    # ----------------------------------------------
    # UPDATE CURRENT SEMESTER
    # ----------------------------------------------

    student.semester = new_semester

    # ----------------------------------------------
    # CLEAN REASON
    # ----------------------------------------------

    clean_reason = (
        reason.strip()
        if reason and reason.strip()
        else "Semester updated"
    )

    # ----------------------------------------------
    # SAVE HISTORY
    # ----------------------------------------------

    history = StudentSemesterHistory(
        student_id=student.id,
        old_semester=old_semester,
        new_semester=new_semester,
        updated_by=current_user.id,
        reason=clean_reason
    )

    db.add(history)

    # ----------------------------------------------
    # SAVE DATABASE
    # ----------------------------------------------

    db.commit()

    db.refresh(student)

    return {
        "message": "Student semester updated successfully",

        "student_id": student.student_id,

        "old_semester": old_semester,

        "new_semester": new_semester,

        "updated_by": current_user.name,

        "reason": clean_reason
    }