import logging
import uuid
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from rq import Callback

from app.utils.auth import require_admin
from app.services.rag_service import (
    DOCUMENT_DIR,
    SUPPORTED_EXTENSIONS,
)
from app.services.rag_queue import (
    rag_queue,
    get_retry_policy,
)
from app.services.rag_jobs import (
    create_job,
    get_job,
    update_job,
    mark_rag_job_failed,
)

router = APIRouter(
    prefix="/rag-documents",
    tags=["RAG Documents"],
)

logger = logging.getLogger(__name__)

MAX_UPLOAD_BYTES = 20 * 1024 * 1024


def _submit_job(
    job_id: str,
    source: str,
    task_path: str,
    *task_args,
):
    """PostgreSQL mein job record banao aur Redis queue mein bhejo."""

    try:
        create_job(job_id, source)

    except Exception as exc:
        logger.exception("Could not create RAG job record.")

        raise HTTPException(
            status_code=500,
            detail="Could not create the indexing job record.",
        ) from exc

    try:
        rag_queue.enqueue(
            task_path,
            job_id,
            *task_args,
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

    except Exception as exc:
        logger.exception("Could not enqueue RAG job %s.", job_id)

        try:
            update_job(
                job_id,
                "failed",
                (
                    "Redis queue mein job submit nahi hui. "
                    "Redis aur RQ worker configuration check karo."
                ),
            )
        except Exception:
            logger.exception("Could not update failed job status.")

        raise HTTPException(
            status_code=503,
            detail=(
                "Document file save ho sakti hai, lekin indexing job "
                "queue nahi hui. Redis connection check karke retry karo."
            ),
        ) from exc

    return {
        "job_id": job_id,
        "indexing_status": "queued",
        "status_url": f"/rag-documents/status/{job_id}",
    }


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
            detail="Path must remain inside app/Document.",
        )

    if candidate == root:
        raise HTTPException(
            status_code=400,
            detail="A document file path is required.",
        )

    return candidate


# ============================================================
# UPLOAD
# ============================================================

@router.post(
    "/upload",
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_document(
    file: UploadFile = File(...),
    current_user=Depends(require_admin),
):
    DOCUMENT_DIR.mkdir(parents=True, exist_ok=True)

    try:
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

        content = await file.read(MAX_UPLOAD_BYTES + 1)

        if not content:
            raise HTTPException(
                status_code=400,
                detail="Uploaded file is empty.",
            )

        if len(content) > MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=413,
                detail="File exceeds the 20 MB limit.",
            )

        # Existing file ko overwrite mat karo.
        try:
            with destination.open("xb") as output:
                output.write(content)
        except FileExistsError:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"'{filename}' already exists. "
                    "Use a different filename."
                ),
            )

        source = destination.relative_to(
            DOCUMENT_DIR.parent.parent.resolve()
        ).as_posix()

        job_id = str(uuid.uuid4())

        job_info = _submit_job(
            job_id,
            source,
            "app.services.rag_jobs.process_uploaded_document",
            source,
        )

        return {
            "message": "Document uploaded and queued for indexing.",
            "filename": filename,
            "source": source,
            "size_bytes": len(content),
            **job_info,
        }

    finally:
        await file.close()


# ============================================================
# JOB STATUS
# ============================================================

@router.get("/status/{job_id}")
def get_indexing_status(
    job_id: str,
    current_user=Depends(require_admin),
):
    job = get_job(job_id)

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

        files.append({
            "filename": path.name,
            "source": source,
            "extension": extension or None,
            "supported": extension in SUPPORTED_EXTENSIONS,
            "size_bytes": size_bytes,
        })

    return {
        "document_directory": str(DOCUMENT_DIR),
        "total_files": len(files),
        "files": files,
    }


# ============================================================
# QUEUED FULL REINDEX
# ============================================================

@router.post(
    "/reindex",
    status_code=status.HTTP_202_ACCEPTED,
)
def reindex_documents(
    current_user=Depends(require_admin),
):
    job_id = str(uuid.uuid4())

    job_info = _submit_job(
        job_id,
        "__ALL_DOCUMENTS__",
        "app.services.rag_jobs.process_full_reindex",
    )

    return {
        "message": "Full reindex job queued.",
        **job_info,
    }


# ============================================================
# QUEUED DOCUMENT DELETE
# ============================================================

@router.delete(
    "/",
    status_code=status.HTTP_202_ACCEPTED,
)
def delete_document(
    source: str = Query(
        ...,
        description=(
            "Project-relative path, e.g. "
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
            detail="A regular document file is required.",
        )

    project_source = target.relative_to(
        DOCUMENT_DIR.parent.parent.resolve()
    ).as_posix()

    job_id = str(uuid.uuid4())

    job_info = _submit_job(
        job_id,
        project_source,
        "app.services.rag_jobs.process_delete_document",
        project_source,
    )

    return {
        "message": "Document deletion job queued.",
        **job_info,
    }