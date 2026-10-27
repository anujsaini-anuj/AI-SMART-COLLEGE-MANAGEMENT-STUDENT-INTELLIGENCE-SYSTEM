from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from starlette.concurrency import run_in_threadpool

from app.utils.auth import require_admin
from app.services.rag_service import (
    DOCUMENT_DIR,
    PROJECT_ROOT,
    SUPPORTED_EXTENSIONS,
    build_rag_index,
)

import logging

logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/rag-documents",
    tags=["RAG Document Management"],
)


# Maximum upload size: 15 MB
MAX_UPLOAD_BYTES = 15 * 1024 * 1024

# Uploaded documents are stored separately from existing
# college policy files.
UPLOAD_DIR = DOCUMENT_DIR / "uploads"


@router.post(
    "/upload",
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    file: UploadFile = File(...),
    current_user=Depends(require_admin),
):
    """
    Upload a document and automatically synchronize
    the RAG index.

    Only authenticated admins can upload documents.
    """

    original_name = Path(file.filename or "").name.strip()

    if (
        not original_name
        or original_name in {".", ".."}
        or "\x00" in original_name
    ):
        raise HTTPException(
            status_code=400,
            detail="A valid filename is required.",
        )

    extension = Path(original_name).suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:
        allowed = ", ".join(sorted(SUPPORTED_EXTENSIONS))

        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {allowed}",
        )

    content = await file.read(MAX_UPLOAD_BYTES + 1)
    await file.close()

    if not content:
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is empty.",
        )

    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail="Maximum upload size is 15 MB.",
        )

    UPLOAD_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    destination = UPLOAD_DIR / original_name

    # Keep a copy so that a failed re-index can restore
    # the previously uploaded document.
    previous_content = (
        destination.read_bytes()
        if destination.exists()
        else None
    )

    try:
        # Uploading the same filename replaces the previous
        # file only if indexing succeeds.
        destination.write_bytes(content)

        # Run blocking extraction, embedding and DB work
        # outside the async event loop.
        index_result = await run_in_threadpool(
            build_rag_index
        )

        source = destination.relative_to(
            PROJECT_ROOT
        ).as_posix()

        # Do not report success if the document did not
        # produce any indexed chunks.
        indexed_sources = index_result.get(
            "sources",
            [],
        )

        if source not in indexed_sources:
            raise RuntimeError(
                "The file was uploaded, but no usable "
                "document chunks were indexed. Check that "
                "the document contains extractable content "
                "and inspect the server logs."
            )

        return {
            "message": (
                "Document uploaded and RAG index "
                "updated successfully."
            ),
            "filename": original_name,
            "source": source,
            "uploaded_by_user_id": current_user.id,
            "indexing": index_result,
        }

    except Exception as exc:
        # Restore the old file if this was an update.
        # Delete the new file if this was a first upload.
        try:
            if previous_content is None:
                destination.unlink(missing_ok=True)
            else:
                destination.write_bytes(previous_content)
        except OSError:
            pass

        if isinstance(exc, HTTPException):
            raise

        logger.exception(
            "RAG document upload/indexing failed for file: %s",
            original_name,
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Document indexing failed. The previous "
                "uploaded file, if any, was restored. "
                "Check the server logs for details."
            ),
        ) from exc
