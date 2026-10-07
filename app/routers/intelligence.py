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


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/intelligence",
    tags=["Student Intelligence"]
)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_segment_name(
    cluster_centers,
    cluster
):
    """
    Convert KMeans cluster number into
    Low / Medium / High based on average
    cluster performance.
    """

    cluster_scores = {
        index: float(np.mean(center))
        for index, center
        in enumerate(cluster_centers)
    }

    sorted_clusters = sorted(
        cluster_scores,
        key=cluster_scores.get
    )

    cluster_names = {}

    if len(sorted_clusters) >= 1:
        cluster_names[
            sorted_clusters[0]
        ] = "Low"

    if len(sorted_clusters) >= 2:
        cluster_names[
            sorted_clusters[1]
        ] = "Medium"

    if len(sorted_clusters) >= 3:
        cluster_names[
            sorted_clusters[2]
        ] = "High"

    return cluster_names.get(
        cluster,
        "Unknown"
    )


# ============================================================
# STUDENT INTELLIGENCE
# ============================================================

@router.get("/my-intelligence")
def get_my_intelligence(

    db: Session = Depends(get_db),

    current_student=Depends(
        require_student
    )
):

    # --------------------------------------------------------
    # FIND CURRENT STUDENT
    # --------------------------------------------------------

    student = (
        db.query(Student)
        .filter(
            Student.user_id ==
            current_student.id
        )
        .first()
    )

    if not student:

        raise HTTPException(
            status_code=404,
            detail="Student profile not found."
        )


    student_id = student.student_id


    # --------------------------------------------------------
    # PERFORMANCE
    # --------------------------------------------------------

    performance_records = (
        db.query(Performance)
        .filter(
            Performance.student_id ==
            student_id
        )
        .all()
    )


    # --------------------------------------------------------
    # RISK
    # --------------------------------------------------------

    risk_records = (
        db.query(StudentRisk)
        .filter(
            StudentRisk.student_id ==
            student_id
        )
        .all()
    )


    # --------------------------------------------------------
    # FUTURE PREDICTIONS ONLY
    # --------------------------------------------------------

    prediction_records = (
        db.query(Prediction)
        .filter(
            Prediction.student_id ==
            student_id,

            Prediction.prediction_type ==
            "Future Final Exam Performance"
        )
        .order_by(
            Prediction.created_at.desc()
        )
        .all()
    )


    # --------------------------------------------------------
    # RECOMMENDATIONS
    # --------------------------------------------------------

    recommendation_records = (
        db.query(Recommendation)
        .filter(
            Recommendation.student_id ==
            student_id
        )
        .order_by(
            Recommendation.created_at.desc()
        )
        .all()
    )


    # ========================================================
    # STUDENT PERFORMANCE RESPONSE
    # ========================================================

    performance = []

    for record in performance_records:

        performance.append({

            "performance_id":
                record.id,

            "subject_id":
                record.subject.id
                if record.subject
                else record.subject_id,

            "subject_name":
                record.subject.name
                if record.subject
                else None,

            "subject_code":
                record.subject.code
                if record.subject
                else None,

            "attendance_percentage":
                record.attendance_percentage,

            "marks_percentage":
                record.marks_percentage,

            "assignment_percentage":
                record.assignment_percentage,

            "overall_percentage":
                record.overall_percentage,

            "academic_percentage":
                record.overall_percentage,

            "pass_status":
                record.pass_status,

            "performance_level":
                record.performance_level
        })


    # ========================================================
    # RISK RESPONSE
    # ========================================================

    risk = []

    for record in risk_records:

        risk.append({

            "risk_id":
                record.id,

            "subject_id":
                record.subject.id
                if record.subject
                else record.subject_id,

            "subject_name":
                record.subject.name
                if record.subject
                else None,

            "risk_score":
                record.risk_score,

            "risk_level":
                record.risk_level,

            "risk_reason":
                record.risk_reason
        })


    # ========================================================
    # PREDICTION RESPONSE
    # ========================================================

    predictions = []

    for record in prediction_records:

        predictions.append({

            "prediction_id":
                record.id,

            "subject_id":
                record.subject.id
                if record.subject
                else record.subject_id,

            "subject_name":
                record.subject.name
                if record.subject
                else None,

            "predicted_performance":
                record.predicted_performance,

            "predicted_level":
                record.predicted_level,

            "model_name":
                record.model_name,

            "prediction_type":
                record.prediction_type,

            "created_at":
                record.created_at
        })


    # ========================================================
    # RECOMMENDATION RESPONSE
    # ========================================================

    recommendations = []

    for record in recommendation_records:

        recommendations.append({

            "recommendation_id":
                record.id,

            "subject_id":
                record.subject.id
                if record.subject
                else record.subject_id,

            "subject_name":
                record.subject.name
                if record.subject
                else None,

            "recommendation":
                record.recommendation_text,

            "recommendation_type":
                record.recommendation_type,

            "priority":
                record.priority,

            "created_at":
                record.created_at
        })


    # ========================================================
    # STUDENT LEVEL K-MEANS SEGMENTATION
    # ========================================================

    all_performance = (
        db.query(Performance)
        .all()
    )


    student_data = {}


    for record in all_performance:

        sid = record.student_id

        if sid not in student_data:

            student_data[sid] = {

                "attendance": [],

                "marks": [],

                "assignment": []
            }


        student_data[sid][
            "attendance"
        ].append(
            record.attendance_percentage
        )

        student_data[sid][
            "marks"
        ].append(
            record.marks_percentage
        )

        student_data[sid][
            "assignment"
        ].append(
            record.assignment_percentage
        )


    segmentation = {

        "available": False,

        "message":
            "Not enough students for segmentation."
    }


    if len(student_data) >= 3:

        feature_rows = []

        student_ids = []


        for sid, values in student_data.items():

            avg_attendance = np.mean(
                values["attendance"]
            )

            avg_marks = np.mean(
                values["marks"]
            )

            avg_assignment = np.mean(
                values["assignment"]
            )

            feature_rows.append([

                avg_attendance,

                avg_marks,

                avg_assignment
            ])

            student_ids.append(sid)


        X = np.array(
            feature_rows
        )


        kmeans = KMeans(

            n_clusters=3,

            random_state=42,

            n_init=10
        )


        labels = kmeans.fit_predict(X)


        current_index = None

        for index, sid in enumerate(
            student_ids
        ):

            if sid == student_id:

                current_index = index

                break


        if current_index is not None:

            current_cluster = int(
                labels[current_index]
            )

            cluster_names = {}

            cluster_scores = {}

            for index, center in enumerate(
                kmeans.cluster_centers_
            ):

                cluster_scores[index] = (
                    float(
                        np.mean(center)
                    )
                )


            sorted_clusters = sorted(

                cluster_scores,

                key=cluster_scores.get
            )


            if len(sorted_clusters) >= 1:

                cluster_names[
                    sorted_clusters[0]
                ] = "Low"


            if len(sorted_clusters) >= 2:

                cluster_names[
                    sorted_clusters[1]
                ] = "Medium"


            if len(sorted_clusters) >= 3:

                cluster_names[
                    sorted_clusters[2]
                ] = "High"


            current_features = (
                X[current_index]
            )


            segmentation = {

                "available": True,

                "method":
                    "K-Means Clustering",

                "clusters":
                    3,

                "current_cluster":
                    current_cluster,

                "current_segment":
                    cluster_names.get(
                        current_cluster,
                        "Unknown"
                    ),

                "average_attendance":
                    round(
                        float(
                            current_features[0]
                        ),
                        2
                    ),

                "average_marks":
                    round(
                        float(
                            current_features[1]
                        ),
                        2
                    ),

                "average_assignment":
                    round(
                        float(
                            current_features[2]
                        ),
                        2
                    )
            }


    # ========================================================
    # STUDENT SUMMARY
    # ========================================================

    if performance_records:

        average_attendance = round(

            float(
                np.mean([
                    record.attendance_percentage
                    for record
                    in performance_records
                ])
            ),

            2
        )


        average_marks = round(

            float(
                np.mean([
                    record.marks_percentage
                    for record
                    in performance_records
                ])
            ),

            2
        )


        average_assignment = round(

            float(
                np.mean([
                    record.assignment_percentage
                    for record
                    in performance_records
                ])
            ),

            2
        )


        average_overall = round(

            float(
                np.mean([
                    record.overall_percentage
                    for record
                    in performance_records
                ])
            ),

            2
        )

    else:

        average_attendance = 0

        average_marks = 0

        average_assignment = 0

        average_overall = 0


    # ========================================================
    # RETURN STUDENT INTELLIGENCE
    # ========================================================

    return {

        "student": {

            "student_id":
                student.student_id,

            "name":
                student.name,

            "course_id":
                student.course_id,

            "department_id":
                student.department_id,

            "semester":
                student.semester
        },

        "summary": {

            "total_subjects":
                len(performance_records),

            "average_attendance":
                average_attendance,

            "average_marks":
                average_marks,

            "average_assignment":
                average_assignment,

            "average_overall_performance":
                average_overall,

            "total_risk_records":
                len(risk_records),

            "total_predictions":
                len(prediction_records),

            "total_recommendations":
                len(recommendation_records)
        },

        "performance":
            performance,

        "risk":
            risk,

        "predictions":
            predictions,

        "segmentation":
            segmentation,

        "recommendations":
            recommendations
    }


