import os
import joblib
import numpy as np

from datetime import datetime, timezone

from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score
)

from sqlalchemy.orm import Session

from app.services.ml_dataset_service import get_ml_training_data


MODEL_DIR = "app/ml_models"

MODEL_PATH = os.path.join(
    MODEL_DIR,
    "student_future_performance_model.joblib"
)


def train_and_save_future_model(db: Session):

    # Get training data from StudentMLRecord table
    X, y = get_ml_training_data(db)

    X = np.array(X, dtype=float)
    y = np.array(y, dtype=float)

    # Minimum records required
    if len(X) < 9:
        raise ValueError(
            "At least 9 ML training records are required "
            "for future performance model training."
        )

    # Split data into training and testing
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.3,
        random_state=42
    )

    # Create Random Forest model
    model = RandomForestRegressor(
        n_estimators=100,
        random_state=42
    )

    # Train model
    model.fit(X_train, y_train)

    # Test model
    y_pred = model.predict(X_test)

    # Evaluation metrics
    mae = mean_absolute_error(
        y_test,
        y_pred
    )

    rmse = np.sqrt(
        mean_squared_error(
            y_test,
            y_pred
        )
    )

    r2 = r2_score(
        y_test,
        y_pred
    )

    metrics = {
        "mae": round(float(mae), 2),
        "rmse": round(float(rmse), 2),
        "r2_score": round(float(r2), 2)
    }

    # Train final model using all available records
    final_model = RandomForestRegressor(
        n_estimators=100,
        random_state=42
    )

    final_model.fit(X, y)

    # Model information
    model_artifact = {
        "model": final_model,

        "model_name": "Random Forest Regressor",

        "prediction_type": "Future Final Exam Performance",

        "features": [
            "attendance_percentage",
            "internal_marks_percentage",
            "assignment_percentage",
            "previous_exam_percentage",
            "academic_trend"
        ],

        "target": "final_exam_percentage",

        "metrics": metrics,

        "training_samples": len(X),

        "trained_at": datetime.now(
            timezone.utc
        ).isoformat()
    }

    # Create model directory
    os.makedirs(
        MODEL_DIR,
        exist_ok=True
    )

    # Save model
    joblib.dump(
        model_artifact,
        MODEL_PATH
    )

    return model_artifact


def load_future_prediction_model():

    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(
            "Future performance model not found. "
            "Please train the model first."
        )

    model_artifact = joblib.load(
        MODEL_PATH
    )

    return model_artifact


def predict_future_performance(
    attendance_percentage,
    internal_marks_percentage,
    assignment_percentage,
    previous_exam_percentage,
    academic_trend
):

    model_artifact = load_future_prediction_model()

    model = model_artifact["model"]

    input_data = np.array(
        [[
            attendance_percentage,
            internal_marks_percentage,
            assignment_percentage,
            previous_exam_percentage,
            academic_trend
        ]],
        dtype=float
    )

    prediction = model.predict(
        input_data
    )[0]

    # Keep prediction between 0 and 100
    prediction = round(
        max(
            0,
            min(
                100,
                float(prediction)
            )
        )
    )

    return prediction