import numpy as np

from sqlalchemy.orm import Session

from app.database.models import StudentMLRecord


def get_ml_training_data(db: Session):
    """
    Get training data from StudentMLRecord table.

    Features:
    1. Attendance percentage
    2. Internal marks percentage
    3. Assignment percentage
    4. Previous exam percentage

    Target:
    Final exam percentage
    """

    records = db.query(StudentMLRecord).all()

    if not records:
        raise ValueError(
            "No ML training data available."
        )

    X = []
    y = []

    for record in records:

        # -------------------------------
        # INPUT FEATURES
        # -------------------------------

        X.append([
            record.attendance_percentage,
            record.internal_marks_percentage,
            record.assignment_percentage,
            record.previous_exam_percentage
        ])

        # -------------------------------
        # TARGET
        # -------------------------------

        y.append(
            record.final_exam_percentage
        )

    # Convert to NumPy arrays
    X = np.array(
        X,
        dtype=float
    )

    y = np.array(
        y,
        dtype=float
    )

    return X, y