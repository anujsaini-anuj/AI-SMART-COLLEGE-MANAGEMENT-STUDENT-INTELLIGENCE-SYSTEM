from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sklearn.cluster import KMeans
import numpy as np

from app.database.database import get_db

from app.database.models import (
    Student,
    Performance,
    StudentRisk,
    Prediction,
    Recommendation,
    Faculty,
    FacultySubject
)

from app.utils.auth import (
    require_student,
    require_faculty,
    require_admin
)


router = APIRouter(
    prefix="/intelligence",
    tags=["Student Intelligence"]
)


@router.get("/my-intelligence")
def get_my_intelligence(
    db: Session = Depends(get_db),
    current_student=Depends(require_student)
):
    # Find student profile
    student = db.query(Student).filter(
        Student.user_id == current_student.id
    ).first()

    if not student:
        raise HTTPException(
            status_code=404,
            detail="Student profile not found."
        )

    student_id = student.student_id

    # -------------------------------------------------
    # PERFORMANCE
    # -------------------------------------------------

    performance_records = db.query(Performance).filter(
        Performance.student_id == student_id
    ).all()

    performance_data = []

    for record in performance_records:
        performance_data.append({
            "subject_id": record.subject.id,
            "subject_name": record.subject.name,
            "subject_code": record.subject.code,
            "attendance_percentage": record.attendance_percentage,
            "marks_percentage": record.marks_percentage,
            "assignment_percentage": record.assignment_percentage,
            "overall_percentage": record.overall_percentage,
            "performance_level": record.performance_level
        })

    # -------------------------------------------------
    # RISK
    # -------------------------------------------------

    risk_records = db.query(StudentRisk).filter(
        StudentRisk.student_id == student_id
    ).all()

    risk_data = []

    for record in risk_records:
        risk_data.append({
            "subject_id": record.subject.id,
            "subject_name": record.subject.name,
            "risk_score": record.risk_score,
            "risk_level": record.risk_level,
            "risk_reason": record.risk_reason
        })

    # -------------------------------------------------
    # PREDICTIONS
    # -------------------------------------------------

    prediction_records = db.query(Prediction).filter(
        Prediction.student_id == student_id
    ).order_by(
        Prediction.created_at.desc()
    ).all()

    prediction_data = []

    for record in prediction_records:
        prediction_data.append({
            "prediction_id": record.id,
            "subject_id": record.subject.id,
            "subject_name": record.subject.name,
            "subject_code": record.subject.code,
            "prediction_type": record.prediction_type,
            "predicted_performance": record.predicted_performance,
            "predicted_level": record.predicted_level,
            "model_name": record.model_name,
            "created_at": record.created_at
        })

    # -------------------------------------------------
    # RECOMMENDATIONS
    # -------------------------------------------------

    recommendation_records = db.query(
        Recommendation
    ).filter(
        Recommendation.student_id == student_id
    ).order_by(
        Recommendation.created_at.desc()
    ).all()

    recommendation_data = []

    for record in recommendation_records:
        recommendation_data.append({
            "recommendation_id": record.id,
            "subject_id": record.subject.id,
            "subject_name": record.subject.name,
            "recommendation": record.recommendation_text,
            "recommendation_type": record.recommendation_type,
            "priority": record.priority,
            "created_at": record.created_at
        })

    # -------------------------------------------------
    # STUDENT LEVEL K-MEANS SEGMENTATION
    # -------------------------------------------------

    all_performance = db.query(Performance).all()

    student_features = {}

    for record in all_performance:

        if record.student_id not in student_features:
            student_features[record.student_id] = {
                "attendance": [],
                "marks": [],
                "assignment": []
            }

        student_features[record.student_id]["attendance"].append(
            record.attendance_percentage
        )

        student_features[record.student_id]["marks"].append(
            record.marks_percentage
        )

        student_features[record.student_id]["assignment"].append(
            record.assignment_percentage
        )

    student_ids = list(student_features.keys())

    segment_data = None

    if len(student_ids) >= 3:

        X = []

        for sid in student_ids:

            data = student_features[sid]

            X.append([
                np.mean(data["attendance"]),
                np.mean(data["marks"]),
                np.mean(data["assignment"])
            ])

        X = np.array(X, dtype=float)

        kmeans = KMeans(
            n_clusters=3,
            n_init=10,
            random_state=42
        )

        clusters = kmeans.fit_predict(X)

        centers = kmeans.cluster_centers_

        # Calculate average center for each cluster
        cluster_scores = {}

        for cluster_number in range(3):
            cluster_scores[cluster_number] = np.mean(
                centers[cluster_number]
            )

        # Sort clusters from low to high performance
        sorted_clusters = sorted(
            cluster_scores,
            key=cluster_scores.get
        )

        low_cluster = sorted_clusters[0]
        medium_cluster = sorted_clusters[1]
        high_cluster = sorted_clusters[2]

        current_index = student_ids.index(student_id)
        current_cluster = int(
            clusters[current_index]
        )

        if current_cluster == high_cluster:
            segment = "High Performance"

        elif current_cluster == medium_cluster:
            segment = "Medium Performance"

        else:
            segment = "Low Performance"

        current_features = X[current_index]

        segment_data = {
            "segment": segment,
            "cluster": current_cluster,
            "average_attendance": round(
                float(current_features[0]), 2
            ),
            "average_marks": round(
                float(current_features[1]), 2
            ),
            "average_assignment": round(
                float(current_features[2]), 2
            )
        }

    else:

        segment_data = {
            "segment": "Not Available",
            "cluster": None,
            "average_attendance": None,
            "average_marks": None,
            "average_assignment": None
        }

    # -------------------------------------------------
    # SUMMARY
    # -------------------------------------------------

    average_attendance = None
    average_marks = None
    average_assignment = None
    average_overall = None

    if performance_records:

        average_attendance = round(
            sum(
                r.attendance_percentage
                for r in performance_records
            ) / len(performance_records),
            2
        )

        average_marks = round(
            sum(
                r.marks_percentage
                for r in performance_records
            ) / len(performance_records),
            2
        )

        average_assignment = round(
            sum(
                r.assignment_percentage
                for r in performance_records
            ) / len(performance_records),
            2
        )

        average_overall = round(
            sum(
                r.overall_percentage
                for r in performance_records
            ) / len(performance_records),
            2
        )

    # -------------------------------------------------
    # FINAL RESPONSE
    # -------------------------------------------------

    return {
        "message": "Student intelligence data retrieved successfully",

        "student": {
            "student_id": student.student_id,
            "student_name": student.name,
            "semester": student.semester
        },

        "summary": {
            "average_attendance": average_attendance,
            "average_marks": average_marks,
            "average_assignment": average_assignment,
            "average_overall_performance": average_overall,
            "performance_records": len(performance_data),
            "risk_records": len(risk_data),
            "predictions": len(prediction_data),
            "recommendations": len(recommendation_data)
        },

        "performance": performance_data,

        "risk": risk_data,

        "prediction": prediction_data,

        "segmentation": segment_data,

        "recommendations": recommendation_data
    }




