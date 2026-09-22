from sqlalchemy.orm import Session

from app.services.prediction_model import (
    train_and_save_model,
    load_prediction_model,
    predict_with_saved_model
)

from app.services.future_prediction_model import (
    train_and_save_future_model,
    load_future_prediction_model,
    predict_future_performance
)


def train_prediction_model(db: Session):

    model_artifact = train_and_save_model(db)

    return {
        "model_name": model_artifact["model_name"],
        "features": model_artifact["features"],
        "training_samples": model_artifact["training_samples"],
        "metrics": model_artifact["metrics"],
        "trained_at": model_artifact["trained_at"]
    }


def predict_performance(
    db: Session,
    attendance_percentage,
    marks_percentage,
    assignment_percentage
):

    # ---------------------------------------------
    # CHECK SAVED MODEL
    # ---------------------------------------------

    try:

        model_artifact = load_prediction_model()

    except FileNotFoundError:

        # -----------------------------------------
        # FIRST TIME TRAINING
        # -----------------------------------------

        model_artifact = train_and_save_model(db)

    # ---------------------------------------------
    # PREDICTION
    # ---------------------------------------------

    prediction = predict_with_saved_model(
        attendance_percentage,
        marks_percentage,
        assignment_percentage
    )

    # ---------------------------------------------
    # SAVED MODEL METRICS
    # ---------------------------------------------

    metrics = model_artifact["metrics"]

    return prediction, metrics





def train_future_prediction_model(db: Session):

    model_artifact = train_and_save_future_model(db)

    return {
        "model_name": model_artifact["model_name"],
        "prediction_type": model_artifact["prediction_type"],
        "features": model_artifact["features"],
        "target": model_artifact["target"],
        "training_samples": model_artifact["training_samples"],
        "metrics": model_artifact["metrics"],
        "trained_at": model_artifact["trained_at"]
    }


def predict_future_student_performance(
    db: Session,
    attendance_percentage,
    internal_marks_percentage,
    assignment_percentage,
    previous_exam_percentage,
    academic_trend
):

    try:
        model_artifact = load_future_prediction_model()

    except FileNotFoundError:
        model_artifact = train_and_save_future_model(db)

    prediction = predict_future_performance(
        attendance_percentage,
        internal_marks_percentage,
        assignment_percentage,
        previous_exam_percentage,
        academic_trend
    )

    return prediction, {
        "model_name": model_artifact["model_name"],
        "prediction_type": model_artifact["prediction_type"],
        "metrics": model_artifact["metrics"],
        "training_samples": model_artifact["training_samples"]
    }