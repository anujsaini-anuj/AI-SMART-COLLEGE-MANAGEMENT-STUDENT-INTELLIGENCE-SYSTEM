import logging
import os

from app.services.rag_queue import (
    rag_queue,
    redis_connection,
)

from rq import SimpleWorker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    # Redis connection check
    redis_connection.ping()

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

    # Scheduler enabled: delayed retries ke liye.
    worker.work(with_scheduler=True)


if __name__ == "__main__":
    main()