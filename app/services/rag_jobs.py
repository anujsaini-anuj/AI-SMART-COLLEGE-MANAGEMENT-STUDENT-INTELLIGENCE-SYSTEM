import logging
from pathlib import Path

from sqlalchemy import text
from rq import get_current_job

from app.database.database import engine
from app.services.rag_queue import redis_connection
from app.services.rag_service import (
    DOCUMENT_DIR,
    SUPPORTED_EXTENSIONS,
    build_rag_index,
    delete_indexed_document_source,
)

logger = logging.getLogger(__name__)

JOB_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS rag_document_jobs (
    job_id VARCHAR(36) PRIMARY KEY,
    source TEXT NOT NULL,
    job_status VARCHAR(20) NOT NULL,
    message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
)
"""


def ensure_job_table():
    with engine.begin() as connection:
        connection.execute(text(JOB_TABLE_SQL))


def create_job(job_id: str, source: str):
    ensure_job_table()

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO rag_document_jobs
                    (job_id, source, job_status, message)
                VALUES
                    (:job_id, :source, 'queued', :message)
                """
            ),
            {
                "job_id": job_id,
                "source": source,
                "message": "Job Redis queue mein submit ho rahi hai.",
            },
        )


def update_job(job_id: str, job_status: str, message: str):
    ensure_job_table()

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                UPDATE rag_document_jobs
                SET job_status = :job_status,
                    message = :message,
                    updated_at = NOW()
                WHERE job_id = :job_id
                """
            ),
            {
                "job_id": job_id,
                "job_status": job_status,
                "message": message,
            },
        )


def get_job(job_id: str):
    ensure_job_table()

    with engine.begin() as connection:
        result = connection.execute(
            text(
                """
                SELECT
                    job_id,
                    source,
                    job_status,
                    message,
                    created_at,
                    updated_at
                FROM rag_document_jobs
                WHERE job_id = :job_id
                """
            ),
            {"job_id": job_id},
        ).mappings().first()

        return dict(result) if result else None

def _with_index_lock(operation):
    lock = redis_connection.lock(
        "rag:indexing:lock",
        timeout=7200,
        blocking_timeout=7200,
    )

    if not lock.acquire(blocking=True):
        raise TimeoutError("Could not acquire RAG indexing lock.")

    try:
        return operation()
    finally:
        try:
            lock.release()
        except Exception:
            logger.exception("Could not release RAG indexing lock.")


def _build_index_with_lock():
    return _with_index_lock(build_rag_index)


def _run_task(job_id: str, operation):
    """
    RQ retry ke liye exception ko swallow nahi karna.
    Error par exception dobara raise hoga, jisse RQ retry kar sake.
    """

    update_job(
        job_id,
        "processing",
        "Background worker document process kar raha hai.",
    )

    try:
        result = operation()

        return result

    except Exception:
        logger.exception(
            "RAG job failed during an indexing attempt: %s",
            job_id,
        )

        try:
            update_job(
                job_id,
                "retrying",
                "Attempt fail hui. Queue retry kar sakti hai.",
            )
        except Exception:
            logger.exception(
                "Could not update retry status: %s",
                job_id,
            )

        raise


def process_uploaded_document(job_id: str, source: str):
    """Uploaded document ko existing incremental indexer se process karo."""

    def operation():
        result = _build_index_with_lock()

        indexed_sources = set(result.get("sources", []))

        if source not in indexed_sources:
            raise RuntimeError(
                f"Uploaded source was not indexed: {source}"
            )

        update_job(
            job_id,
            "indexed",
            "Document successfully indexed and searchable hai.",
        )

        return {
            "job_id": job_id,
            "source": source,
            "status": "indexed",
        }

    return _run_task(job_id, operation)


def process_full_reindex(job_id: str):
    """Saare documents ko PostgreSQL/pgvector ke saath synchronize karo."""

    def operation():
        result = _build_index_with_lock()

        update_job(
            job_id,
            "completed",
            "Full RAG index synchronization complete hui.",
        )

        return {
            "job_id": job_id,
            "status": "completed",
            "index_result": result,
        }

    return _run_task(job_id, operation)

def process_delete_document(job_id: str, source: str):
    def operation():
        def delete_and_index():
            project_root = DOCUMENT_DIR.parent.parent.resolve()
            root = DOCUMENT_DIR.resolve()
            supplied = Path(source)

            if supplied.is_absolute():
                raise ValueError("Absolute paths are not allowed.")

            target = (project_root / supplied).resolve()

            try:
                target.relative_to(root)
            except ValueError:
                raise ValueError(
                    "Path must remain inside app/Document."
                )

            if target == root:
                raise ValueError("A document file path is required.")

            if target.exists():
                if not target.is_file():
                    raise ValueError("A regular document file is required.")
                target.unlink()

            deleted_chunks = 0

            if target.suffix.lower() in SUPPORTED_EXTENSIONS:
                deleted_chunks = delete_indexed_document_source(source)

            index_result = build_rag_index()

            update_job(
                job_id,
                "completed",
                "Document delete hua aur index synchronize ho gaya.",
            )

            return {
                "job_id": job_id,
                "source": source,
                "status": "completed",
                "deleted_chunks": deleted_chunks,
                "index_result": index_result,
            }

        return _with_index_lock(delete_and_index)

    return _run_task(job_id, operation)


def mark_rag_job_failed(
    job,
    connection,
    exception_type,
    exception_value,
    traceback,
):
    """
    RQ ka final failure callback.
    Retry attempts exhaust hone par PostgreSQL status failed karega.
    """

    job_id = getattr(job, "id", None)

    if not job_id:
        return

    try:
        update_job(
            job_id,
            "failed",
            (
                "Job retries ke baad bhi fail hui: "
                f"{str(exception_value)[:700]}"
            ),
        )

    except Exception:
        logger.exception(
            "Could not persist final failure for RAG job %s",
            job_id,
        )