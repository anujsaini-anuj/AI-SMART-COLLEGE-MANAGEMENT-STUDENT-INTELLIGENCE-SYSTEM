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

from app.services.ml_training_service import get_training_data


# ---------------------------------------------------
# MODEL PATH
# ---------------------------------------------------

MODEL_DIR = "app/ml_models"

MODEL_PATH = os.path.join(
    MODEL_DIR,
    "student_performance_model.joblib"
)


# ---------------------------------------------------
# TRAIN AND SAVE MODEL
# ---------------------------------------------------

def train_and_save_model(db: Session):

    X, y = get_training_data(db)

    X = np.array(X, dtype=float)
    y = np.array(y, dtype=float)

    # ------------------------------------------------
    # DATA CHECK
    # ------------------------------------------------

    if len(X) < 9:
        raise ValueError(
            "At least 9 performance records are required "
            "for model training."
        )

    # ------------------------------------------------
    # TRAIN / TEST SPLIT
    # ------------------------------------------------

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.3,
        random_state=42
    )

    # ------------------------------------------------
    # CREATE MODEL
    # ------------------------------------------------

    model = RandomForestRegressor(
        n_estimators=100,
        random_state=42
    )

    # ------------------------------------------------
    # TRAIN MODEL
    # ------------------------------------------------

    model.fit(
        X_train,
        y_train
    )

    # ------------------------------------------------
    # EVALUATION
    # ------------------------------------------------

    y_pred = model.predict(
        X_test
    )

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

    # ------------------------------------------------
    # FINAL MODEL
    # Train again using ALL available data
    # ------------------------------------------------

    final_model = RandomForestRegressor(
        n_estimators=100,
        random_state=42
    )

    final_model.fit(
        X,
        y
    )

    # ------------------------------------------------
    # CREATE DIRECTORY
    # ------------------------------------------------

    os.makedirs(
        MODEL_DIR,
        exist_ok=True
    )

    # ------------------------------------------------
    # MODEL METADATA
    # ------------------------------------------------

    model_artifact = {
        "model": final_model,

        "model_name": "Random Forest Regressor",

        "features": [
            "attendance_percentage",
            "marks_percentage",
            "assignment_percentage"
        ],

        "metrics": metrics,

        "training_samples": len(X),

        "trained_at": datetime.now(
            timezone.utc
        ).isoformat()
    }

    # ------------------------------------------------
    # SAVE MODEL + METADATA
    # ------------------------------------------------

    joblib.dump(
        model_artifact,
        MODEL_PATH
    )

    return model_artifact


# ---------------------------------------------------
# LOAD SAVED MODEL
# ---------------------------------------------------

def load_prediction_model():

    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(
            "Trained ML model not found. "
            "Please train the model first."
        )

    model_artifact = joblib.load(
        MODEL_PATH
    )

    return model_artifact


# ---------------------------------------------------
# PREDICT USING SAVED MODEL
# ---------------------------------------------------

def predict_with_saved_model(
    attendance_percentage,
    marks_percentage,
    assignment_percentage
):

    model_artifact = load_prediction_model()

    model = model_artifact["model"]

    input_data = np.array([
        [
            attendance_percentage,
            marks_percentage,
            assignment_percentage
        ]
    ], dtype=float)

    prediction = model.predict(
        input_data
    )[0]

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