from fastapi import (
    APIRouter,
    Depends,
    HTTPException
)

from sqlalchemy.orm import Session

from app.database.database import get_db

from app.database.models import (
    Student,
    Subject,
    Prediction,
    StudentMLRecord,
    Faculty,
    FacultySubject
)

from app.services.prediction_service import (
    train_future_prediction_model,
    predict_future_student_performance,
    create_historical_ml_record
)

from app.utils.auth import (
    require_faculty,
    require_student,
    require_admin
)


router = APIRouter(
    prefix="/prediction",
    tags=["Student Performance Prediction"]
)


# ============================================================
# TRAIN FUTURE PERFORMANCE MODEL
# ADMIN ONLY
# ============================================================

@router.post("/train-future-model")
def train_future_model(
    db: Session = Depends(get_db),
    current_admin=Depends(require_admin)
):

    try:

        result = (
            train_future_prediction_model(db)
        )

    except ValueError as e:

        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

    return {

        "message":
            "Future performance ML model trained and saved successfully",

        "model": {

            "model_name":
                result["model_name"],

            "prediction_type":
                result["prediction_type"],

            "features":
                result["features"],

            "target":
                result["target"],

            "training_samples":
                result["training_samples"],

            "evaluation":
                result["metrics"],

            "trained_at":
                result["trained_at"]
        }
    }


# ============================================================
# FUTURE PERFORMANCE PREDICTION
# FACULTY ONLY
#
# IMPORTANT:
# Only student_id + subject_id are required.
# All ML features are calculated automatically.
# ============================================================

@router.post("/future-performance")
def future_performance_prediction(

    student_id: str,
    subject_id: int,

    db: Session = Depends(get_db),
    current_faculty=Depends(require_faculty)
):

    student_id = student_id.strip()

    if not student_id:

        raise HTTPException(
            status_code=400,
            detail="Student ID cannot be empty."
        )

    # --------------------------------------------------------
    # Faculty profile
    # --------------------------------------------------------

    faculty = db.query(Faculty).filter(
        Faculty.user_id == current_faculty.id
    ).first()

    if not faculty:

        raise HTTPException(
            status_code=404,
            detail="Faculty profile not found."
        )

    # --------------------------------------------------------
    # Student
    # --------------------------------------------------------

    student = db.query(Student).filter(
        Student.student_id == student_id
    ).first()

    if not student:

        raise HTTPException(
            status_code=404,
            detail="Student not found."
        )

    # --------------------------------------------------------
    # Subject
    # --------------------------------------------------------

    subject = db.query(Subject).filter(
        Subject.id == subject_id
    ).first()

    if not subject:

        raise HTTPException(
            status_code=404,
            detail="Subject not found."
        )

    # --------------------------------------------------------
    # Faculty subject authorization
    # --------------------------------------------------------

    faculty_subject = db.query(
        FacultySubject
    ).filter(
        FacultySubject.faculty_id == faculty.id,
        FacultySubject.subject_id == subject_id
    ).first()

    if not faculty_subject:

        raise HTTPException(
            status_code=403,
            detail="You are not assigned to this subject."
        )

    # --------------------------------------------------------
    # IMPORTANT:
    # Prediction service itself checks whether Final Exam
    # already exists.
    # --------------------------------------------------------

    try:

        (
            prediction,
            features,
            model_info
        ) = predict_future_student_performance(

            db=db,

            student_id=student_id,

            subject_id=subject_id
        )

    except ValueError as e:

        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

    # --------------------------------------------------------
    # Prediction level
    # --------------------------------------------------------

    if prediction >= 80:

        predicted_level = "Excellent"

    elif prediction >= 60:

        predicted_level = "Good"

    elif prediction >= 40:

        predicted_level = "Average"

    else:

        predicted_level = "Poor"

    # --------------------------------------------------------
    # Existing prediction
    # --------------------------------------------------------

    existing_prediction = db.query(
        Prediction
    ).filter(

        Prediction.student_id == student_id,

        Prediction.subject_id == subject_id,

        Prediction.prediction_type ==
            "Future Final Exam Performance"

    ).first()

    # --------------------------------------------------------
    # Update existing
    # --------------------------------------------------------

    if existing_prediction:

        existing_prediction.predicted_performance = (
            prediction
        )

        existing_prediction.predicted_level = (
            predicted_level
        )

        existing_prediction.model_name = (
            model_info["model_name"]
        )

        prediction_record = (
            existing_prediction
        )

    # --------------------------------------------------------
    # Create new
    # --------------------------------------------------------

    else:

        prediction_record = Prediction(

            student_id=student_id,

            subject_id=subject_id,

            predicted_performance=
                prediction,

            predicted_level=
                predicted_level,

            model_name=
                model_info["model_name"],

            prediction_type=
                "Future Final Exam Performance"
        )

        db.add(prediction_record)

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    try:

        db.commit()

        db.refresh(
            prediction_record
        )

    except Exception:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Failed to save prediction."
        )

    # --------------------------------------------------------
    # Response
    # --------------------------------------------------------

    return {

        "message":
            "Future performance predicted and saved successfully",

        "prediction_id":
            prediction_record.id,

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

        "input_data": {

            "attendance_percentage":
                features["attendance_percentage"],

            "internal_marks_percentage":
                features["internal_marks_percentage"],

            "assignment_percentage":
                features["assignment_percentage"],

            "previous_exam_percentage":
                features["previous_exam_percentage"],

            "academic_trend":
                features["academic_trend"]
        },

        "prediction": {

            "predicted_final_exam_percentage":
                prediction,

            "predicted_level":
                predicted_level
        },

        "model": {

            "model_name":
                model_info["model_name"],

            "prediction_type":
                model_info["prediction_type"],

            "training_samples":
                model_info["training_samples"],

            "evaluation":
                model_info["metrics"]
        }
    }


