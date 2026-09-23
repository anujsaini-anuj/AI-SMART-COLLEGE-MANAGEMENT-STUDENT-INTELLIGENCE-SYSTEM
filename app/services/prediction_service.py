from sqlalchemy.orm import Session

from app.services.future_prediction_model import (
    train_and_save_future_model,
    load_future_prediction_model,
    predict_future_performance
)


# ===================================================
# TRAIN FUTURE PREDICTION MODEL
# ===================================================

def train_future_prediction_model(
    db: Session
):
    """
    Train and save the future performance
    prediction model.
    """

    model_artifact = (
        train_and_save_future_model(db)
    )

    return {
        "model_name": model_artifact[
            "model_name"
        ],

        "prediction_type": model_artifact[
            "prediction_type"
        ],

        "features": model_artifact[
            "features"
        ],

        "target": model_artifact[
            "target"
        ],

        "training_samples": model_artifact[
            "training_samples"
        ],

        "metrics": model_artifact[
            "metrics"
        ],

        "trained_at": model_artifact[
            "trained_at"
        ]
    }


# ===================================================
# PREDICT FUTURE STUDENT PERFORMANCE
# ===================================================

def predict_future_student_performance(
    db: Session,
    attendance_percentage,
    internal_marks_percentage,
    assignment_percentage,
    previous_exam_percentage,
    academic_trend
):
    """
    Predict future final exam performance
    for a student.
    """

    # -------------------------------------------------
    # CHECK WHETHER MODEL EXISTS
    # -------------------------------------------------

    try:

        model_artifact = (
            load_future_prediction_model()
        )

    except FileNotFoundError:

        # ---------------------------------------------
        # FIRST-TIME TRAINING
        # ---------------------------------------------

        model_artifact = (
            train_and_save_future_model(db)
        )

    # -------------------------------------------------
    # MAKE PREDICTION
    # -------------------------------------------------

    prediction = predict_future_performance(
        attendance_percentage,
        internal_marks_percentage,
        assignment_percentage,
        previous_exam_percentage,
        academic_trend
    )

    # -------------------------------------------------
    # RETURN PREDICTION + MODEL INFORMATION
    # -------------------------------------------------

    return (
        prediction,
        {
            "model_name": model_artifact[
                "model_name"
            ],

            "prediction_type": model_artifact[
                "prediction_type"
            ],

            "metrics": model_artifact[
                "metrics"
            ],

            "training_samples": model_artifact[
                "training_samples"
            ]
        }
    )