@router.get("/faculty")
def get_faculty_intelligence(
    db: Session = Depends(get_db),
    current_faculty=Depends(require_faculty)
):
    # -------------------------------------------------
    # FIND FACULTY
    # -------------------------------------------------

    faculty = db.query(Faculty).filter(
        Faculty.user_id == current_faculty.id
    ).first()

    if not faculty:
        raise HTTPException(
            status_code=404,
            detail="Faculty profile not found."
        )

    # -------------------------------------------------
    # GET ASSIGNED SUBJECTS
    # -------------------------------------------------

    faculty_subjects = db.query(FacultySubject).filter(
        FacultySubject.faculty_id == faculty.id
    ).all()

    subject_ids = [
        item.subject_id
        for item in faculty_subjects
    ]

    if not subject_ids:
        return {
            "message": "No subjects assigned to this faculty.",
            "faculty": {
                "faculty_id": faculty.faculty_id,
                "faculty_name": faculty.name
            },
            "overview": {
                "total_students": 0,
                "high_risk_students": 0,
                "medium_risk_students": 0,
                "low_risk_students": 0
            },
            "students": []
        }

    # -------------------------------------------------
    # GET PERFORMANCE FOR ASSIGNED SUBJECTS
    # -------------------------------------------------

    performance_records = db.query(Performance).filter(
        Performance.subject_id.in_(subject_ids)
    ).all()

    # -------------------------------------------------
    # GET RISK FOR ASSIGNED SUBJECTS
    # -------------------------------------------------

    risk_records = db.query(StudentRisk).filter(
        StudentRisk.subject_id.in_(subject_ids)
    ).all()

    # -------------------------------------------------
    # GET PREDICTIONS
    # -------------------------------------------------

    prediction_records = db.query(Prediction).filter(
        Prediction.subject_id.in_(subject_ids)
    ).order_by(
        Prediction.created_at.desc()
    ).all()

    # -------------------------------------------------
    # GET RECOMMENDATIONS
    # -------------------------------------------------

    recommendation_records = db.query(
        Recommendation
    ).filter(
        Recommendation.subject_id.in_(subject_ids)
    ).all()

    # -------------------------------------------------
    # BUILD STUDENT DATA
    # -------------------------------------------------

    students = {}

    # Performance
    for record in performance_records:

        if record.student_id not in students:
            students[record.student_id] = {
                "student_id": record.student_id,
                "student_name": record.student.name,
                "performance_records": [],
                "risk_records": [],
                "predictions": [],
                "recommendations": []
            }

        students[record.student_id][
            "performance_records"
        ].append({
            "subject_id": record.subject.id,
            "subject_name": record.subject.name,
            "subject_code": record.subject.code,
            "overall_percentage": record.overall_percentage,
            "performance_level": record.performance_level
        })

    # Risk
    for record in risk_records:

        if record.student_id not in students:
            students[record.student_id] = {
                "student_id": record.student_id,
                "student_name": record.student.name,
                "performance_records": [],
                "risk_records": [],
                "predictions": [],
                "recommendations": []
            }

        students[record.student_id][
            "risk_records"
        ].append({
            "subject_id": record.subject.id,
            "subject_name": record.subject.name,
            "risk_score": record.risk_score,
            "risk_level": record.risk_level,
            "risk_reason": record.risk_reason
        })

    # Predictions
    for record in prediction_records:

        if record.student_id not in students:
            students[record.student_id] = {
                "student_id": record.student_id,
                "student_name": record.student.name,
                "performance_records": [],
                "risk_records": [],
                "predictions": [],
                "recommendations": []
            }

        students[record.student_id][
            "predictions"
        ].append({
            "prediction_id": record.id,
            "subject_id": record.subject.id,
            "subject_name": record.subject.name,
            "prediction_type": record.prediction_type,
            "predicted_performance":
                record.predicted_performance,
            "predicted_level":
                record.predicted_level
        })

    # Recommendations
    for record in recommendation_records:

        if record.student_id not in students:
            students[record.student_id] = {
                "student_id": record.student_id,
                "student_name": record.student.name,
                "performance_records": [],
                "risk_records": [],
                "predictions": [],
                "recommendations": []
            }

        students[record.student_id][
            "recommendations"
        ].append({
            "recommendation_id": record.id,
            "subject_id": record.subject.id,
            "subject_name": record.subject.name,
            "recommendation":
                record.recommendation_text,
            "recommendation_type":
                record.recommendation_type,
            "priority": record.priority
        })

    # -------------------------------------------------
    # CALCULATE STUDENT SUMMARY
    # -------------------------------------------------

    student_results = []

    high_risk = 0
    medium_risk = 0
    low_risk = 0

    for student_data in students.values():

        performance_records_for_student = (
            student_data["performance_records"]
        )

        risk_records_for_student = (
            student_data["risk_records"]
        )

        predictions_for_student = (
            student_data["predictions"]
        )

        # Average performance
        if performance_records_for_student:

            average_performance = round(
                sum(
                    item["overall_percentage"]
                    for item in performance_records_for_student
                )
                /
                len(performance_records_for_student),
                2
            )

        else:
            average_performance = None

        # Determine highest risk
        risk_level = "Low"

        if any(
            item["risk_level"] == "High"
            for item in risk_records_for_student
        ):
            risk_level = "High"

        elif any(
            item["risk_level"] == "Medium"
            for item in risk_records_for_student
        ):
            risk_level = "Medium"

        if risk_level == "High":
            high_risk += 1

        elif risk_level == "Medium":
            medium_risk += 1

        else:
            low_risk += 1

        # Latest future prediction
        future_prediction = None

        for prediction in predictions_for_student:

            if (
                prediction["prediction_type"]
                == "Future Final Exam Performance"
            ):
                future_prediction = prediction
                break

        student_results.append({
            "student_id": student_data["student_id"],
            "student_name": student_data["student_name"],

            "average_performance":
                average_performance,

            "risk_level":
                risk_level,

            "future_prediction":
                future_prediction,

            "performance":
                performance_records_for_student,

            "risk":
                risk_records_for_student,

            "predictions":
                predictions_for_student,

            "recommendations":
                student_data["recommendations"]
        })

    # -------------------------------------------------
    # FINAL RESPONSE
    # -------------------------------------------------

    return {
        "message": "Faculty student intelligence retrieved successfully",

        "faculty": {
            "faculty_id": faculty.faculty_id,
            "faculty_name": faculty.name
        },

        "assigned_subjects": [
            {
                "subject_id": subject.id,
                "subject_name": subject.name,
                "subject_code": subject.code
            }
            for subject in [
                item.subject
                for item in faculty_subjects
            ]
        ],

        "overview": {
            "total_students": len(student_results),
            "high_risk_students": high_risk,
            "medium_risk_students": medium_risk,
            "low_risk_students": low_risk
        },

        "students": student_results
    }