# ============================================================
# GET ALL FUTURE PREDICTIONS
# FACULTY ONLY
# ============================================================

@router.get("/")
def get_predictions(

    db: Session = Depends(get_db),

    current_faculty=Depends(require_faculty)
):

    faculty = db.query(Faculty).filter(
        Faculty.user_id == current_faculty.id
    ).first()

    if not faculty:

        raise HTTPException(
            status_code=404,
            detail="Faculty profile not found."
        )

    faculty_subjects = db.query(
        FacultySubject
    ).filter(
        FacultySubject.faculty_id == faculty.id
    ).all()

    subject_ids = [
        item.subject_id
        for item in faculty_subjects
    ]

    if not subject_ids:

        return {

            "faculty": {

                "faculty_id":
                    faculty.faculty_id,

                "faculty_name":
                    faculty.name
            },

            "assigned_subjects": 0,

            "total_predictions": 0,

            "predictions": []
        }

    predictions = db.query(
        Prediction
    ).filter(

        Prediction.subject_id.in_(
            subject_ids
        ),

        Prediction.prediction_type ==
            "Future Final Exam Performance"

    ).order_by(
        Prediction.created_at.desc()
    ).all()

    result = []

    for prediction in predictions:

        result.append({

            "prediction_id":
                prediction.id,

            "student": {

                "student_id":
                    prediction.student.student_id,

                "student_name":
                    prediction.student.name
            },

            "subject": {

                "subject_id":
                    prediction.subject.id,

                "subject_name":
                    prediction.subject.name,

                "subject_code":
                    prediction.subject.code
            },

            "prediction_type":
                prediction.prediction_type,

            "prediction": {

                "predicted_final_exam_percentage":
                    prediction.predicted_performance,

                "predicted_level":
                    prediction.predicted_level
            },

            "model_name":
                prediction.model_name,

            "created_at":
                prediction.created_at
        })

    return {

        "faculty": {

            "faculty_id":
                faculty.faculty_id,

            "faculty_name":
                faculty.name
        },

        "assigned_subjects":
            len(subject_ids),

        "total_predictions":
            len(result),

        "predictions":
            result
    }


# ============================================================
# MY FUTURE PREDICTIONS
# STUDENT ONLY
# ============================================================

