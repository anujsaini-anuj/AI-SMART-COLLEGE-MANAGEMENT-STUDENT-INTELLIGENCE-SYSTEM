import logging
import os

from redis import Redis

from app.services.rag_queue import (
    rag_queue,
    redis_connection,
)

from rq import SimpleWorker, Worker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    force=True,
)
logger = logging.getLogger(__name__)


def main():
    # Redis connection check
    redis_connection.ping()

    logger.info("Redis connection successful.")

    logger.info(
        "RAG worker starting. Queue: %s",
        rag_queue.name,
    )

    # Local Windows development ke liye SimpleWorker.
    # Linux production deployment mein normal Worker.
    worker_class = (
        SimpleWorker
        if os.name == "nt"
        else Worker
    )

    worker = worker_class(
        [rag_queue],
        connection=redis_connection,
    )

    logger.info("Worker is waiting for jobs...")

    # Scheduler enabled: delayed retries ke liye.
    worker.work(with_scheduler=True)


if __name__ == "__main__":
    main()