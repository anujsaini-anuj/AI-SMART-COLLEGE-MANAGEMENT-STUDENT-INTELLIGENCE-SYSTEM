import numpy as np

from sqlalchemy.orm import Session

from app.database.models import StudentMLRecord


# ============================================================
# ML FEATURE DEFINITIONS
# ============================================================

FEATURE_NAMES = [
    "attendance_percentage",
    "internal_marks_percentage",
    "assignment_percentage",
    "previous_exam_percentage"
]

TARGET_NAME = "final_exam_percentage"


# ============================================================
# GET ML TRAINING DATA
# ============================================================

def get_ml_training_data(db: Session):

    """
    Get historical ML training data.

    Features:
        1. Attendance percentage
        2. Internal marks percentage
        3. Assignment percentage
        4. Previous exam percentage

    Target:
        Final exam percentage

    IMPORTANT:
        Final exam percentage is ONLY the target.
        It is never used as an input feature.
    """

    records = (
        db.query(StudentMLRecord)
        .order_by(StudentMLRecord.id.asc())
        .all()
    )

    if not records:
        raise ValueError(
            "No ML training data available. "
            "Please create historical ML records first."
        )

    X = []
    y = []

    # ========================================================
    # PROCESS EACH HISTORICAL RECORD
    # ========================================================

    for record in records:

        features = [
            record.attendance_percentage,
            record.internal_marks_percentage,
            record.assignment_percentage,
            record.previous_exam_percentage
        ]

        target = record.final_exam_percentage

        # ----------------------------------------------------
        # SKIP INCOMPLETE RECORDS
        # ----------------------------------------------------

        if any(value is None for value in features):
            continue

        if target is None:
            continue

        # ----------------------------------------------------
        # CONVERT TO FLOAT
        # ----------------------------------------------------

        try:

            features = [
                float(value)
                for value in features
            ]

            target = float(target)

        except (TypeError, ValueError):

            continue

        # ----------------------------------------------------
        # CHECK FOR INVALID NUMBERS
        # ----------------------------------------------------

        if not np.isfinite(features).all():
            continue

        if not np.isfinite(target):
            continue

        # ----------------------------------------------------
        # CHECK PERCENTAGE RANGE
        #
        # All ML features and target must be between
        # 0 and 100 percentage.
        # ----------------------------------------------------

        if not all(
            0 <= value <= 100
            for value in features
        ):
            continue

        if not 0 <= target <= 100:
            continue

        # ----------------------------------------------------
        # ADD VALID DATA TO DATASET
        # ----------------------------------------------------

        X.append(features)
        y.append(target)

    # ========================================================
    # CHECK AFTER CLEANING
    # ========================================================

    if not X:

        raise ValueError(
            "No valid ML training records available."
        )

    # ========================================================
    # CONVERT TO NUMPY ARRAYS
    # ========================================================

    X = np.array(
        X,
        dtype=float
    )

    y = np.array(
        y,
        dtype=float
    )

    # ========================================================
    # FINAL VALIDATION
    # ========================================================

    if X.ndim != 2:
        raise ValueError(
            "Invalid ML feature matrix."
        )

    if X.shape[1] != len(FEATURE_NAMES):

        raise ValueError(
            f"Expected {len(FEATURE_NAMES)} features, "
            f"but received {X.shape[1]}."
        )

    if y.ndim != 1:

        raise ValueError(
            "Invalid ML target array."
        )

    if len(X) != len(y):

        raise ValueError(
            "Feature and target data size mismatch."
        )

    return X, y