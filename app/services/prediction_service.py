from sqlalchemy.orm import Session

from app.database.models import (
    Student,
    Subject,
    Attendance,
    Marks,
    Assignment,
    StudentMLRecord
)

from app.services.future_prediction_model import (
    train_and_save_future_model,
    load_future_prediction_model,
    predict_future_performance,
    retrain_future_model_if_needed
)


# ============================================================
# ATTENDANCE ELIGIBILITY
# ============================================================

MIN_ATTENDANCE_PERCENTAGE = 75


# ============================================================
# HELPER - GET STUDENT
# ============================================================

def _get_student(
    db: Session,
    student_id: str
):
    return (
        db.query(Student)
        .filter(
            Student.student_id == student_id
        )
        .first()
    )


# ============================================================
# HELPER - GET SUBJECT
# ============================================================

def _get_subject(
    db: Session,
    subject_id: int
):
    return (
        db.query(Subject)
        .filter(
            Subject.id == subject_id
        )
        .first()
    )


# ============================================================
# VALIDATE STUDENT + SUBJECT
# ============================================================

def _validate_student_subject(
    db: Session,
    student_id: str,
    subject_id: int
):

    student = _get_student(
        db,
        student_id
    )

    if not student:
        raise ValueError(
            "Student not found."
        )

    if not student.is_active:
        raise ValueError(
            "Prediction is not allowed for "
            "an inactive student."
        )

    subject = _get_subject(
        db,
        subject_id
    )

    if not subject:
        raise ValueError(
            "Subject not found."
        )

    if subject.course_id != student.course_id:
        raise ValueError(
            "This subject does not belong "
            "to the student's course."
        )

    return student, subject


# ============================================================
# EXAM TYPE CHECK
# ============================================================

def _is_final_exam(
    exam_type: str
) -> bool:

    if not exam_type:
        return False

    return (
        "final"
        in exam_type.strip().lower()
    )


# ============================================================
# ATTENDANCE PERCENTAGE
# ============================================================

def calculate_attendance_percentage(
    db: Session,
    student_id: str,
    subject_id: int,
    cutoff_date=None
):

    records = (
        db.query(Attendance)
        .filter(
            Attendance.student_id == student_id,
            Attendance.subject_id == subject_id
        )
        .all()
    )

    # --------------------------------------------------------
    # APPLY DATE CUTOFF
    # --------------------------------------------------------

    if cutoff_date is not None:

        records = [
            record
            for record in records
            if (
                record.date is not None
                and record.date <= cutoff_date
            )
        ]

    # --------------------------------------------------------
    # NO ATTENDANCE
    # --------------------------------------------------------

    if not records:
        return 0

    total_classes = len(records)

    present_classes = sum(
        1
        for record in records
        if (
            record.status
            and str(
                record.status
            ).strip().lower() == "present"
        )
    )

    return round(
        (
            present_classes
            / total_classes
        ) * 100
    )


# ============================================================
# ASSIGNMENT PERCENTAGE
# ============================================================

def calculate_assignment_percentage(
    db: Session,
    student_id: str,
    subject_id: int,
    cutoff_date=None
):

    records = (
        db.query(Assignment)
        .filter(
            Assignment.student_id == student_id,
            Assignment.subject_id == subject_id
        )
        .all()
    )

    # --------------------------------------------------------
    # APPLY DATE CUTOFF
    # --------------------------------------------------------

    if cutoff_date is not None:

        records = [
            record
            for record in records
            if (
                record.submission_date is not None
                and record.submission_date <= cutoff_date
            )
        ]

    # --------------------------------------------------------
    # ONLY VALID GRADED ASSIGNMENTS
    # --------------------------------------------------------

    valid_records = [
        record
        for record in records
        if (
            record.marks_obtained is not None
            and record.max_marks is not None
            and record.max_marks > 0
        )
    ]

    if not valid_records:
        return 0

    total_obtained = sum(
        record.marks_obtained
        for record in valid_records
    )

    total_max = sum(
        record.max_marks
        for record in valid_records
    )

    if total_max <= 0:
        return 0

    return round(
        (
            total_obtained
            / total_max
        ) * 100
    )


