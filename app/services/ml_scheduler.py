from apscheduler.schedulers.background import BackgroundScheduler

from app.database.database import SessionLocal
from app.services.future_prediction_model import (
    retrain_future_model_if_needed
)



# ============================================================
# SCHEDULER
# ============================================================

scheduler = BackgroundScheduler()


# ============================================================
# AUTOMATIC ML MODEL CHECK
# ============================================================

def automatic_future_model_training():

    db = SessionLocal()

    try:

        print("\n==================================================")
        print("AUTOMATIC ML MODEL CHECK STARTED")
        print("==================================================")

        try:

            result = retrain_future_model_if_needed(
                db=db,
                minimum_new_records=10
            )

            print(
                "Automatic Future Performance ML check completed."
            )

            if result:

                print(
                    f"Retrained: "
                    f"{result.get('retrained', False)}"
                )

                print(
                    f"Reason: "
                    f"{result.get('reason', 'N/A')}"
                )

                print(
                    f"Training samples: "
                    f"{result.get('training_samples', 'N/A')}"
                )

                print(
                    f"New records: "
                    f"{result.get('new_records', 'N/A')}"
                )

        except ValueError as e:

            print(
                f"ML model was not retrained: {str(e)}"
            )

        except Exception as e:

            print(
                f"Automatic ML training check failed: {str(e)}"
            )

    finally:

        db.close()

        print(
            "==================================================\n"
        )


# ============================================================
# START SCHEDULER
# ============================================================

def start_ml_scheduler():

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
        "Future Performance model will be checked "
        "every 1 hour."
    )


# ============================================================
# STOP SCHEDULER
# ============================================================

def stop_ml_scheduler():

    if scheduler.running:

        scheduler.shutdown(
            wait=False
        )

        print(
            "Automatic ML scheduler stopped."
        )