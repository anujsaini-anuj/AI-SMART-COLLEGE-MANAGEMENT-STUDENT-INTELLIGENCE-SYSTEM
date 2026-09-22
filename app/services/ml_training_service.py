from sqlalchemy.orm import Session

from app.database.models import Performance


# ---------------------------------------------------
# GET TRAINING DATA FROM DATABASE
# ---------------------------------------------------

def get_training_data(db: Session):

    performance_records = db.query(Performance).all()

    if not performance_records:
        raise ValueError(
            "No performance data available for ML training."
        )

    X = []
    y = []

    for record in performance_records:

        X.append([
            record.attendance_percentage,
            record.marks_percentage,
            record.assignment_percentage
        ])

        y.append(
            record.overall_percentage
        )

    return X, y