# ============================================================
# GET ALL STUDENT SUBJECT MARKS
# ============================================================

def get_student_subject_marks(
    db: Session,
    student_id: str,
    subject_id: int
):

    return (
        db.query(Marks)
        .filter(
            Marks.student_id == student_id,
            Marks.subject_id == subject_id
        )
        .order_by(
            Marks.exam_date.asc(),
            Marks.id.asc()
        )
        .all()
    )


# ============================================================
# GET FINAL EXAM RECORD
# ============================================================

def get_final_exam_record(
    db: Session,
    student_id: str,
    subject_id: int
):

    records = get_student_subject_marks(
        db=db,
        student_id=student_id,
        subject_id=subject_id
    )

    final_records = [
        record
        for record in records
        if _is_final_exam(
            record.exam_type
        )
    ]

    if not final_records:
        return None

    # Latest final exam record
    return final_records[-1]


# ============================================================
# CALCULATE EXAM PERCENTAGE
# ============================================================

def calculate_exam_percentage(
    record: Marks
):

    if not record:
        return 0

    if record.max_marks is None:
        return 0

    if record.max_marks <= 0:
        return 0

    if record.marks_obtained is None:
        return 0

    return round(
        (
            record.marks_obtained
            / record.max_marks
        ) * 100
    )


# ============================================================
# GET NON-FINAL EXAMS
# ============================================================

def get_non_final_exams(
    db: Session,
    student_id: str,
    subject_id: int,
    before_date=None
):

    records = get_student_subject_marks(
        db=db,
        student_id=student_id,
        subject_id=subject_id
    )

    # --------------------------------------------------------
    # REMOVE FINAL EXAM
    # --------------------------------------------------------

    records = [
        record
        for record in records
        if not _is_final_exam(
            record.exam_type
        )
    ]

    # --------------------------------------------------------
    # ONLY EXAMS BEFORE FINAL EXAM
    # --------------------------------------------------------

    if before_date is not None:

        records = [
            record
            for record in records
            if (
                record.exam_date is not None
                and record.exam_date < before_date
            )
        ]

    return records


# ============================================================
# PREVIOUS EXAM PERCENTAGE
# ============================================================

def calculate_previous_exam_percentage(
    db: Session,
    student_id: str,
    subject_id: int,
    before_date=None
):

    records = get_non_final_exams(
        db=db,
        student_id=student_id,
        subject_id=subject_id,
        before_date=before_date
    )

    if not records:
        return 0

    # Latest non-final exam
    latest_record = records[-1]

    return calculate_exam_percentage(
        latest_record
    )


# ============================================================
# INTERNAL MARKS PERCENTAGE
# ============================================================

def calculate_internal_marks_percentage(
    db: Session,
    student_id: str,
    subject_id: int,
    before_date=None
):

    records = get_non_final_exams(
        db=db,
        student_id=student_id,
        subject_id=subject_id,
        before_date=before_date
    )

    if not records:
        return 0

    percentages = [
        calculate_exam_percentage(
            record
        )
        for record in records
    ]

    if not percentages:
        return 0

    return round(
        sum(percentages)
        / len(percentages)
    )


# ============================================================
# CHECK FINAL EXAM
# ============================================================

def has_final_exam(
    db: Session,
    student_id: str,
    subject_id: int
):

    return (
        get_final_exam_record(
            db=db,
            student_id=student_id,
            subject_id=subject_id
        )
        is not None
    )



# ============================================================
# CALCULATE FUTURE FEATURES
# ============================================================