# ============================================================
# FACULTY INTELLIGENCE
# ============================================================

@router.get("/faculty")
def get_faculty_intelligence(

    db: Session = Depends(get_db),

    current_faculty=Depends(
        require_faculty
    )
):

    # --------------------------------------------------------
    # FACULTY PROFILE
    # --------------------------------------------------------

    faculty = (
        db.query(Faculty)
        .filter(
            Faculty.user_id ==
            current_faculty.id
        )
        .first()
    )

    if not faculty:

        raise HTTPException(
            status_code=404,
            detail="Faculty profile not found."
        )


    # --------------------------------------------------------
    # ASSIGNED SUBJECTS
    # --------------------------------------------------------

    assigned_subject_records = (
        db.query(FacultySubject)
        .filter(
            FacultySubject.faculty_id ==
            faculty.id
        )
        .all()
    )


    assigned_subject_ids = [

        record.subject_id

        for record
        in assigned_subject_records
    ]


    # --------------------------------------------------------
    # NO SUBJECTS
    # --------------------------------------------------------

    if not assigned_subject_ids:

        return {

            "faculty": {

                "user_id":
                    current_faculty.id,

                "name":
                    current_faculty.name
            },

            "assigned_subjects": [],

            "overview": {

                "total_students":
                    0,

                "total_performance_records":
                    0,

                "total_risk_records":
                    0,

                "total_predictions":
                    0,

                "total_recommendations":
                    0
            },

            "students": []
        }


    # --------------------------------------------------------
    # PERFORMANCE
    # --------------------------------------------------------

    performance_records = (
        db.query(Performance)
        .filter(
            Performance.subject_id.in_(
                assigned_subject_ids
            )
        )
        .all()
    )


    # --------------------------------------------------------
    # RISK
    # --------------------------------------------------------

    risk_records = (
        db.query(StudentRisk)
        .filter(
            StudentRisk.subject_id.in_(
                assigned_subject_ids
            )
        )
        .all()
    )


    # --------------------------------------------------------
    # FUTURE PREDICTIONS
    # --------------------------------------------------------

    prediction_records = (
        db.query(Prediction)
        .filter(

            Prediction.subject_id.in_(
                assigned_subject_ids
            ),

            Prediction.prediction_type ==
            "Future Final Exam Performance"

        )
        .order_by(
            Prediction.created_at.desc()
        )
        .all()
    )


    # --------------------------------------------------------
    # RECOMMENDATIONS
    # --------------------------------------------------------

    recommendation_records = (
        db.query(Recommendation)
        .filter(
            Recommendation.subject_id.in_(
                assigned_subject_ids
            )
        )
        .order_by(
            Recommendation.created_at.desc()
        )
        .all()
    )


    # ========================================================
    # STUDENT-WISE DATA
    # ========================================================

    students = {}


    # --------------------------------------------------------
    # PERFORMANCE
    # --------------------------------------------------------

    for record in performance_records:

        sid = record.student_id

        if sid not in students:

            students[sid] = {

                "student_id":
                    sid,

                "student_name":
                    record.student.name
                    if record.student
                    else None,

                "performance": [],

                "risk": [],

                "predictions": [],

                "recommendations": []
            }


        students[sid][
            "performance"
        ].append({

            "performance_id":
                record.id,

            "subject_id":
                record.subject_id,

            "subject_name":
                record.subject.name
                if record.subject
                else None,

            "attendance_percentage":
                record.attendance_percentage,

            "marks_percentage":
                record.marks_percentage,

            "assignment_percentage":
                record.assignment_percentage,

            "overall_percentage":
                record.overall_percentage,

            "performance_level":
                record.performance_level,

            "pass_status":
                record.pass_status
        })


    # --------------------------------------------------------
    # RISK
    # --------------------------------------------------------

    for record in risk_records:

        sid = record.student_id

        if sid not in students:

            students[sid] = {

                "student_id":
                    sid,

                "student_name":
                    record.student.name
                    if record.student
                    else None,

                "performance": [],

                "risk": [],

                "predictions": [],

                "recommendations": []
            }


        students[sid][
            "risk"
        ].append({

            "risk_id":
                record.id,

            "subject_id":
                record.subject_id,

            "subject_name":
                record.subject.name
                if record.subject
                else None,

            "risk_score":
                record.risk_score,

            "risk_level":
                record.risk_level,

            "risk_reason":
                record.risk_reason
        })


    # --------------------------------------------------------
    # PREDICTIONS
    # --------------------------------------------------------

    for record in prediction_records:

        sid = record.student_id

        if sid not in students:

            students[sid] = {

                "student_id":
                    sid,

                "student_name":
                    record.student.name
                    if record.student
                    else None,

                "performance": [],

                "risk": [],

                "predictions": [],

                "recommendations": []
            }


        students[sid][
            "predictions"
        ].append({

            "prediction_id":
                record.id,

            "subject_id":
                record.subject_id,

            "subject_name":
                record.subject.name
                if record.subject
                else None,

            "predicted_performance":
                record.predicted_performance,

            "predicted_level":
                record.predicted_level,

            "model_name":
                record.model_name,

            "prediction_type":
                record.prediction_type,

            "created_at":
                record.created_at
        })


    # --------------------------------------------------------
    # RECOMMENDATIONS
    # --------------------------------------------------------

    for record in recommendation_records:

        sid = record.student_id

        if sid not in students:

            students[sid] = {

                "student_id":
                    sid,

                "student_name":
                    record.student.name
                    if record.student
                    else None,

                "performance": [],

                "risk": [],

                "predictions": [],

                "recommendations": []
            }


        students[sid][
            "recommendations"
        ].append({

            "recommendation_id":
                record.id,

            "subject_id":
                record.subject_id,

            "subject_name":
                record.subject.name
                if record.subject
                else None,

            "recommendation":
                record.recommendation_text,

            "recommendation_type":
                record.recommendation_type,

            "priority":
                record.priority,

            "created_at":
                record.created_at
        })


    # ========================================================
    # RISK PRIORITY
    # ========================================================

    risk_priority = {

        "High": 3,

        "Medium": 2,

        "Low": 1
    }


    for student_data in students.values():

        risk_levels = [

            item["risk_level"]

            for item
            in student_data["risk"]

            if item.get("risk_level")
        ]


        if risk_levels:

            highest_risk = max(

                risk_levels,

                key=lambda level:
                    risk_priority.get(
                        level,
                        0
                    )
            )

        else:

            highest_risk = "Low"


        student_data[
            "overall_risk_level"
        ] = highest_risk


    # ========================================================
    # OVERVIEW
    # ========================================================

    high_risk_students = sum(

        1

        for student_data
        in students.values()

        if student_data.get(
            "overall_risk_level"
        ) == "High"
    )


    medium_risk_students = sum(

        1

        for student_data
        in students.values()

        if student_data.get(
            "overall_risk_level"
        ) == "Medium"
    )


    low_risk_students = sum(

        1

        for student_data
        in students.values()

        if student_data.get(
            "overall_risk_level"
        ) == "Low"
    )


    return {

        "faculty": {

            "user_id":
                current_faculty.id,

            "name":
                current_faculty.name,

            "faculty_id":
                faculty.faculty_id
        },

        "assigned_subjects":
            assigned_subject_ids,

        "overview": {

            "total_students":
                len(students),

            "total_performance_records":
                len(performance_records),

            "total_risk_records":
                len(risk_records),

            "total_predictions":
                len(prediction_records),

            "total_recommendations":
                len(recommendation_records),

            "risk_distribution": {

                "High":
                    high_risk_students,

                "Medium":
                    medium_risk_students,

                "Low":
                    low_risk_students
            }
        },

        "students":
            list(students.values())
    }


