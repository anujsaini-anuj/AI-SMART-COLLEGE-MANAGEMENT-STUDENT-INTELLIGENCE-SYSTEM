import logging
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
from starlette.concurrency import run_in_threadpool

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


def _safe_document_path(source: str) -> Path:
    """
    Accept a project-relative source such as:
    app/Document/college_rules.pdf

    The resolved file must remain inside DOCUMENT_DIR.
    """
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


@router.post(
    "/upload",
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    file: UploadFile = File(...),
    current_user=Depends(require_admin),
):
    """Save and index a document in the single document folder."""

    try:
        DOCUMENT_DIR.mkdir(parents=True, exist_ok=True)

        # Ignore any directory components in the uploaded filename.
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

        # Do not overwrite an original or previously uploaded file.
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

        try:
            index_result = await run_in_threadpool(
                build_rag_index
            )
        except Exception as exc:
            # Keep the saved file so an administrator can retry
            # indexing after correcting the underlying problem.
            logger.exception(
                "Indexing failed after uploading %s",
                source,
            )

            raise HTTPException(
                status_code=500,
                detail={
                    "message": (
                        "The file was saved, but indexing failed. "
                        "Use POST /rag-documents/reindex after "
                        "checking the server logs."
                    ),
                    "source": source,
                },
            ) from exc

        return {
            "message": "Document uploaded and indexing completed.",
            "filename": filename,
            "source": source,
            "size_bytes": len(content),
            "index_result": index_result,
        }

    finally:
        await file.close()


@router.get("/")
async def list_documents(
    current_user=Depends(require_admin),
):
    """List supported and unsupported files recursively."""

    DOCUMENT_DIR.mkdir(parents=True, exist_ok=True)

    files = []

    for path in sorted(DOCUMENT_DIR.rglob("*")):
        if not path.is_file():
            continue

        # Skip symbolic links so listing stays within the document root.
        if path.is_symlink():
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


@router.post("/reindex")
async def reindex_documents(
    current_user=Depends(require_admin),
):
    """Synchronize all documents in app/Document with pgvector."""

    try:
        result = await run_in_threadpool(build_rag_index)
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
    """Delete one document and remove its indexed chunks."""

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

    extension = target.suffix.lower()

    # Unsupported files are listed for administrators but are not
    # indexed by the RAG loader.
    project_relative_source = target.relative_to(
        DOCUMENT_DIR.parent.parent.resolve()
    ).as_posix()

    try:
        target.unlink()

        deleted_chunks = 0

        if extension in SUPPORTED_EXTENSIONS:
            deleted_chunks = await run_in_threadpool(
                delete_indexed_document_source,
                project_relative_source,
            )

        # Synchronize any other pending changes as well.
        try:
            index_result = await run_in_threadpool(
                build_rag_index
            )
        except Exception:
            logger.exception(
                "Reindex failed after deleting %s",
                project_relative_source,
            )

            return {
                "message": (
                    "File deleted and its indexed chunks removed "
                    "where applicable, but full index synchronization "
                    "failed. Retry POST /rag-documents/reindex."
                ),
                "source": project_relative_source,
                "deleted_chunks": deleted_chunks,
                "index_synchronized": False,
            }

        return {
            "message": "Document deleted and index synchronized.",
            "source": project_relative_source,
            "deleted_chunks": deleted_chunks,
            "index_synchronized": True,
            "index_result": index_result,
        }

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception(
            "Document deletion failed: %s",
            project_relative_source,
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Document deletion failed. Check the server logs."
            ),
        ) from exc