def calculate_future_features(
    db: Session,
    student_id: str,
    subject_id: int
):

    # --------------------------------------------------------
    # VALIDATE STUDENT + SUBJECT
    # --------------------------------------------------------

    _validate_student_subject(
        db=db,
        student_id=student_id,
        subject_id=subject_id
    )

    # --------------------------------------------------------
    # FINAL EXAM ALREADY AVAILABLE
    # --------------------------------------------------------

    if has_final_exam(
        db=db,
        student_id=student_id,
        subject_id=subject_id
    ):

        raise ValueError(
            "Final Exam result is already available "
            "for this student and subject. "
            "Prediction is not required."
        )

    # --------------------------------------------------------
    # ATTENDANCE RECORDS REQUIRED
    # --------------------------------------------------------

    attendance_records = (
        db.query(Attendance)
        .filter(
            Attendance.student_id == student_id,
            Attendance.subject_id == subject_id
        )
        .all()
    )

    if not attendance_records:

        raise ValueError(
            "Insufficient attendance data for prediction. "
            "Attendance records are required."
        )

    # --------------------------------------------------------
    # NON-FINAL EXAMS REQUIRED
    # --------------------------------------------------------

    non_final_exams = get_non_final_exams(
        db=db,
        student_id=student_id,
        subject_id=subject_id
    )

    if not non_final_exams:

        raise ValueError(
            "Insufficient academic data for prediction. "
            "At least one non-final exam result is required."
        )

    # --------------------------------------------------------
    # CALCULATE FEATURES
    # --------------------------------------------------------

    attendance_percentage = (
        calculate_attendance_percentage(
            db=db,
            student_id=student_id,
            subject_id=subject_id
        )
    )

    internal_marks_percentage = (
        calculate_internal_marks_percentage(
            db=db,
            student_id=student_id,
            subject_id=subject_id
        )
    )

    assignment_percentage = (
        calculate_assignment_percentage(
            db=db,
            student_id=student_id,
            subject_id=subject_id
        )
    )

    previous_exam_percentage = (
        calculate_previous_exam_percentage(
            db=db,
            student_id=student_id,
            subject_id=subject_id
        )
    )

    # --------------------------------------------------------
    # ATTENDANCE ELIGIBILITY
    #
    # Important:
    # Low attendance does NOT stop AI prediction.
    #
    # It only determines college eligibility status.
    # --------------------------------------------------------

    attendance_eligible = (
        attendance_percentage
        >= MIN_ATTENDANCE_PERCENTAGE
    )

    if attendance_eligible:

        eligibility_status = "ELIGIBLE"

    else:

        eligibility_status = "NOT ELIGIBLE"

    # --------------------------------------------------------
    # RETURN FEATURES + ELIGIBILITY
    # --------------------------------------------------------

    return {

        "attendance_percentage":
            attendance_percentage,

        "internal_marks_percentage":
            internal_marks_percentage,

        "assignment_percentage":
            assignment_percentage,

        "previous_exam_percentage":
            previous_exam_percentage,

        "attendance_eligible":
            attendance_eligible,

        "eligibility_status":
            eligibility_status
    }


# ============================================================
# CALCULATE HISTORICAL FEATURES
# ============================================================

