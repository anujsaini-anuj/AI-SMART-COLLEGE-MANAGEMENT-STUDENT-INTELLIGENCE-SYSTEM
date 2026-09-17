import numpy as np
from sklearn.cluster import KMeans


def segment_students(student_data):

    if len(student_data) < 3:
        raise ValueError(
            "At least 3 students are required for segmentation"
        )

    X = np.array([
        [
            student["attendance_percentage"],
            student["marks_percentage"],
            student["assignment_percentage"]
        ]
        for student in student_data
    ])

    model = KMeans(
        n_clusters=3,
        random_state=42,
        n_init=10
    )

    clusters = model.fit_predict(X)

    # Get cluster centers
    centers = model.cluster_centers_

    # Calculate average score of every cluster
    cluster_scores = {}

    for cluster_number in range(3):

        center = centers[cluster_number]

        average_score = (
            center[0] +
            center[1] +
            center[2]
        ) / 3

        cluster_scores[cluster_number] = average_score

    # Sort clusters from highest to lowest performance
    sorted_clusters = sorted(
        cluster_scores,
        key=cluster_scores.get,
        reverse=True
    )

    # Assign meaningful labels
    cluster_labels = {
        sorted_clusters[0]: "High Performance",
        sorted_clusters[1]: "Medium Performance",
        sorted_clusters[2]: "Low Performance"
    }

    result = []

    for index, student in enumerate(student_data):

        cluster_number = int(clusters[index])

        result.append({
            "student_id": student["student_id"],

            "student_name": student["student_name"],

            "attendance_percentage":
                student["attendance_percentage"],

            "marks_percentage":
                student["marks_percentage"],

            "assignment_percentage":
                student["assignment_percentage"],

            "cluster":
                cluster_number,

            "segment":
                cluster_labels[cluster_number]
        })

    return result