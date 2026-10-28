import logging
import threading
import uuid
from pathlib import Path

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy import text
from starlette.concurrency import run_in_threadpool

from app.database.database import engine
from app.utils.auth import require_admin
from app.services.rag_service import (
    DOCUMENT_DIR,
    SUPPORTED_EXTENSIONS,
    build_rag_index,
    delete_indexed_document_source,
)

router = APIRouter(
    prefix="/rag-documents",
    tags=["RAG Documents"],
)

logger = logging.getLogger(__name__)

MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20 MB

# Ek process ke andar ek samay par sirf ek indexing operation.
# Upload, manual reindex aur deletion ek doosre se conflict nahi karenge.
INDEX_LOCK = threading.Lock()


# ============================================================
# INDEXING JOB STATUS TABLE
# ============================================================

def _ensure_job_table():
    """PostgreSQL mein indexing jobs ka status store karo."""

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS rag_document_jobs (
                    job_id VARCHAR(36) PRIMARY KEY,
                    source TEXT NOT NULL,
                    job_status VARCHAR(20) NOT NULL,
                    message TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
        )


def _create_job(job_id: str, source: str):
    _ensure_job_table()

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO rag_document_jobs
                    (job_id, source, job_status, message)
                VALUES
                    (:job_id, :source, 'processing', :message)
                """
            ),
            {
                "job_id": job_id,
                "source": source,
                "message": "Document upload ho gaya hai. Indexing pending hai.",
            },
        )


def _update_job(
    job_id: str,
    job_status: str,
    message: str,
):
    _ensure_job_table()

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


def _get_job(job_id: str):
    _ensure_job_table()

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


# ============================================================
# SAFE INDEXING
# ============================================================

def _run_indexing():
    """Indexing operations ko ek-ek karke execute karo."""

    with INDEX_LOCK:
        return build_rag_index()


def _process_uploaded_document(
    job_id: str,
    source: str,
):
    """
    FastAPI BackgroundTasks is function ko response bhejne ke baad
    execute karega. Function khud indexing status update karta hai.
    """

    try:
        logger.info("Background RAG indexing started: %s", source)

        index_result = _run_indexing()

        indexed_sources = set(index_result.get("sources", []))

        # Sirf function return hone ko success na maano.
        # Confirm karo ki uploaded source index mein aa gaya hai.
        if source not in indexed_sources:
            _update_job(
                job_id,
                "failed",
                (
                    "Indexing complete hui, lekin uploaded document "
                    "indexed sources mein nahi mila. Server logs aur "
                    "document extraction report check karo."
                ),
            )
            logger.error(
                "Uploaded source was not indexed: %s",
                source,
            )
            return

        _update_job(
            job_id,
            "indexed",
            "Document successfully indexed. Ab RAG mein searchable hai.",
        )

        logger.info("Background RAG indexing completed: %s", source)

    except Exception:
        logger.exception(
            "Background RAG indexing failed: %s",
            source,
        )

        try:
            _update_job(
                job_id,
                "failed",
                (
                    "Indexing fail hui. Server logs check karo aur "
                    "POST /rag-documents/reindex se retry kar sakte ho."
                ),
            )
        except Exception:
            logger.exception(
                "Could not save failed indexing status for job %s",
                job_id,
            )


# ============================================================
# SAFE DOCUMENT PATH
# ============================================================

def _safe_document_path(source: str) -> Path:
    root = DOCUMENT_DIR.resolve()
    project_root = root.parent.parent.resolve()

    supplied = Path(source)

    if supplied.is_absolute():
        raise HTTPException(
            status_code=400,
            detail="Absolute paths are not allowed.",
        )

    candidate = (project_root / supplied).resolve()

    try:
        candidate.relative_to(root)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="The path must point inside app/Document.",
        )

    if candidate == root:
        raise HTTPException(
            status_code=400,
            detail="A document file path is required.",
        )

    return candidate


# ============================================================
# UPLOAD DOCUMENT - ASYNCHRONOUS INDEXING
# ============================================================

@router.post(
    "/upload",
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user=Depends(require_admin),
):
    """
    File save karo, processing status create karo aur indexing
    ko background mein start karo.
    """

    try:
        DOCUMENT_DIR.mkdir(parents=True, exist_ok=True)

        filename = Path(file.filename or "").name.strip()

        if not filename or filename in {".", ".."}:
            raise HTTPException(
                status_code=400,
                detail="A valid filename is required.",
            )

        extension = Path(filename).suffix.lower()

        if extension not in SUPPORTED_EXTENSIONS:
            raise HTTPException(
                status_code=415,
                detail={
                    "message": "Unsupported file type.",
                    "supported_extensions": sorted(
                        SUPPORTED_EXTENSIONS
                    ),
                },
            )

        destination = (DOCUMENT_DIR / filename).resolve()

        try:
            destination.relative_to(DOCUMENT_DIR.resolve())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid filename.",
            )

        if destination.exists():
            raise HTTPException(
                status_code=409,
                detail=(
                    f"'{filename}' already exists in app/Document. "
                    "Use a different filename."
                ),
            )

        content = await file.read(MAX_UPLOAD_BYTES + 1)

        if not content:
            raise HTTPException(
                status_code=400,
                detail="The uploaded file is empty.",
            )

        if len(content) > MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=413,
                detail="The file exceeds the 20 MB limit.",
            )

        # Exclusive creation prevents accidental overwriting.
        try:
            with destination.open("xb") as output:
                output.write(content)
        except FileExistsError:
            raise HTTPException(
                status_code=409,
                detail="A file with this name already exists.",
            )

        source = destination.relative_to(
            DOCUMENT_DIR.parent.parent.resolve()
        ).as_posix()

        job_id = str(uuid.uuid4())

        try:
            # Status database mein save hone ke baad hi task schedule karo.
            _create_job(job_id, source)
        except Exception as exc:
            logger.exception(
                "Could not create indexing job for %s",
                source,
            )
            raise HTTPException(
                status_code=500,
                detail=(
                    "File save ho gayi, lekin indexing job create "
                    "nahi hui. Server logs check karo aur reindex endpoint "
                    "se index synchronize karo."
                ),
            ) from exc

        background_tasks.add_task(
            _process_uploaded_document,
            job_id,
            source,
        )

        # Indexing complete hone ka wait nahi kiya ja raha.
        return {
            "message": (
                "Document uploaded. Background indexing started."
            ),
            "filename": filename,
            "source": source,
            "size_bytes": len(content),
            "job_id": job_id,
            "indexing_status": "processing",
            "status_url": f"/rag-documents/status/{job_id}",
        }

    finally:
        await file.close()


# ============================================================
# CHECK INDEXING STATUS
# ============================================================

@router.get("/status/{job_id}")
def get_indexing_status(
    job_id: str,
    current_user=Depends(require_admin),
):
    """Job ID se document ki indexing status check karo."""

    job = _get_job(job_id)

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="Indexing job not found.",
        )

    return job


# ============================================================
# LIST DOCUMENTS
# ============================================================

@router.get("/")
async def list_documents(
    current_user=Depends(require_admin),
):
    DOCUMENT_DIR.mkdir(parents=True, exist_ok=True)

    files = []

    for path in sorted(DOCUMENT_DIR.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue

        source = path.relative_to(
            DOCUMENT_DIR.parent.parent.resolve()
        ).as_posix()

        extension = path.suffix.lower()

        try:
            size_bytes = path.stat().st_size
        except OSError:
            size_bytes = None

        files.append(
            {
                "filename": path.name,
                "source": source,
                "extension": extension or None,
                "supported": extension in SUPPORTED_EXTENSIONS,
                "size_bytes": size_bytes,
            }
        )

    return {
        "document_directory": str(DOCUMENT_DIR),
        "total_files": len(files),
        "files": files,
    }


# ============================================================
# MANUAL REINDEX
# ============================================================

@router.post("/reindex")
async def reindex_documents(
    current_user=Depends(require_admin),
):
    """Saare documents ko PostgreSQL/pgvector ke saath synchronize karo."""

    try:
        result = await run_in_threadpool(_run_indexing)

        return {
            "message": "RAG indexing completed.",
            "index_result": result,
        }

    except Exception as exc:
        logger.exception("Manual RAG reindex failed")

        raise HTTPException(
            status_code=500,
            detail=(
                "RAG indexing failed. Check the server logs "
                "and the document scan report."
            ),
        ) from exc


# ============================================================
# DELETE DOCUMENT AND SYNCHRONIZE INDEX
# ============================================================

def _delete_document_and_sync(
    target: Path,
    source: str,
    extension: str,
):
    """
    File deletion, chunk deletion aur reindex ko ek lock ke andar
    rakho taaki upload indexing ke saath race na ho.
    """

    with INDEX_LOCK:
        if not target.exists():
            raise HTTPException(
                status_code=404,
                detail="Document not found.",
            )

        target.unlink()

        deleted_chunks = 0

        if extension in SUPPORTED_EXTENSIONS:
            deleted_chunks = delete_indexed_document_source(source)

        try:
            index_result = build_rag_index()

        except Exception:
            logger.exception(
                "Reindex failed after deleting %s",
                source,
            )

            return {
                "message": (
                    "File deleted and its indexed chunks removed "
                    "where applicable, but full index synchronization "
                    "failed. Retry POST /rag-documents/reindex."
                ),
                "source": source,
                "deleted_chunks": deleted_chunks,
                "index_synchronized": False,
            }

        return {
            "message": "Document deleted and index synchronized.",
            "source": source,
            "deleted_chunks": deleted_chunks,
            "index_synchronized": True,
            "index_result": index_result,
        }


@router.delete("/")
async def delete_document(
    source: str = Query(
        ...,
        description=(
            "Exact project-relative path, e.g. "
            "app/Document/college_rules.pdf"
        ),
    ),
    current_user=Depends(require_admin),
):
    target = _safe_document_path(source)

    if not target.exists():
        raise HTTPException(
            status_code=404,
            detail="Document not found.",
        )

    if target.is_symlink() or not target.is_file():
        raise HTTPException(
            status_code=400,
            detail="The supplied path must identify a regular file.",
        )

    project_relative_source = target.relative_to(
        DOCUMENT_DIR.parent.parent.resolve()
    ).as_posix()

    try:
        return await run_in_threadpool(
            _delete_document_and_sync,
            target,
            project_relative_source,
            target.suffix.lower(),
        )

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception(
            "Document deletion failed: %s",
            project_relative_source,
        )

        raise HTTPException(
            status_code=500,
            detail="Document deletion failed. Check the server logs.",
        ) from exc
