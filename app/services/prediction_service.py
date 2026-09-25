from sqlalchemy.orm import Session

from app.database.models import (
    Student,
    Subject,
    Attendance,
    Marks,
    Assignment,
    Performance,
    StudentMLRecord
)

from app.services.future_prediction_model import (
    train_and_save_future_model,
    load_future_prediction_model,
    predict_future_performance
)


# ============================================================
# HELPER
# ============================================================

def _get_student(
    db: Session,
    student_id: str
):
    return db.query(Student).filter(
        Student.student_id == student_id
    ).first()


def _get_subject(
    db: Session,
    subject_id: int
):
    return db.query(Subject).filter(
        Subject.id == subject_id
    ).first()


# ============================================================
# EXAM TYPE
# ============================================================

def _is_final_exam(exam_type: str) -> bool:

    if not exam_type:
        return False

    return "final" in exam_type.strip().lower()


# ============================================================
# ATTENDANCE PERCENTAGE
# ============================================================

def calculate_attendance_percentage(
    db: Session,
    student_id: str,
    subject_id: int
):

    records = db.query(Attendance).filter(
        Attendance.student_id == student_id,
        Attendance.subject_id == subject_id
    ).all()

    if not records:
        return 0

    total_classes = len(records)

    present_classes = sum(
        1
        for record in records
        if record.status
        and record.status.strip().lower() == "present"
    )

    return round(
        (present_classes / total_classes) * 100
    )


# ============================================================
# ASSIGNMENT PERCENTAGE
# ============================================================

