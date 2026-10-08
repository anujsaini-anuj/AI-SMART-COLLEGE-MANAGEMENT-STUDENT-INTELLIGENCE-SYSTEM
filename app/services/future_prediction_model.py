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
    get_ml_training_data,
    FEATURE_NAMES,
    TARGET_NAME
)


# ============================================================
# MODEL CONFIGURATION
# ============================================================

MODEL_DIR = "app/ml_models"

MODEL_PATH = os.path.join(
    MODEL_DIR,
    "student_future_performance_model.joblib"
)

MODEL_NAME = "Random Forest Regressor"

PREDICTION_TYPE = "Future Final Exam Performance"


# ============================================================
# TRAIN AND SAVE MODEL
# ============================================================

def train_and_save_future_model(
    db: Session
):

    """
    Train Random Forest model for future final
    exam performance prediction.
    """

    # --------------------------------------------------------
    # GET TRAINING DATA
    # --------------------------------------------------------

    X, y = get_ml_training_data(
        db
    )

    # --------------------------------------------------------
    # MINIMUM DATA CHECK
    # --------------------------------------------------------

    if len(X) < 9:

        raise ValueError(
            "At least 9 ML training records are required "
            "for future performance model training."
        )

    # --------------------------------------------------------
    # TRAIN / TEST SPLIT
    # --------------------------------------------------------

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.30,
        random_state=42
    )

    # --------------------------------------------------------
    # EVALUATION MODEL
    # --------------------------------------------------------

    evaluation_model = RandomForestRegressor(
        n_estimators=200,
        random_state=42,
        n_jobs=-1
    )

    evaluation_model.fit(
        X_train,
        y_train
    )

    # --------------------------------------------------------
    # TEST MODEL
    # --------------------------------------------------------

    y_pred = evaluation_model.predict(
        X_test
    )

    # --------------------------------------------------------
    # METRICS
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # R2 SCORE
    # --------------------------------------------------------

    if len(y_test) >= 2:

        r2 = r2_score(
            y_test,
            y_pred
        )

    else:

        r2 = 0.0

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

    # --------------------------------------------------------
    # FINAL MODEL
    #
    # After evaluation, train final model using
    # ALL available historical records.
    # --------------------------------------------------------

    final_model = RandomForestRegressor(
        n_estimators=200,
        random_state=42,
        n_jobs=-1
    )

    final_model.fit(
        X,
        y
    )

    # --------------------------------------------------------
    # CREATE MODEL DIRECTORY
    # --------------------------------------------------------

    os.makedirs(
        MODEL_DIR,
        exist_ok=True
    )

    # --------------------------------------------------------
    # MODEL ARTIFACT
    # --------------------------------------------------------

    model_artifact = {

        "model":
            final_model,

        "model_name":
            MODEL_NAME,

        "prediction_type":
            PREDICTION_TYPE,

        "features":
            FEATURE_NAMES,

        "target":
            TARGET_NAME,

        "metrics":
            metrics,

        "training_samples":
            len(X),

        "trained_at":
            datetime.now(
                timezone.utc
            ).isoformat()
    }

    # --------------------------------------------------------
    # SAVE MODEL
    # --------------------------------------------------------

    joblib.dump(
        model_artifact,
        MODEL_PATH
    )

    return model_artifact


# ============================================================
# AUTOMATIC MODEL RETRAINING CHECK
# ============================================================