@router.get("/admin")
def get_admin_intelligence(
    db: Session = Depends(get_db),
    current_admin=Depends(require_admin)
):
    # -------------------------------------------------
    # GET DATA
    # -------------------------------------------------

    performance_records = db.query(Performance).all()

    risk_records = db.query(StudentRisk).all()

    prediction_records = db.query(
        Prediction
    ).order_by(
        Prediction.created_at.desc()
    ).all()

    recommendation_records = db.query(
        Recommendation
    ).all()

    # -------------------------------------------------
    # UNIQUE STUDENTS
    # -------------------------------------------------

    student_ids = set()

    for record in performance_records:
        student_ids.add(record.student_id)

    for record in risk_records:
        student_ids.add(record.student_id)

    for record in prediction_records:
        student_ids.add(record.student_id)

    for record in recommendation_records:
        student_ids.add(record.student_id)

    # -------------------------------------------------
    # ACADEMIC OVERVIEW
    # -------------------------------------------------

    if performance_records:

        average_attendance = round(
            sum(
                record.attendance_percentage
                for record in performance_records
            )
            / len(performance_records),
            2
        )

        average_marks = round(
            sum(
                record.marks_percentage
                for record in performance_records
            )
            / len(performance_records),
            2
        )

        average_assignment = round(
            sum(
                record.assignment_percentage
                for record in performance_records
            )
            / len(performance_records),
            2
        )

        average_overall = round(
            sum(
                record.overall_percentage
                for record in performance_records
            )
            / len(performance_records),
            2
        )

    else:
        average_attendance = 0
        average_marks = 0
        average_assignment = 0
        average_overall = 0

    # -------------------------------------------------
    # PERFORMANCE DISTRIBUTION
    # -------------------------------------------------

    performance_distribution = {
        "excellent": 0,
        "good": 0,
        "average": 0,
        "poor": 0
    }

    for record in performance_records:

        level = record.performance_level.lower()

        if level == "excellent":
            performance_distribution["excellent"] += 1

        elif level == "good":
            performance_distribution["good"] += 1

        elif level == "average":
            performance_distribution["average"] += 1

        elif level == "poor":
            performance_distribution["poor"] += 1

    # -------------------------------------------------
    # BUILD STUDENT-WISE INTELLIGENCE
    # -------------------------------------------------

    students = {}

    for student_id in student_ids:

        student = db.query(Student).filter(
            Student.student_id == student_id
        ).first()

        if not student:
            continue

        student_performance = [
            record
            for record in performance_records
            if record.student_id == student_id
        ]

        student_risk = [
            record
            for record in risk_records
            if record.student_id == student_id
        ]

        student_predictions = [
            record
            for record in prediction_records
            if record.student_id == student_id
        ]

        student_recommendations = [
            record
            for record in recommendation_records
            if record.student_id == student_id
        ]

        # -------------------------------------------------
        # AVERAGE PERFORMANCE
        # -------------------------------------------------

        if student_performance:

            average_performance = round(
                sum(
                    record.overall_percentage
                    for record in student_performance
                )
                / len(student_performance),
                2
            )

        else:
            average_performance = None

        # -------------------------------------------------
        # STUDENT RISK
        # -------------------------------------------------

        risk_level = "Low"

        risk_scores = []

        risk_reasons = []

        for risk in student_risk:

            risk_scores.append(risk.risk_score)

            if risk.risk_reason:
                risk_reasons.append(
                    risk.risk_reason
                )

        if any(
            risk.risk_level == "High"
            for risk in student_risk
        ):
            risk_level = "High"

        elif any(
            risk.risk_level == "Medium"
            for risk in student_risk
        ):
            risk_level = "Medium"

        elif any(
            risk.risk_level == "Low"
            for risk in student_risk
        ):
            risk_level = "Low"

        # -------------------------------------------------
        # FUTURE PREDICTION
        # -------------------------------------------------

        future_prediction = None

        for prediction in student_predictions:

            if (
                prediction.prediction_type
                == "Future Final Exam Performance"
            ):

                future_prediction = {
                    "prediction_id": prediction.id,
                    "subject_id": prediction.subject_id,
                    "predicted_performance":
                        prediction.predicted_performance,
                    "predicted_level":
                        prediction.predicted_level
                }

                break

        # -------------------------------------------------
        # EARLY WARNING
        # -------------------------------------------------

        warning_reasons = []

        if risk_level == "High":
            warning_reasons.append(
                "Student has high risk indicators."
            )

        elif risk_level == "Medium":
            warning_reasons.append(
                "Student has medium risk indicators."
            )

        if (
            average_performance is not None
            and average_performance < 50
        ):
            warning_reasons.append(
                "Average academic performance is below 50%."
            )

        if student_recommendations:

            high_priority_count = len([
                recommendation
                for recommendation
                in student_recommendations
                if recommendation.priority == "High"
            ])

            if high_priority_count > 0:
                warning_reasons.append(
                    "Student has high-priority recommendations."
                )

            if len(student_recommendations) >= 2:
                warning_reasons.append(
                    "Student has multiple improvement recommendations."
                )

        early_warning = len(warning_reasons) > 0

        # -------------------------------------------------
        # SAVE STUDENT RESULT
        # -------------------------------------------------

        students[student_id] = {
            "student_id": student.student_id,
            "student_name": student.name,

            "average_performance":
                average_performance,

            "risk": {
                "risk_level": risk_level,
                "risk_records":
                    len(student_risk),
                "average_risk_score":
                    round(
                        sum(risk_scores)
                        / len(risk_scores),
                        2
                    )
                    if risk_scores
                    else None,
                "reasons":
                    list(set(risk_reasons))
            },

            "future_prediction":
                future_prediction,

            "recommendation_count":
                len(student_recommendations),

            "early_warning": {
                "required":
                    early_warning,
                "reasons":
                    warning_reasons
            }
        }

    # -------------------------------------------------
    # UNIQUE STUDENT RISK OVERVIEW
    # -------------------------------------------------

    high_risk_students = 0
    medium_risk_students = 0
    low_risk_students = 0

    for student in students.values():

        level = student["risk"]["risk_level"]

        if level == "High":
            high_risk_students += 1

        elif level == "Medium":
            medium_risk_students += 1

        else:
            low_risk_students += 1

    # -------------------------------------------------
    # EARLY WARNING STUDENTS
    # -------------------------------------------------

    early_warning_students = []

    for student in students.values():

        if student["early_warning"]["required"]:

            early_warning_students.append({
                "student_id":
                    student["student_id"],

                "student_name":
                    student["student_name"],

                "average_performance":
                    student["average_performance"],

                "risk_level":
                    student["risk"]["risk_level"],

                "recommendation_count":
                    student["recommendation_count"],

                "reasons":
                    student["early_warning"]["reasons"]
            })

    # -------------------------------------------------
    # FINAL RESPONSE
    # -------------------------------------------------

    return {
        "message":
            "Admin student intelligence retrieved successfully",

        "overview": {
            "total_students":
                len(students),

            "students_with_performance":
                len({
                    record.student_id
                    for record in performance_records
                }),

            "students_with_risk":
                len({
                    record.student_id
                    for record in risk_records
                }),

            "students_with_predictions":
                len({
                    record.student_id
                    for record in prediction_records
                }),

            "students_with_recommendations":
                len({
                    record.student_id
                    for record in recommendation_records
                })
        },

        "academic_overview": {
            "average_attendance":
                average_attendance,

            "average_marks":
                average_marks,

            "average_assignment":
                average_assignment,

            "average_overall_performance":
                average_overall
        },

        "performance_distribution":
            performance_distribution,

        "risk_overview": {
            "high_risk_students":
                high_risk_students,

            "medium_risk_students":
                medium_risk_students,

            "low_risk_students":
                low_risk_students
        },

        "prediction_overview": {
            "total_predictions":
                len(prediction_records),

            "future_predictions":
                len([
                    record
                    for record in prediction_records
                    if record.prediction_type
                    == "Future Final Exam Performance"
                ])
        },

        "recommendation_overview": {
            "total_recommendations":
                len(recommendation_records)
        },

        "early_warning": {
            "total_students":
                len(early_warning_students),

            "students":
                early_warning_students
        },

        "students":
            list(students.values())
    }



