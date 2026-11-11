import logging
from pathlib import Path

from sqlalchemy import text

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
    progress INTEGER NOT NULL DEFAULT 0,
    stage VARCHAR(50) NOT NULL DEFAULT 'queued',
    message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
)
"""


def ensure_job_table():
    with engine.begin() as connection:
        connection.execute(text(JOB_TABLE_SQL))

        # Existing table mein naye columns add honge.
        connection.execute(text("""
            ALTER TABLE rag_document_jobs
            ADD COLUMN IF NOT EXISTS progress INTEGER
            NOT NULL DEFAULT 0
        """))

        connection.execute(text("""
            ALTER TABLE rag_document_jobs
            ADD COLUMN IF NOT EXISTS stage VARCHAR(50)
            NOT NULL DEFAULT 'queued'
        """))


def create_job(job_id: str, source: str):
    ensure_job_table()

    with engine.begin() as connection:
        connection.execute(
            text("""
                INSERT INTO rag_document_jobs
                    (
                        job_id,
                        source,
                        job_status,
                        progress,
                        stage,
                        message
                    )
                VALUES
                    (
                        :job_id,
                        :source,
                        'queued',
                        0,
                        'queued',
                        :message
                    )
            """),
            {
                "job_id": job_id,
                "source": source,
                "message": "Job Redis queue mein submit ho rahi hai.",
            },
        )

def update_job(
    job_id: str,
    job_status: str,
    message: str,
    progress=None,
    stage=None,
):
    with engine.begin() as connection:
        connection.execute(
            text("""
                UPDATE rag_document_jobs
                SET
                    job_status = :job_status,
                    message = :message,
                    progress = COALESCE(:progress, progress),
                    stage = COALESCE(:stage, stage),
                    updated_at = NOW()
                WHERE job_id = :job_id
            """),
            {
                "job_id": job_id,
                "job_status": job_status,
                "message": message,
                "progress": progress,
                "stage": stage,
            },
        )


def get_job(job_id: str):
    with engine.begin() as connection:
        result = connection.execute(
            text("""
                SELECT
                    job_id,
                    source,
                    job_status,
                    progress,
                    stage,
                    message,
                    created_at,
                    updated_at
                FROM rag_document_jobs
                WHERE job_id = :job_id
            """),
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


def _build_index_with_lock(progress_callback=None):
    return _with_index_lock(
        lambda: build_rag_index(
            progress_callback=progress_callback
        )
    )

def _run_task(job_id: str, operation):
    """
    RQ retry ke liye exception ko swallow nahi karna.
    Error par exception dobara raise hoga, jisse RQ retry kar sake.
    """

    update_job(
        job_id,
        "processing",
        "Background worker document process kar raha hai.",
        progress=5,
        stage="starting",
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
                stage="retrying",
            )
            
        except Exception:
            logger.exception(
                "Could not update retry status: %s",
                job_id,
            )

        raise

def process_uploaded_document(job_id: str, source: str):
    """Uploaded document ko progress tracking ke saath index karo."""

    def operation():

        def progress_callback(stage, progress, message):
            update_job(
                job_id=job_id,
                job_status="processing",
                progress=progress,
                stage=stage,
                message=message,
            )

            # RQ Worker terminal mein live progress
            logger.info(
                "[RAG INDEXING] Job=%s | Stage=%s | Progress=%s%% | Message=%s",
                job_id,
                stage,
                progress,
                message,
            )

            


           
            

        result = _build_index_with_lock(
            progress_callback=progress_callback
        )

        indexed_sources = set(
            result.get("sources", [])
        )

        if source not in indexed_sources:
            raise RuntimeError(
                f"Uploaded document was not indexed: {source}"
            )

        update_job(
            job_id=job_id,
            job_status="indexed",
            progress=100,
            stage="completed",
            message="Document indexed successfully.",
        )

        return result

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
        logger.error("Failed RAG job has no job ID.")
        return

    try:
        update_job(
            job_id,
            "failed",
            (
                "Job retries ke baad bhi fail hui: "
                f"{str(exception_value)[:700]}"
            ),
            stage="failed",
        )
        

    except Exception:
        logger.exception(
            "Could not persist final failure for RAG job %s",
            job_id,
        )