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
    create_historical_ml_record,
    get_actual_final_exam_percentage
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
                features["previous_exam_percentage"]
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
#
# AUTOMATIC PREDICTION
#
# Student dashboard open/request karega:
# 1. Student ke course ke subjects niklenge
# 2. Final Exam hai to prediction nahi banegi
# 3. Final Exam nahi hai to latest features calculate honge
# 4. Trained model se prediction hogi
# 5. Prediction database mein create/update hogi
# 6. Student ko latest result milega
# ============================================================

@router.get("/my-prediction")
def get_my_predictions(

    db: Session = Depends(get_db),

    current_student=Depends(require_student)
):

    # ========================================================
    # 1. STUDENT PROFILE
    # ========================================================

    student = (
        db.query(Student)
        .filter(
            Student.user_id == current_student.id
        )
        .first()
    )

    if not student:

        raise HTTPException(
            status_code=404,
            detail="Student profile not found."
        )

    # ========================================================
    # 2. STUDENT COURSE KE SUBJECTS
    # ========================================================

    subjects = (
        db.query(Subject)
        .filter(
            Subject.course_id == student.course_id
        )
        .order_by(
            Subject.semester.asc(),
            Subject.id.asc()
        )
        .all()
    )

    if not subjects:

        return {

            "student": {

                "student_id":
                    student.student_id,

                "student_name":
                    student.name
            },

            "total_subjects":
                0,

            "total_predictions":
                0,

            "predictions":
                [],

            "message":
                "No subjects found for the student's course."
        }

    # ========================================================
    # 3. PROCESS EACH SUBJECT
    # ========================================================

    result = []

    prediction_count = 0

    for subject in subjects:

        # ----------------------------------------------------
        # CHECK FINAL EXAM
        #
        # Service itself performs this check.
        # If Final Exam exists, future prediction is not needed.
        # ----------------------------------------------------

        try:

            (
                prediction,
                features,
                model_info
            ) = predict_future_student_performance(

                db=db,

                student_id=
                    student.student_id,

                subject_id=
                    subject.id
            )

        except ValueError as e:

            message = str(e)

            # ------------------------------------------------
            # FINAL EXAM ALREADY AVAILABLE
            #
            # Future prediction should not be shown.
            # Actual result can be shown instead.
            # ------------------------------------------------

            if (
                "Final Exam result is already available"
                in message
            ):

                actual_percentage = (
                    get_actual_final_exam_percentage(

                        db=db,

                        student_id=
                            student.student_id,

                        subject_id=
                            subject.id
                    )
                )

                if actual_percentage is not None:

                    if actual_percentage >= 80:

                        actual_level = "Excellent"

                    elif actual_percentage >= 60:

                        actual_level = "Good"

                    elif actual_percentage >= 40:

                        actual_level = "Average"

                    else:

                        actual_level = "Poor"

                    result.append({

                        "subject": {

                            "subject_id":
                                subject.id,

                            "subject_name":
                                subject.name,

                            "subject_code":
                                subject.code
                        },

                        "status":
                            "actual_result_available",

                        "prediction":
                            None,

                        "actual_result": {

                            "final_exam_percentage":
                                actual_percentage,

                            "performance_level":
                                actual_level
                        },

                        "message":
                            "Final Exam result is already available. "
                            "Future prediction is not required."
                    })

                continue

            # ------------------------------------------------
            # INSUFFICIENT DATA
            #
            # Student should still see subject status.
            # Do NOT fail the complete endpoint.
            # ------------------------------------------------

            result.append({

                "subject": {

                    "subject_id":
                        subject.id,

                    "subject_name":
                        subject.name,

                    "subject_code":
                        subject.code
                },

                "status":
                    "prediction_unavailable",

                "prediction":
                    None,

                "message":
                    message
            })

            continue

        # ====================================================
        # 4. PREDICTION LEVEL
        # ====================================================

        if prediction >= 80:

            predicted_level = "Excellent"

        elif prediction >= 60:

            predicted_level = "Good"

        elif prediction >= 40:

            predicted_level = "Average"

        else:

            predicted_level = "Poor"

        # ====================================================
        # 5. CREATE / UPDATE SAVED PREDICTION
        # ====================================================

        existing_prediction = (
            db.query(Prediction)
            .filter(

                Prediction.student_id ==
                    student.student_id,

                Prediction.subject_id ==
                    subject.id,

                Prediction.prediction_type ==
                    "Future Final Exam Performance"
            )
            .first()
        )

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

        else:

            prediction_record = Prediction(

                student_id =
                    student.student_id,

                subject_id =
                    subject.id,

                predicted_performance =
                    prediction,

                predicted_level =
                    predicted_level,

                model_name =
                    model_info["model_name"],

                prediction_type =
                    "Future Final Exam Performance"
            )

            db.add(
                prediction_record
            )

        # ====================================================
        # 6. SAVE
        # ====================================================

        try:

            db.commit()

            db.refresh(
                prediction_record
            )

        except Exception:

            db.rollback()

            # One subject ki saving fail ho to
            # baaki subjects continue kar sakein.

            result.append({

                "subject": {

                    "subject_id":
                        subject.id,

                    "subject_name":
                        subject.name,

                    "subject_code":
                        subject.code
                },

                "status":
                    "prediction_save_failed",

                "prediction":
                    None,

                "message":
                    "Prediction was calculated but could not be saved."
            })

            continue

        # ====================================================
        # 7. ADD RESULT
        # ====================================================

        result.append({

            "prediction_id":
                prediction_record.id,

            "subject": {

                "subject_id":
                    subject.id,

                "subject_name":
                    subject.name,

                "subject_code":
                    subject.code
            },

            "status":
                "predicted",

            "input_data": {

                "attendance_percentage":
                    features[
                        "attendance_percentage"
                    ],

                "internal_marks_percentage":
                    features[
                        "internal_marks_percentage"
                    ],

                "assignment_percentage":
                    features[
                        "assignment_percentage"
                    ],

                "previous_exam_percentage":
                    features[
                        "previous_exam_percentage"
                    ]
            },

            "prediction": {

                "predicted_final_exam_percentage":
                    prediction,

                "predicted_level":
                    predicted_level
            },

            "model": {

                "model_name":
                    model_info[
                        "model_name"
                    ],

                "training_samples":
                    model_info[
                        "training_samples"
                    ],

                "evaluation":
                    model_info[
                        "metrics"
                    ]
            },

            "created_at":
                prediction_record.created_at
        })

        prediction_count += 1

    # ========================================================
    # 8. FINAL RESPONSE
    # ========================================================

    return {

        "student": {

            "student_id":
                student.student_id,

            "student_name":
                student.name
        },

        "total_subjects":
            len(subjects),

        "total_predictions":
            prediction_count,

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
            final_percentage,
            training_result
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
                features["previous_exam_percentage"]
        },

        "target": {

            "actual_final_exam_percentage":
                final_percentage
        },


        "automatic_training": {

            "retrained":
                training_result.get(
                    "retrained",
                    False
                ),

            "reason":
                training_result.get(
                    "reason"
                ),

            "training_samples":
                training_result.get(
                    "training_samples"
                ),

            "new_records":
                training_result.get(
                    "new_records"
                )
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
                    record.previous_exam_percentage
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