@router.get("/my-prediction")
def get_my_predictions(

    db: Session = Depends(get_db),

    current_student=Depends(require_student)
):

    student = db.query(Student).filter(
        Student.user_id == current_student.id
    ).first()

    if not student:

        raise HTTPException(
            status_code=404,
            detail="Student profile not found."
        )

    predictions = db.query(
        Prediction
    ).filter(

        Prediction.student_id ==
            student.student_id,

        Prediction.prediction_type ==
            "Future Final Exam Performance"

    ).order_by(
        Prediction.created_at.desc()
    ).all()

    result = []

    for prediction in predictions:

        result.append({

            "prediction_id":
                prediction.id,

            "subject": {

                "subject_id":
                    prediction.subject.id,

                "subject_name":
                    prediction.subject.name,

                "subject_code":
                    prediction.subject.code
            },

            "prediction_type":
                prediction.prediction_type,

            "prediction": {

                "predicted_final_exam_percentage":
                    prediction.predicted_performance,

                "predicted_level":
                    prediction.predicted_level
            },

            "model_name":
                prediction.model_name,

            "created_at":
                prediction.created_at
        })

    return {

        "student": {

            "student_id":
                student.student_id,

            "student_name":
                student.name
        },

        "total_predictions":
            len(result),

        "predictions":
            result
    }


# ============================================================
# CREATE HISTORICAL ML RECORD
# ADMIN ONLY
#
# IMPORTANT:
# Only student_id + subject_id are required.
#
# Final Exam MUST already exist.
# ============================================================

@router.post("/ml-record")
def create_ml_record(

    student_id: str,
    subject_id: int,

    db: Session = Depends(get_db),

    current_admin=Depends(require_admin)
):

    student_id = student_id.strip()

    if not student_id:

        raise HTTPException(
            status_code=400,
            detail="Student ID cannot be empty."
        )

    try:

        (
            ml_record,
            features,
            final_percentage
        ) = create_historical_ml_record(

            db=db,

            student_id=student_id,

            subject_id=subject_id
        )

    except ValueError as e:

        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

    return {

        "message":
            "Historical ML training record created successfully",

        "ml_record_id":
            ml_record.id,

        "student": {

            "student_id":
                ml_record.student.student_id,

            "student_name":
                ml_record.student.name
        },

        "subject": {

            "subject_id":
                ml_record.subject.id,

            "subject_name":
                ml_record.subject.name,

            "subject_code":
                ml_record.subject.code
        },

        "features": {

            "attendance_percentage":
                features["attendance_percentage"],

            "internal_marks_percentage":
                features["internal_marks_percentage"],

            "assignment_percentage":
                features["assignment_percentage"],

            "previous_exam_percentage":
                features["previous_exam_percentage"],

            "academic_trend":
                features["academic_trend"]
        },

        "target": {

            "actual_final_exam_percentage":
                final_percentage
        }
    }


# ============================================================
# GET ML TRAINING RECORDS
# ADMIN ONLY
# ============================================================

@router.get("/ml-records")
def get_ml_records(

    db: Session = Depends(get_db),

    current_admin=Depends(require_admin)
):

    records = db.query(
        StudentMLRecord
    ).order_by(
        StudentMLRecord.created_at.desc()
    ).all()

    result = []

    for record in records:

        result.append({

            "ml_record_id":
                record.id,

            "student_id":
                record.student.student_id,

            "student_name":
                record.student.name,

            "subject_id":
                record.subject.id,

            "subject_name":
                record.subject.name,

            "features": {

                "attendance_percentage":
                    record.attendance_percentage,

                "internal_marks_percentage":
                    record.internal_marks_percentage,

                "assignment_percentage":
                    record.assignment_percentage,

                "previous_exam_percentage":
                    record.previous_exam_percentage,

                "academic_trend":
                    record.academic_trend
            },

            "target": {

                "final_exam_percentage":
                    record.final_exam_percentage
            },

            "created_at":
                record.created_at
        })

    return {

        "total_records":
            len(result),

        "records":
            result
    }