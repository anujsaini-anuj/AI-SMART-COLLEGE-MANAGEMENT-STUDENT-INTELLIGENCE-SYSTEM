import logging
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.blocking import BlockingScheduler
from rq import Callback

from app.services.rag_queue import (
    rag_queue,
    redis_connection,
    get_retry_policy,
)
from app.services.rag_jobs import (
    create_job,
    update_job,
    mark_rag_job_failed,
)


logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

TIMEZONE = ZoneInfo("Asia/Kolkata")


def enqueue_nightly_reindex():
    """
    Har din full RAG index synchronization ko
    Redis/RQ queue mein submit karo.

    Actual indexing RAG worker karega.
    """

    today = datetime.now(TIMEZONE).date().isoformat()

    # Ek din mein duplicate scheduled jobs ko roko.
    dedupe_key = f"rag:scheduler:nightly:{today}"

    acquired = redis_connection.set(
        dedupe_key,
        "1",
        nx=True,
        ex=48 * 60 * 60,
    )

    if not acquired:
        logger.info(
            "Nightly RAG reindex already scheduled today: %s",
            today,
        )
        return

    job_id = str(uuid.uuid4())
    job_created = False

    try:
        # PostgreSQL mein trackable job record.
        create_job(
            job_id,
            "__ALL_DOCUMENTS__",
        )
        job_created = True

        # Sirf queue mein job submit hoti hai.
        # Indexing worker process mein hogi.
        rag_queue.enqueue(
            "app.services.rag_jobs.process_full_reindex",
            job_id,
            job_id=job_id,
            job_timeout=7200,
            retry=get_retry_policy(),
            on_failure=Callback(
                mark_rag_job_failed,
                timeout=30,
            ),
            result_ttl=86400,
            failure_ttl=604800,
        )

        logger.info(
            "Nightly RAG reindex queued successfully. "
            "Date=%s JobID=%s",
            today,
            job_id,
        )

    except Exception as exc:
        logger.exception(
            "Could not enqueue nightly RAG reindex."
        )

        if job_created:
            try:
                update_job(
                    job_id,
                    "failed",
                    f"Scheduler could not enqueue job: {exc}",
                )
            except Exception:
                logger.exception(
                    "Could not update scheduled job status."
                )

        # Failed submission ko baad mein dobara attempt
        # karne ki permission do.
        try:
            redis_connection.delete(dedupe_key)
        except Exception:
            logger.exception(
                "Could not release scheduler deduplication key."
            )

        raise


def main():
    scheduler = BlockingScheduler(
        timezone=TIMEZONE,
    )

    scheduler.add_job(
        enqueue_nightly_reindex,
        trigger="cron",
        hour=2,
        minute=0,
        id="rag_nightly_reindex",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=3600,
    )

    logger.info(
        "RAG scheduler started. "
        "Nightly indexing is scheduled for 02:00 AM IST."
    )

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("RAG scheduler stopped.")


if __name__ == "__main__":
    main()