def calculate_assignment_percentage(
    db: Session,
    student_id: str,
    subject_id: int
):

    records = db.query(Assignment).filter(
        Assignment.student_id == student_id,
        Assignment.subject_id == subject_id
    ).all()

    if not records:
        return 0

    valid_records = [
        record
        for record in records
        if record.marks_obtained is not None
        and record.max_marks
        and record.max_marks > 0
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

    if total_max == 0:
        return 0

    return round(
        (total_obtained / total_max) * 100
    )


# ============================================================
# GET ALL MARKS
# ============================================================

def get_student_subject_marks(
    db: Session,
    student_id: str,
    subject_id: int
):

    return db.query(Marks).filter(
        Marks.student_id == student_id,
        Marks.subject_id == subject_id
    ).order_by(
        Marks.exam_date.asc(),
        Marks.id.asc()
    ).all()


# ============================================================
# FINAL EXAM RECORD
# ============================================================

def get_final_exam_record(
    db: Session,
    student_id: str,
    subject_id: int
):

    records = get_student_subject_marks(
        db,
        student_id,
        subject_id
    )

    final_records = [
        record
        for record in records
        if _is_final_exam(record.exam_type)
    ]

    if not final_records:
        return None

    return final_records[-1]


# ============================================================
# EXAM PERCENTAGE
# ============================================================

def calculate_exam_percentage(
    record: Marks
):

    if not record:
        return 0

    if not record.max_marks:
        return 0

    if record.max_marks <= 0:
        return 0

    return round(
        (
            record.marks_obtained
            / record.max_marks
        ) * 100
    )


# ============================================================
# NON-FINAL EXAMS
# ============================================================

def get_non_final_exams(
    db: Session,
    student_id: str,
    subject_id: int
):

    records = get_student_subject_marks(
        db,
        student_id,
        subject_id
    )

    return [
        record
        for record in records
        if not _is_final_exam(record.exam_type)
    ]


# ============================================================
# PREVIOUS EXAM PERCENTAGE
# ============================================================

def calculate_previous_exam_percentage(
    db: Session,
    student_id: str,
    subject_id: int
):

    records = get_non_final_exams(
        db,
        student_id,
        subject_id
    )

    if not records:
        return 0

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
    subject_id: int
):

    # First use existing Performance data if available.
    performance = db.query(Performance).filter(
        Performance.student_id == student_id,
        Performance.subject_id == subject_id
    ).first()

    if performance:
        return performance.marks_percentage

    # Otherwise calculate from non-final exams.
    records = get_non_final_exams(
        db,
        student_id,
        subject_id
    )

    if not records:
        return 0

    percentages = [
        calculate_exam_percentage(record)
        for record in records
    ]

    return round(
        sum(percentages) / len(percentages)
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
            db,
            student_id,
            subject_id
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

    student = _get_student(
        db,
        student_id
    )

    if not student:
        raise ValueError(
            "Student not found."
        )

    subject = _get_subject(
        db,
        subject_id
    )

    if not subject:
        raise ValueError(
            "Subject not found."
        )

    # --------------------------------------------------------
    # VERY IMPORTANT
    # If Final Exam already exists,
    # prediction must NOT be performed.
    # --------------------------------------------------------

    if has_final_exam(
        db,
        student_id,
        subject_id
    ):
        raise ValueError(
            "Final Exam result is already available "
            "for this student and subject. "
            "Prediction is not required."
        )

    attendance_percentage = (
        calculate_attendance_percentage(
            db,
            student_id,
            subject_id
        )
    )

    internal_marks_percentage = (
        calculate_internal_marks_percentage(
            db,
            student_id,
            subject_id
        )
    )

    assignment_percentage = (
        calculate_assignment_percentage(
            db,
            student_id,
            subject_id
        )
    )

    previous_exam_percentage = (
        calculate_previous_exam_percentage(
            db,
            student_id,
            subject_id
        )
    )


    return {
        "attendance_percentage":
            attendance_percentage,

        "internal_marks_percentage":
            internal_marks_percentage,

        "assignment_percentage":
            assignment_percentage,

        "previous_exam_percentage":
            previous_exam_percentage
    }


# ============================================================
# CALCULATE HISTORICAL FEATURES
# ============================================================

def calculate_historical_features(
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

    subject = _get_subject(
        db,
        subject_id
    )

    if not subject:
        raise ValueError(
            "Subject not found."
        )

    # Historical record requires Final Exam.
    final_exam = get_final_exam_record(
        db,
        student_id,
        subject_id
    )

    if not final_exam:
        raise ValueError(
            "Final Exam result is not available. "
            "Historical ML record cannot be created."
        )

    features = {
        "attendance_percentage":
            calculate_attendance_percentage(
                db,
                student_id,
                subject_id
            ),

        "internal_marks_percentage":
            calculate_internal_marks_percentage(
                db,
                student_id,
                subject_id
            ),

        "assignment_percentage":
            calculate_assignment_percentage(
                db,
                student_id,
                subject_id
            ),

        "previous_exam_percentage":
            calculate_previous_exam_percentage(
                db,
                student_id,
                subject_id
            )
    }

    final_percentage = calculate_exam_percentage(
        final_exam
    )

    return features, final_percentage


# ============================================================
# ACTUAL FINAL EXAM PERCENTAGE
# ============================================================

def get_actual_final_exam_percentage(
    db: Session,
    student_id: str,
    subject_id: int
):

    final_exam = get_final_exam_record(
        db,
        student_id,
        subject_id
    )

    if not final_exam:
        return None

    return calculate_exam_percentage(
        final_exam
    )


# ============================================================
# TRAIN MODEL
# ============================================================

def train_future_prediction_model(
    db: Session
):

    model_artifact = (
        train_and_save_future_model(db)
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
    """
    Predict future final exam performance.

    Model must already be trained.
    """

    # --------------------------------------------------------
    # Calculate future features automatically
    # --------------------------------------------------------

    features = calculate_future_features(
        db=db,
        student_id=student_id,
        subject_id=subject_id
    )

    # --------------------------------------------------------
    # Load already trained model
    # --------------------------------------------------------

    try:

        model_info = load_future_prediction_model()

    except FileNotFoundError:

        raise ValueError(
            "Future performance model is not trained yet. "
            "Please train the model first using "
            "'Train Future Model'."
        )

    # --------------------------------------------------------
    # Make prediction
    # --------------------------------------------------------

    prediction = predict_future_performance(
        attendance_percentage=features["attendance_percentage"],
        internal_marks_percentage=features["internal_marks_percentage"],
        assignment_percentage=features["assignment_percentage"],
        previous_exam_percentage=features["previous_exam_percentage"]
    )

    return (
        prediction,
        features,
        model_info
    )
# ============================================================
# CREATE HISTORICAL ML RECORD
# ============================================================

def create_historical_ml_record(
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

    subject = _get_subject(
        db,
        subject_id
    )

    if not subject:
        raise ValueError(
            "Subject not found."
        )

    # --------------------------------------------------------
    # Final Exam MUST exist.
    # --------------------------------------------------------

    final_percentage = (
        get_actual_final_exam_percentage(
            db,
            student_id,
            subject_id
        )
    )

    if final_percentage is None:
        raise ValueError(
            "Final Exam result is not available. "
            "ML training record cannot be created."
        )

    # --------------------------------------------------------
    # Prevent duplicate historical records.
    # --------------------------------------------------------

    existing_records = db.query(
        StudentMLRecord
    ).filter(
        StudentMLRecord.student_id == student_id,
        StudentMLRecord.subject_id == subject_id
    ).all()

    if existing_records:
        raise ValueError(
            "Historical ML record already exists "
            "for this student and subject."
        )

    # --------------------------------------------------------
    # Calculate features automatically.
    # --------------------------------------------------------

    features, final_percentage = (
        calculate_historical_features(
            db,
            student_id,
            subject_id
        )
    )

    # --------------------------------------------------------
    # Create record.
    # --------------------------------------------------------

    ml_record = StudentMLRecord(
        student_id=student_id,
        subject_id=subject_id,

        attendance_percentage=
            features["attendance_percentage"],

        internal_marks_percentage=
            features["internal_marks_percentage"],

        assignment_percentage=
            features["assignment_percentage"],

        previous_exam_percentage=
            features["previous_exam_percentage"],

        final_exam_percentage=
            final_percentage
    )

    db.add(ml_record)

    try:

        db.commit()

    except Exception as e:

        db.rollback()

        raise ValueError(
            "Failed to create ML training record. "
            "The record may already exist or the data may be invalid."
        ) from e

    db.refresh(ml_record)

    return ml_record, features, final_percentage