def calculate_historical_features(
    db: Session,
    student_id: str,
    subject_id: int
):

    # --------------------------------------------------------
    # VALIDATE STUDENT + SUBJECT
    # --------------------------------------------------------

    _validate_student_subject(
        db=db,
        student_id=student_id,
        subject_id=subject_id
    )

    # --------------------------------------------------------
    # FINAL EXAM REQUIRED
    # --------------------------------------------------------

    final_exam = get_final_exam_record(
        db=db,
        student_id=student_id,
        subject_id=subject_id
    )

    if not final_exam:

        raise ValueError(
            "Final Exam result is not available. "
            "Historical ML record cannot be created."
        )

    # --------------------------------------------------------
    # FINAL EXAM DATE REQUIRED
    #
    # Required to prevent future-data leakage.
    # --------------------------------------------------------

    if final_exam.exam_date is None:

        raise ValueError(
            "Final Exam date is required to create "
            "historical ML training data."
        )

    final_exam_date = final_exam.exam_date

    # --------------------------------------------------------
    # PRE-FINAL EXAMS
    # --------------------------------------------------------

    non_final_exams = get_non_final_exams(
        db=db,
        student_id=student_id,
        subject_id=subject_id,
        before_date=final_exam_date
    )

    if not non_final_exams:

        raise ValueError(
            "At least one non-final exam result "
            "before the Final Exam is required "
            "to create historical ML training data."
        )

    # --------------------------------------------------------
    # PRE-FINAL ATTENDANCE
    # --------------------------------------------------------

    attendance_percentage = (
        calculate_attendance_percentage(
            db=db,
            student_id=student_id,
            subject_id=subject_id,
            cutoff_date=final_exam_date
        )
    )

    if attendance_percentage == 0:

        raise ValueError(
            "Valid pre-final attendance data is required "
            "for historical ML training."
        )

    # --------------------------------------------------------
    # PRE-FINAL INTERNAL MARKS
    # --------------------------------------------------------

    internal_marks_percentage = (
        calculate_internal_marks_percentage(
            db=db,
            student_id=student_id,
            subject_id=subject_id,
            before_date=final_exam_date
        )
    )

    # --------------------------------------------------------
    # PRE-FINAL ASSIGNMENTS
    # --------------------------------------------------------

    assignment_percentage = (
        calculate_assignment_percentage(
            db=db,
            student_id=student_id,
            subject_id=subject_id,
            cutoff_date=final_exam_date
        )
    )

    # --------------------------------------------------------
    # PREVIOUS EXAM
    # --------------------------------------------------------

    previous_exam_percentage = (
        calculate_previous_exam_percentage(
            db=db,
            student_id=student_id,
            subject_id=subject_id,
            before_date=final_exam_date
        )
    )

    # --------------------------------------------------------
    # FINAL EXAM = TARGET
    # --------------------------------------------------------

    final_percentage = (
        calculate_exam_percentage(
            final_exam
        )
    )

    # --------------------------------------------------------
    # FEATURES
    # --------------------------------------------------------

    features = {
        "attendance_percentage":
            attendance_percentage,

        "internal_marks_percentage":
            internal_marks_percentage,

        "assignment_percentage":
            assignment_percentage,

        "previous_exam_percentage":
            previous_exam_percentage
    }

    return (
        features,
        final_percentage
    )


# ============================================================
# ACTUAL FINAL EXAM PERCENTAGE
# ============================================================

def get_actual_final_exam_percentage(
    db: Session,
    student_id: str,
    subject_id: int
):

    final_exam = get_final_exam_record(
        db=db,
        student_id=student_id,
        subject_id=subject_id
    )

    if not final_exam:
        return None

    return calculate_exam_percentage(
        final_exam
    )


# ============================================================
# PERFORMANCE LEVEL
# ============================================================

def get_performance_level(
    percentage: float
) -> str:

    if percentage >= 80:
        return "Excellent"

    elif percentage >= 60:
        return "Good"

    elif percentage >= 40:
        return "Average"

    return "Poor"


# ============================================================
# TRAIN FUTURE MODEL
# ============================================================

def train_future_prediction_model(
    db: Session
):

    model_artifact = (
        train_and_save_future_model(
            db
        )
    )

    return {
        "model_name":
            model_artifact["model_name"],

        "prediction_type":
            model_artifact["prediction_type"],

        "features":
            model_artifact["features"],

        "target":
            model_artifact["target"],

        "metrics":
            model_artifact["metrics"],

        "training_samples":
            model_artifact["training_samples"],

        "trained_at":
            model_artifact["trained_at"]
    }


# ============================================================
# FUTURE STUDENT PREDICTION
# ============================================================

def predict_future_student_performance(
    db: Session,
    student_id: str,
    subject_id: int
):

    # --------------------------------------------------------
    # CALCULATE CURRENT FEATURES
    # --------------------------------------------------------

    features = (
        calculate_future_features(
            db=db,
            student_id=student_id,
            subject_id=subject_id
        )
    )

    # --------------------------------------------------------
    # LOAD TRAINED MODEL
    # --------------------------------------------------------

    try:

        model_info = (
            load_future_prediction_model()
        )

    except FileNotFoundError:

        raise ValueError(
            "Future performance model is not trained yet. "
            "Please train the model first using "
            "'Train Future Model'."
        )

    except ValueError as e:

        raise ValueError(
            str(e)
        )

    # --------------------------------------------------------
    # MAKE PREDICTION
    # --------------------------------------------------------

    prediction = (
        predict_future_performance(

            attendance_percentage=
                features[
                    "attendance_percentage"
                ],

            internal_marks_percentage=
                features[
                    "internal_marks_percentage"
                ],

            assignment_percentage=
                features[
                    "assignment_percentage"
                ],

            previous_exam_percentage=
                features[
                    "previous_exam_percentage"
                ]
        )
    )

    return (
        prediction,
        features,
        model_info
    )