def retrain_future_model_if_needed(
    db: Session,
    minimum_new_records: int = 1,
    force: bool = False
):

    """
    Automatically retrain the future performance model.

    Retraining happens when:

    1. No model exists.
    2. Existing model is invalid.
    3. Enough new ML records are available.
    4. force=True is passed.

    force=True is important when an existing ML record
    is updated but the total number of rows does not increase.
    """

    # --------------------------------------------------------
    # GET CURRENT TRAINING DATA
    # --------------------------------------------------------

    X, y = get_ml_training_data(
        db
    )

    current_samples = len(X)

    # --------------------------------------------------------
    # MINIMUM TOTAL DATA CHECK
    # --------------------------------------------------------

    if current_samples < 9:

        return {
            "retrained":
                False,

            "reason":
                (
                    "Not enough historical ML records "
                    "available for training. "
                    "At least 9 valid records are required."
                ),

            "training_samples":
                current_samples,

            "new_records":
                0
        }

    # --------------------------------------------------------
    # CHECK EXISTING MODEL
    # --------------------------------------------------------

    model_exists = os.path.exists(
        MODEL_PATH
    )

    # --------------------------------------------------------
    # NO MODEL EXISTS
    # --------------------------------------------------------

    if not model_exists:

        model_artifact = (
            train_and_save_future_model(
                db
            )
        )

        return {
            "retrained":
                True,

            "reason":
                "No existing model found. Model trained.",

            "training_samples":
                model_artifact[
                    "training_samples"
                ],

            "new_records":
                current_samples,

            "model":
                model_artifact
        }

    # --------------------------------------------------------
    # LOAD EXISTING MODEL
    # --------------------------------------------------------

    try:

        existing_model = (
            load_future_prediction_model()
        )

    except (
        FileNotFoundError,
        ValueError,
        KeyError
    ):

        model_artifact = (
            train_and_save_future_model(
                db
            )
        )

        return {
            "retrained":
                True,

            "reason":
                (
                    "Existing model was invalid. "
                    "Model retrained."
                ),

            "training_samples":
                model_artifact[
                    "training_samples"
                ],

            "new_records":
                current_samples,

            "model":
                model_artifact
        }

    # --------------------------------------------------------
    # PREVIOUS TRAINING SAMPLE COUNT
    # --------------------------------------------------------

    previous_training_samples = int(
        existing_model.get(
            "training_samples",
            0
        )
    )

    # --------------------------------------------------------
    # CALCULATE NEW RECORDS
    # --------------------------------------------------------

    new_records = max(
        current_samples
        - previous_training_samples,
        0
    )

    # ========================================================
    # AUTOMATIC 1-DAY RETRAINING CHECK
    # ========================================================

    trained_at = existing_model.get(
        "trained_at"
    )

    one_day_passed = False

    if trained_at:

        try:

            last_trained_at = datetime.fromisoformat(
                trained_at.replace(
                    "Z",
                    "+00:00"
                )
            )

            current_time = datetime.now(
                timezone.utc
            )

            elapsed_time = (
                current_time - last_trained_at
            )

            if elapsed_time.total_seconds() >= 86400:

                one_day_passed = True

        except (
            ValueError,
            TypeError
        ):

            one_day_passed = False

    # ========================================================
    # FORCE RETRAINING
    # ========================================================

    if force:

        model_artifact = (
            train_and_save_future_model(
                db
            )
        )

        return {
            "retrained":
                True,

            "reason":
                (
                    "Model force-retrained after "
                    "historical ML record update."
                ),

            "training_samples":
                model_artifact[
                    "training_samples"
                ],

            "previous_training_samples":
                previous_training_samples,

            "new_records":
                new_records,

            "model":
                model_artifact
        }


    # ========================================================
    # NORMAL NEW RECORD / 1-DAY RETRAINING CHECK
    # ========================================================

    if (
        new_records < minimum_new_records
        and not one_day_passed
    ):

        return {
            "retrained":
                False,

            "reason":
                "Retraining threshold not reached. "
                "Model will retrain after 10 new records "
                "or 1 day.",

            "training_samples":
                current_samples,

            "previous_training_samples":
                previous_training_samples,

            "new_records":
                new_records
        }

    # ========================================================
    # RETRAIN MODEL
    # ========================================================

    model_artifact = (
        train_and_save_future_model(
            db
        )
    )

    return {
        "retrained":
            True,

        "reason":
            (
                "Model automatically retrained because "
                "10 new records were added or 1 day "
                "has passed since the last training."
            ),

        "training_samples":
            model_artifact[
                "training_samples"
            ],

        "previous_training_samples":
            previous_training_samples,

        "new_records":
            new_records,

        "model":
            model_artifact
    }

# ============================================================
# LOAD MODEL
# ============================================================

def load_future_prediction_model():

    # --------------------------------------------------------
    # MODEL FILE CHECK
    # --------------------------------------------------------

    if not os.path.exists(
        MODEL_PATH
    ):

        raise FileNotFoundError(
            "Future performance model not found. "
            "Please train the model first."
        )

    # --------------------------------------------------------
    # LOAD ARTIFACT
    # --------------------------------------------------------

    model_artifact = joblib.load(
        MODEL_PATH
    )

    # --------------------------------------------------------
    # VALIDATE ARTIFACT TYPE
    # --------------------------------------------------------

    if not isinstance(
        model_artifact,
        dict
    ):

        raise ValueError(
            "Invalid future performance model artifact."
        )

    # --------------------------------------------------------
    # VALIDATE FEATURES
    # --------------------------------------------------------

    saved_features = (
        model_artifact.get(
            "features",
            []
        )
    )

    if saved_features != FEATURE_NAMES:

        raise ValueError(
            "Saved prediction model uses an incompatible "
            "feature set. Please retrain the future "
            "performance model."
        )

    # --------------------------------------------------------
    # VALIDATE MODEL OBJECT
    # --------------------------------------------------------

    if "model" not in model_artifact:

        raise ValueError(
            "Saved prediction model is incomplete."
        )

    return model_artifact


# ============================================================
# PREDICT FUTURE PERFORMANCE
# ============================================================

def predict_future_performance(
    attendance_percentage,
    internal_marks_percentage,
    assignment_percentage,
    previous_exam_percentage
):

    """
    Predict future final exam percentage.

    IMPORTANT:
        Final exam marks are NOT used as an input.
    """

    # --------------------------------------------------------
    # LOAD TRAINED MODEL
    # --------------------------------------------------------

    model_artifact = (
        load_future_prediction_model()
    )

    model = (
        model_artifact[
            "model"
        ]
    )

    # --------------------------------------------------------
    # INPUT FEATURES
    #
    # Order MUST MATCH FEATURE_NAMES
    # --------------------------------------------------------

    input_data = np.array(
        [[
            attendance_percentage,
            internal_marks_percentage,
            assignment_percentage,
            previous_exam_percentage
        ]],
        dtype=float
    )

    # --------------------------------------------------------
    # VALIDATE INPUT
    # --------------------------------------------------------

    if not np.isfinite(
        input_data
    ).all():

        raise ValueError(
            "Prediction input contains invalid values."
        )

    # --------------------------------------------------------
    # VALIDATE RANGE
    # --------------------------------------------------------

    if (
        input_data < 0
    ).any() or (
        input_data > 100
    ).any():

        raise ValueError(
            "Prediction input values must be "
            "between 0 and 100."
        )

    # --------------------------------------------------------
    # PREDICT
    # --------------------------------------------------------

    prediction = (
        model.predict(
            input_data
        )[0]
    )

    # --------------------------------------------------------
    # KEEP PREDICTION BETWEEN 0 AND 100
    # --------------------------------------------------------

    prediction = max(
        0.0,
        min(
            100.0,
            float(prediction)
        )
    )

    return round(
        prediction
    )