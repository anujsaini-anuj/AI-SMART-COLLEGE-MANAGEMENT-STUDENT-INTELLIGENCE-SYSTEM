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

from app.services.ml_dataset_service import (
    get_ml_training_data
)


# ===================================================
# MODEL CONFIGURATION
# ===================================================

MODEL_DIR = "app/ml_models"

MODEL_PATH = os.path.join(
    MODEL_DIR,
    "student_future_performance_model.joblib"
)


# ===================================================
# TRAIN AND SAVE FUTURE PERFORMANCE MODEL
# ===================================================

def train_and_save_future_model(db: Session):
    """
    Train Random Forest model for future final exam
    performance prediction and save the trained model.
    """

    # -------------------------------------------------
    # GET TRAINING DATA
    # -------------------------------------------------

    X, y = get_ml_training_data(db)

    X = np.array(
        X,
        dtype=float
    )

    y = np.array(
        y,
        dtype=float
    )

    # -------------------------------------------------
    # MINIMUM DATA CHECK
    # -------------------------------------------------

    if len(X) < 9:
        raise ValueError(
            "At least 9 ML training records are required "
            "for future performance model training."
        )

    # -------------------------------------------------
    # TRAIN / TEST SPLIT
    # -------------------------------------------------

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.3,
        random_state=42
    )

    # -------------------------------------------------
    # CREATE RANDOM FOREST MODEL
    # -------------------------------------------------

    model = RandomForestRegressor(
        n_estimators=100,
        random_state=42
    )

    # -------------------------------------------------
    # TRAIN MODEL
    # -------------------------------------------------

    model.fit(
        X_train,
        y_train
    )

    # -------------------------------------------------
    # TEST MODEL
    # -------------------------------------------------

    y_pred = model.predict(
        X_test
    )

    # -------------------------------------------------
    # EVALUATION
    # -------------------------------------------------

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
        "mae": round(
            float(mae),
            2
        ),

        "rmse": round(
            float(rmse),
            2
        ),

        "r2_score": round(
            float(r2),
            2
        )
    }

    # -------------------------------------------------
    # TRAIN FINAL MODEL USING ALL DATA
    # -------------------------------------------------

    final_model = RandomForestRegressor(
        n_estimators=100,
        random_state=42
    )

    final_model.fit(
        X,
        y
    )

    # -------------------------------------------------
    # CREATE MODEL DIRECTORY
    # -------------------------------------------------

    os.makedirs(
        MODEL_DIR,
        exist_ok=True
    )

    # -------------------------------------------------
    # MODEL ARTIFACT
    # -------------------------------------------------

    model_artifact = {

        "model": final_model,

        "model_name": (
            "Random Forest Regressor"
        ),

        "prediction_type": (
            "Future Final Exam Performance"
        ),

        "features": [
            "attendance_percentage",
            "internal_marks_percentage",
            "assignment_percentage",
            "previous_exam_percentage"
        ],

        "target": (
            "final_exam_percentage"
        ),

        "metrics": metrics,

        "training_samples": len(X),

        "trained_at": (
            datetime.now(
                timezone.utc
            ).isoformat()
        )
    }

    # -------------------------------------------------
    # SAVE MODEL
    # -------------------------------------------------

    joblib.dump(
        model_artifact,
        MODEL_PATH
    )

    return model_artifact


# ===================================================
# LOAD SAVED MODEL
# ===================================================

def load_future_prediction_model():
    """
    Load the previously trained future prediction model.
    """

    if not os.path.exists(
        MODEL_PATH
    ):
        raise FileNotFoundError(
            "Future performance model not found. "
            "Please train the model first."
        )

    model_artifact = joblib.load(
        MODEL_PATH
    )

    return model_artifact


# ===================================================
# PREDICT FUTURE PERFORMANCE
# ===================================================

def predict_future_performance(
    attendance_percentage,
    internal_marks_percentage,
    assignment_percentage,
    previous_exam_percentage
):
    """
    Predict future final exam percentage.
    """

    # -------------------------------------------------
    # LOAD MODEL
    # -------------------------------------------------

    model_artifact = (
        load_future_prediction_model()
    )

    model = model_artifact[
        "model"
    ]

    # -------------------------------------------------
    # PREPARE INPUT DATA
    # -------------------------------------------------

    input_data = np.array(
        [[
            attendance_percentage,
            internal_marks_percentage,
            assignment_percentage,
            previous_exam_percentage
        ]],
        dtype=float
    )

    # -------------------------------------------------
    # MAKE PREDICTION
    # -------------------------------------------------

    prediction = model.predict(
        input_data
    )[0]

    # -------------------------------------------------
    # KEEP VALUE BETWEEN 0 AND 100
    # -------------------------------------------------

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