# ============================================================
# ADMIN INTELLIGENCE
# ============================================================

@router.get("/admin")
def get_admin_intelligence(

    db: Session = Depends(get_db),

    current_admin=Depends(
        require_admin
    )
):

    # ========================================================
    # LOAD DATA
    # ========================================================

    performance_records = (
        db.query(Performance)
        .all()
    )


    risk_records = (
        db.query(StudentRisk)
        .all()
    )


    prediction_records = (
        db.query(Prediction)
        .filter(
            Prediction.prediction_type ==
            "Future Final Exam Performance"
        )
        .all()
    )


    recommendation_records = (
        db.query(Recommendation)
        .all()
    )


    # ========================================================
    # GET UNIQUE STUDENT IDS
    # ========================================================

    student_ids = set()


    for record in performance_records:

        student_ids.add(
            record.student_id
        )


    for record in risk_records:

        student_ids.add(
            record.student_id
        )


    for record in prediction_records:

        student_ids.add(
            record.student_id
        )


    for record in recommendation_records:

        student_ids.add(
            record.student_id
        )


    student_ids = list(
        student_ids
    )


    # ========================================================
    # FIX N+1 QUERY
    #
    # BEFORE:
    # One Student query for every student
    #
    # NOW:
    # One query for all students
    # ========================================================

    students_records = []

    if student_ids:

        students_records = (
            db.query(Student)
            .filter(
                Student.student_id.in_(
                    student_ids
                )
            )
            .all()
        )


    students_by_id = {

        student.student_id:
            student

        for student
        in students_records
    }


    # ========================================================
    # PERFORMANCE DISTRIBUTION
    # ========================================================

    performance_distribution = {

        "Excellent": 0,

        "Good": 0,

        "Average": 0,

        "Poor": 0
    }


    for record in performance_records:

        level = (
            record.performance_level
            or "Unknown"
        )


        if level in performance_distribution:

            performance_distribution[
                level
            ] += 1


    # ========================================================
    # RISK DISTRIBUTION
    # ========================================================

    risk_distribution = {

        "High": 0,

        "Medium": 0,

        "Low": 0
    }


    for record in risk_records:

        level = (
            record.risk_level
            or "Low"
        )


        if level in risk_distribution:

            risk_distribution[
                level
            ] += 1


    # ========================================================
    # STUDENT-WISE INTELLIGENCE
    # ========================================================

    student_intelligence = []


    for student_id in student_ids:

        # ----------------------------------------------------
        # N+1 FIX
        # ----------------------------------------------------

        student = students_by_id.get(
            student_id
        )


        if not student:

            continue


        student_performance = [

            record

            for record
            in performance_records

            if record.student_id ==
            student_id
        ]


        student_risk = [

            record

            for record
            in risk_records

            if record.student_id ==
            student_id
        ]


        student_predictions = [

            record

            for record
            in prediction_records

            if record.student_id ==
            student_id
        ]


        student_recommendations = [

            record

            for record
            in recommendation_records

            if record.student_id ==
            student_id
        ]


        # ----------------------------------------------------
        # AVERAGES
        # ----------------------------------------------------

        if student_performance:

            average_attendance = round(

                float(
                    np.mean([
                        record.attendance_percentage

                        for record
                        in student_performance
                    ])
                ),

                2
            )


            average_marks = round(

                float(
                    np.mean([
                        record.marks_percentage

                        for record
                        in student_performance
                    ])
                ),

                2
            )


            average_assignment = round(

                float(
                    np.mean([
                        record.assignment_percentage

                        for record
                        in student_performance
                    ])
                ),

                2
            )


            average_overall = round(

                float(
                    np.mean([
                        record.overall_percentage

                        for record
                        in student_performance
                    ])
                ),

                2
            )

        else:

            average_attendance = 0

            average_marks = 0

            average_assignment = 0

            average_overall = 0


        # ----------------------------------------------------
        # HIGHEST RISK
        # ----------------------------------------------------

        risk_priority = {

            "High": 3,

            "Medium": 2,

            "Low": 1
        }


        if student_risk:

            highest_risk_record = max(

                student_risk,

                key=lambda record:
                    risk_priority.get(
                        record.risk_level,
                        0
                    )
            )


            overall_risk = (
                highest_risk_record.risk_level
            )

            highest_risk_score = (
                highest_risk_record.risk_score
            )

        else:

            overall_risk = "Low"

            highest_risk_score = 0


        # ----------------------------------------------------
        # EARLY WARNING
        # ----------------------------------------------------

        early_warning = (

            overall_risk == "High"

            or average_attendance < 75

            or average_overall < 40
        )


        student_intelligence.append({

            "student_id":
                student.student_id,

            "student_name":
                student.name,

            "course_id":
                student.course_id,

            "department_id":
                student.department_id,

            "semester":
                student.semester,

            "average_attendance":
                average_attendance,

            "average_marks":
                average_marks,

            "average_assignment":
                average_assignment,

            "average_overall_performance":
                average_overall,

            "risk_level":
                overall_risk,

            "risk_score":
                highest_risk_score,

            "future_prediction_count":
                len(student_predictions),

            "recommendation_count":
                len(student_recommendations),

            "early_warning":
                early_warning
        })


    # ========================================================
    # EARLY WARNING STUDENTS
    # ========================================================

    early_warning_students = [

        student

        for student
        in student_intelligence

        if student["early_warning"]
    ]


    # ========================================================
    # OVERALL AVERAGES
    # ========================================================

    if performance_records:

        overall_average_attendance = round(

            float(
                np.mean([
                    record.attendance_percentage

                    for record
                    in performance_records
                ])
            ),

            2
        )


        overall_average_marks = round(

            float(
                np.mean([
                    record.marks_percentage

                    for record
                    in performance_records
                ])
            ),

            2
        )


        overall_average_assignment = round(

            float(
                np.mean([
                    record.assignment_percentage

                    for record
                    in performance_records
                ])
            ),

            2
        )


        overall_average_performance = round(

            float(
                np.mean([
                    record.overall_percentage

                    for record
                    in performance_records
                ])
            ),

            2
        )

    else:

        overall_average_attendance = 0

        overall_average_marks = 0

        overall_average_assignment = 0

        overall_average_performance = 0


    # ========================================================
    # RETURN ADMIN INTELLIGENCE
    # ========================================================

    return {

        "overview": {

            "total_students":
                len(student_intelligence),

            "total_performance_records":
                len(performance_records),

            "total_risk_records":
                len(risk_records),

            "total_future_predictions":
                len(prediction_records),

            "total_recommendations":
                len(recommendation_records)
        },

        "academic_overview": {

            "average_attendance":
                overall_average_attendance,

            "average_marks":
                overall_average_marks,

            "average_assignment":
                overall_average_assignment,

            "average_overall_performance":
                overall_average_performance
        },

        "performance_distribution":
            performance_distribution,

        "risk_overview":
            risk_distribution,

        "prediction_count":
            len(prediction_records),

        "recommendation_count":
            len(recommendation_records),

        "early_warning": {

            "total":
                len(
                    early_warning_students
                ),

            "students":
                early_warning_students
        },

        "students":
            student_intelligence
    }


