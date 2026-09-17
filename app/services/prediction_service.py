import numpy as np

from sklearn.ensemble import RandomForestRegressor


# ---------------------------------------------------
# TRAIN MODEL
# ---------------------------------------------------

def train_prediction_model():

    # Training data
    # [attendance, marks, assignment]

    X = np.array([
        [95, 90, 95],
        [90, 85, 90],
        [85, 80, 85],
        [80, 75, 80],
        [75, 70, 75],
        [70, 65, 70],
        [65, 60, 65],
        [60, 55, 60],
        [55, 50, 55],
        [50, 45, 50],
        [45, 40, 45],
        [40, 35, 40]
    ])

    # Overall performance
    y = np.array([
        93,
        88,
        83,
        78,
        73,
        68,
        63,
        58,
        53,
        48,
        43,
        38
    ])

    model = RandomForestRegressor(
        n_estimators=100,
        random_state=42
    )

    model.fit(X, y)

    return model


# ---------------------------------------------------
# PREDICT PERFORMANCE
# ---------------------------------------------------

def predict_performance(
    attendance_percentage,
    marks_percentage,
    assignment_percentage
):

    model = train_prediction_model()

    input_data = np.array([[
        attendance_percentage,
        marks_percentage,
        assignment_percentage
    ]])

    prediction = model.predict(input_data)[0]

    prediction = round(
        max(0, min(100, prediction))
    )

    return prediction