@router.get("/admin/segmentation")
def get_admin_student_segmentation(
    db: Session = Depends(get_db),
    current_admin=Depends(require_admin)
):
    # -------------------------------------------------
    # GET ALL PERFORMANCE RECORDS
    # -------------------------------------------------

    performance_records = db.query(Performance).all()

    if not performance_records:
        return {
            "message": "No performance data available for segmentation.",
            "total_students": 0,
            "students": []
        }

    # -------------------------------------------------
    # AGGREGATE DATA STUDENT-WISE
    # -------------------------------------------------

    student_data = {}

    for record in performance_records:

        if record.student_id not in student_data:
            student_data[record.student_id] = {
                "attendance": [],
                "marks": [],
                "assignment": [],
                "overall": []
            }

        student_data[record.student_id]["attendance"].append(
            record.attendance_percentage
        )

        student_data[record.student_id]["marks"].append(
            record.marks_percentage
        )

        student_data[record.student_id]["assignment"].append(
            record.assignment_percentage
        )

        student_data[record.student_id]["overall"].append(
            record.overall_percentage
        )

    # -------------------------------------------------
    # CREATE ML FEATURES
    # -------------------------------------------------

    student_ids = []
    features = []

    for student_id, data in student_data.items():

        student_ids.append(student_id)

        features.append([
            sum(data["attendance"]) / len(data["attendance"]),
            sum(data["marks"]) / len(data["marks"]),
            sum(data["assignment"]) / len(data["assignment"]),
            sum(data["overall"]) / len(data["overall"])
        ])

    # -------------------------------------------------
    # K-MEANS NEEDS AT LEAST 3 STUDENTS
    # -------------------------------------------------

    if len(features) < 3:
        return {
            "message": (
                "At least 3 students with performance "
                "data are required for K-Means segmentation."
            ),
            "total_students": len(features),
            "students": []
        }

    # -------------------------------------------------
    # APPLY K-MEANS
    # -------------------------------------------------

    kmeans = KMeans(
        n_clusters=3,
        n_init=10,
        random_state=42
    )

    cluster_labels = kmeans.fit_predict(features)

    # -------------------------------------------------
    # CALCULATE CLUSTER AVERAGES
    # -------------------------------------------------

    cluster_scores = {}

    for cluster_number in range(3):

        cluster_students = [
            features[index]
            for index in range(len(features))
            if cluster_labels[index] == cluster_number
        ]

        if cluster_students:

            cluster_average = sum(
                (
                    row[0]
                    + row[1]
                    + row[2]
                    + row[3]
                ) / 4
                for row in cluster_students
            ) / len(cluster_students)

        else:
            cluster_average = 0

        cluster_scores[cluster_number] = cluster_average

    # -------------------------------------------------
    # SORT CLUSTERS BY PERFORMANCE
    # -------------------------------------------------

    sorted_clusters = sorted(
        cluster_scores,
        key=cluster_scores.get,
        reverse=True
    )

    cluster_names = {
        sorted_clusters[0]: "High Performance",
        sorted_clusters[1]: "Medium Performance",
        sorted_clusters[2]: "Low Performance"
    }

    # -------------------------------------------------
    # BUILD FINAL RESPONSE
    # -------------------------------------------------

    results = []

    for index, student_id in enumerate(student_ids):

        student = db.query(Student).filter(
            Student.student_id == student_id
        ).first()

        if not student:
            continue

        cluster = int(cluster_labels[index])
        data = features[index]

        results.append({
            "student_id": student.student_id,
            "student_name": student.name,

            "segment": cluster_names[cluster],

            "cluster": cluster,

            "average_attendance": round(
                data[0], 2
            ),

            "average_marks": round(
                data[1], 2
            ),

            "average_assignment": round(
                data[2], 2
            ),

            "average_overall_performance": round(
                data[3], 2
            )
        })

    # -------------------------------------------------
    # SEGMENT SUMMARY
    # -------------------------------------------------

    segment_summary = {
        "high_performance": 0,
        "medium_performance": 0,
        "low_performance": 0
    }

    for student in results:

        if student["segment"] == "High Performance":
            segment_summary["high_performance"] += 1

        elif student["segment"] == "Medium Performance":
            segment_summary["medium_performance"] += 1

        elif student["segment"] == "Low Performance":
            segment_summary["low_performance"] += 1

    # -------------------------------------------------
    # FINAL RESPONSE
    # -------------------------------------------------

    return {
        "message": "Student segmentation completed successfully",

        "model": {
            "algorithm": "K-Means Clustering",
            "clusters": 3,
            "features": [
                "attendance_percentage",
                "marks_percentage",
                "assignment_percentage",
                "overall_percentage"
            ]
        },

        "total_students": len(results),

        "segment_summary": segment_summary,

        "students": results
    }