# ============================================================
# ADMIN STUDENT SEGMENTATION
# ============================================================

@router.get("/admin/segmentation")
def get_admin_student_segmentation(

    db: Session = Depends(get_db),

    current_admin=Depends(
        require_admin
    )
):

    # ========================================================
    # GET ALL PERFORMANCE
    # ========================================================

    performance_records = (
        db.query(Performance)
        .all()
    )


    # ========================================================
    # CHECK DATA
    # ========================================================

    if not performance_records:

        return {

            "available": False,

            "message":
                "No performance data available for segmentation.",

            "total_students":
                0,

            "segments": [],

            "students": []
        }


    # ========================================================
    # AGGREGATE PERFORMANCE BY STUDENT
    # ========================================================

    student_data = {}


    for record in performance_records:

        sid = record.student_id


        if sid not in student_data:

            student_data[sid] = {

                "attendance": [],

                "marks": [],

                "assignment": [],

                "overall": []
            }


        student_data[sid][
            "attendance"
        ].append(
            record.attendance_percentage
        )


        student_data[sid][
            "marks"
        ].append(
            record.marks_percentage
        )


        student_data[sid][
            "assignment"
        ].append(
            record.assignment_percentage
        )


        student_data[sid][
            "overall"
        ].append(
            record.overall_percentage
        )


    # ========================================================
    # MINIMUM STUDENTS
    # ========================================================

    if len(student_data) < 3:

        return {

            "available": False,

            "message":
                "At least 3 students are required for K-Means segmentation.",

            "total_students":
                len(student_data),

            "segments": [],

            "students": []
        }


    # ========================================================
    # BUILD FEATURE MATRIX
    # ========================================================

    student_ids = []

    feature_rows = []


    for sid, values in student_data.items():

        avg_attendance = float(
            np.mean(
                values["attendance"]
            )
        )


        avg_marks = float(
            np.mean(
                values["marks"]
            )
        )


        avg_assignment = float(
            np.mean(
                values["assignment"]
            )
        )


        avg_overall = float(
            np.mean(
                values["overall"]
            )
        )


        student_ids.append(
            sid
        )


        feature_rows.append([

            avg_attendance,

            avg_marks,

            avg_assignment,

            avg_overall
        ])


    X = np.array(
        feature_rows,
        dtype=float
    )


    # ========================================================
    # K-MEANS
    # ========================================================

    kmeans = KMeans(

        n_clusters=3,

        random_state=42,

        n_init=10
    )


    cluster_labels = (
        kmeans.fit_predict(X)
    )


    # ========================================================
    # CLUSTER NAMES
    # ========================================================

    cluster_scores = {}


    for cluster_index, center in enumerate(
        kmeans.cluster_centers_
    ):

        cluster_scores[
            cluster_index
        ] = float(
            np.mean(center)
        )


    sorted_clusters = sorted(

        cluster_scores,

        key=cluster_scores.get
    )


    cluster_names = {}


    if len(sorted_clusters) >= 1:

        cluster_names[
            sorted_clusters[0]
        ] = "Low"


    if len(sorted_clusters) >= 2:

        cluster_names[
            sorted_clusters[1]
        ] = "Medium"


    if len(sorted_clusters) >= 3:

        cluster_names[
            sorted_clusters[2]
        ] = "High"


    # ========================================================
    # FIX N+1 QUERY
    #
    # BEFORE:
    # Student query inside loop
    #
    # NOW:
    # ONE QUERY FOR ALL STUDENTS
    # ========================================================

    students_records = (
        db.query(Student)
        .filter(
            Student.student_id.in_(
                student_ids
            )
        )
        .all()
    )


    students_by_id = {

        student.student_id:
            student

        for student
        in students_records
    }


    # ========================================================
    # BUILD STUDENT RESULTS
    # ========================================================

    student_results = []


    for index, student_id in enumerate(
        student_ids
    ):

        # ----------------------------------------------------
        # N+1 FIX
        # ----------------------------------------------------

        student = students_by_id.get(
            student_id
        )


        if not student:

            continue


        cluster = int(
            cluster_labels[index]
        )


        features = X[index]


        student_results.append({

            "student_id":
                student.student_id,

            "student_name":
                student.name,

            "course_id":
                student.course_id,

            "department_id":
                student.department_id,

            "semester":
                student.semester,

            "cluster":
                cluster,

            "segment":
                cluster_names.get(
                    cluster,
                    "Unknown"
                ),

            "average_attendance":
                round(
                    float(features[0]),
                    2
                ),

            "average_marks":
                round(
                    float(features[1]),
                    2
                ),

            "average_assignment":
                round(
                    float(features[2]),
                    2
                ),

            "average_overall_performance":
                round(
                    float(features[3]),
                    2
                )
        })


    # ========================================================
    # SEGMENT SUMMARY
    # ========================================================

    segment_summary = {

        "High": 0,

        "Medium": 0,

        "Low": 0
    }


    for result in student_results:

        segment = result["segment"]


        if segment in segment_summary:

            segment_summary[
                segment
            ] += 1


    # ========================================================
    # RETURN SEGMENTATION
    # ========================================================

    return {

        "available": True,

        "method":
            "K-Means Clustering",

        "clusters":
            3,

        "features": [

            "average_attendance",

            "average_marks",

            "average_assignment",

            "average_overall_performance"
        ],

        "total_students":
            len(student_results),

        "segment_summary":
            segment_summary,

        "students":
            student_results
    }