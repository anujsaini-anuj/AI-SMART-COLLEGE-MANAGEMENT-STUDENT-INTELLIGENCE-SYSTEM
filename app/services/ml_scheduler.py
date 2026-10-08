from apscheduler.schedulers.background import BackgroundScheduler

from app.database.database import SessionLocal
from app.services.prediction_service import train_future_prediction_model


# ============================================================
# ML SCHEDULER
# ============================================================

scheduler = BackgroundScheduler()


def automatic_future_model_training():
    """
    Background job for Future Performance ML model.

    This function runs automatically according to the
    scheduler interval.

    The existing train_future_prediction_model()
    function decides whether retraining is actually required
    based on the existing training rules.
    """

    db = SessionLocal()

    try:

        print(
            "\n=================================================="
        )
        print(
            "AUTOMATIC ML MODEL CHECK STARTED"
        )
        print(
            "=================================================="
        )

        try:

            result = train_future_prediction_model(db)

            print(
                "Future Performance ML model check completed."
            )

            if result:
                print(
                    f"Model: {result.get('model_name', 'N/A')}"
                )

                print(
                    f"Training samples: "
                    f"{result.get('training_samples', 'N/A')}"
                )

                print(
                    f"Trained at: "
                    f"{result.get('trained_at', 'N/A')}"
                )

        except ValueError as e:

            # Example:
            # Not enough training data yet.

            print(
                f"ML model was not retrained: {str(e)}"
            )

        except Exception as e:

            print(
                f"Automatic ML training failed: {str(e)}"
            )

    finally:

        db.close()

        print(
            "==================================================\n"
        )


def start_ml_scheduler():

    # --------------------------------------------------------
    # Run the check every 1 hour
    # --------------------------------------------------------

    scheduler.add_job(
        automatic_future_model_training,
        trigger="interval",
        hours=1,
        id="future_performance_ml_training",
        replace_existing=True,
        max_instances=1
    )

    scheduler.start()

    print(
        "Automatic ML scheduler started."
    )

    print(
        "Future Performance model will be checked every 1 hour."
    )


def stop_ml_scheduler():

    if scheduler.running:

        scheduler.shutdown(
            wait=False
        )

        print(
            "Automatic ML scheduler stopped."
        )