# ============================================================
# CREATE / UPDATE HISTORICAL ML RECORD
# ============================================================

def create_historical_ml_record(
    db: Session,
    student_id: str,
    subject_id: int
):

    # --------------------------------------------------------
    # VALIDATE STUDENT + SUBJECT
    # --------------------------------------------------------

    _validate_student_subject(
        db=db,
        student_id=student_id,
        subject_id=subject_id
    )

    # --------------------------------------------------------
    # CALCULATE HISTORICAL FEATURES
    # --------------------------------------------------------

    features, final_percentage = (
        calculate_historical_features(
            db=db,
            student_id=student_id,
            subject_id=subject_id
        )
    )

    # --------------------------------------------------------
    # FIND EXISTING ML RECORD
    #
    # If final marks are corrected later,
    # update the existing ML record.
    # --------------------------------------------------------

    ml_record = (
        db.query(StudentMLRecord)
        .filter(
            StudentMLRecord.student_id == student_id,
            StudentMLRecord.subject_id == subject_id
        )
        .first()
    )

    is_new_record = (
        ml_record is None
    )

    # --------------------------------------------------------
    # CREATE NEW RECORD
    # --------------------------------------------------------

    if is_new_record:

        ml_record = StudentMLRecord(
            student_id=student_id,
            subject_id=subject_id
        )

        db.add(
            ml_record
        )

    # --------------------------------------------------------
    # UPDATE FEATURES
    # --------------------------------------------------------

    ml_record.attendance_percentage = (
        features[
            "attendance_percentage"
        ]
    )

    ml_record.internal_marks_percentage = (
        features[
            "internal_marks_percentage"
        ]
    )

    ml_record.assignment_percentage = (
        features[
            "assignment_percentage"
        ]
    )

    ml_record.previous_exam_percentage = (
        features[
            "previous_exam_percentage"
        ]
    )

    # --------------------------------------------------------
    # FINAL EXAM = TARGET
    # --------------------------------------------------------

    ml_record.final_exam_percentage = (
        final_percentage
    )

    # --------------------------------------------------------
    # SAVE ML RECORD
    # --------------------------------------------------------

    try:

        db.commit()

        db.refresh(
            ml_record
        )

    except Exception as e:

        db.rollback()

        raise ValueError(
            "Failed to create or update ML training record. "
            "The data may be invalid."
        ) from e

    # ========================================================
    # AUTOMATIC MODEL RETRAINING
    # ========================================================

    try:

        if is_new_record:

            # ------------------------------------------------
            # NEW TRAINING RECORD
            # ------------------------------------------------
            # Retraining happens when the new-record
            # threshold is reached.
            # ------------------------------------------------

            training_result = (
                retrain_future_model_if_needed(
                    db=db,
                    minimum_new_records=1,
                    force=False
                )
            )

        else:

            # ------------------------------------------------
            # EXISTING TRAINING RECORD UPDATED
            # ------------------------------------------------
            # Row count has not increased.
            #
            # Example:
            # Final marks changed from 70 -> 80.
            #
            # Therefore normal new-record detection
            # may not detect this change.
            #
            # Force retraining ensures the model learns
            # from the corrected data.
            # ------------------------------------------------

            training_result = (
                retrain_future_model_if_needed(
                    db=db,
                    minimum_new_records=1,
                    force=True
                )
            )

    except Exception as e:

        # ----------------------------------------------------
        # IMPORTANT:
        # ML training failure must NOT delete the
        # successfully saved ML record.
        # ----------------------------------------------------

        training_result = {
            "retrained": False,
            "reason":
                "Automatic model retraining failed: "
                f"{str(e)}"
        }

    # ========================================================
    # RETURN
    # ========================================================

    return (
        ml_record,
        features,
        final_percentage,
        training_result
    )