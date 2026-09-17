# ==================================================
# PERSONALIZED RECOMMENDATION SERVICE
# ==================================================


def generate_recommendations(
    attendance_percentage,
    marks_percentage,
    assignment_percentage,
    overall_percentage
):

    recommendations = []

    # ==================================================
    # ATTENDANCE RECOMMENDATION
    # ==================================================

    if attendance_percentage < 75:

        if attendance_percentage < 60:
            priority = "High"
        else:
            priority = "Medium"

        recommendations.append({
            "recommendation_text":
                "Your attendance is below the recommended level. "
                "Attend classes regularly to improve your attendance.",

            "recommendation_type":
                "Attendance",

            "priority":
                priority
        })


    # ==================================================
    # MARKS RECOMMENDATION
    # ==================================================

    if marks_percentage < 50:

        if marks_percentage < 40:
            priority = "High"
        else:
            priority = "Medium"

        recommendations.append({
            "recommendation_text":
                "Your marks indicate an academic gap. "
                "Focus on revision, practice questions, "
                "and subject preparation.",

            "recommendation_type":
                "Marks",

            "priority":
                priority
        })


    # ==================================================
    # ASSIGNMENT RECOMMENDATION
    # ==================================================

    if assignment_percentage < 50:

        recommendations.append({
            "recommendation_text":
                "Your assignment performance is low. "
                "Complete and submit assignments on time "
                "and review the feedback.",

            "recommendation_type":
                "Assignment",

            "priority":
                "Medium"
        })


    # ==================================================
    # GENERAL PERFORMANCE RECOMMENDATION
    # ==================================================

    if overall_percentage >= 80:

        recommendations.append({
            "recommendation_text":
                "Your overall performance is strong. "
                "Maintain consistent attendance, preparation, "
                "and timely assignment submissions.",

            "recommendation_type":
                "General",

            "priority":
                "Low"
        })

    elif overall_percentage >= 60:

        recommendations.append({
            "recommendation_text":
                "Maintain regular study habits and "
                "focus on improving your weaker areas.",

            "recommendation_type":
                "General",

            "priority":
                "Medium"
        })


    # ==================================================
    # NO MAJOR ISSUE
    # ==================================================

    if not recommendations:

        recommendations.append({
            "recommendation_text":
                "Your performance is currently stable. "
                "Continue your regular study routine.",

            "recommendation_type":
                "General",

            "priority":
                "Low"
        })


    return recommendations