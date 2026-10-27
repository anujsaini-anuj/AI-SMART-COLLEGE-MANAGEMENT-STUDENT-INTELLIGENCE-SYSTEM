import hashlib
import json
import os
import re
from pathlib import Path

from pypdf import PdfReader
from docx import Document as WordDocument

import numpy as np
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pgvector.psycopg2 import register_vector

from app.database.database import engine


import mimetypes
import zipfile

import fitz  # PyMuPDF

from redis import Redis

load_dotenv()


# ============================================================
# REDIS CACHE
# ============================================================

REDIS_URL = os.getenv(
    "REDIS_URL",
    "redis://localhost:6379/0",
)

RAG_CACHE_TTL_SECONDS = 300
RAG_CACHE_PREFIX = "rag:retrieval:v1:"

# One shared Redis client; redis-py manages its connection pool.
redis_client = Redis.from_url(
    REDIS_URL,
    decode_responses=True,
    socket_connect_timeout=1,
    socket_timeout=1,
)


def _rag_cache_key(question, top_k):
    normalized_question = " ".join(
        question.strip().lower().split()
    )

    key_data = (
        f"{INDEXER_VERSION}|"
        f"{EMBEDDING_MODEL}|"
        f"{EMBEDDING_DIMENSIONS}|"
        f"{CHUNK_SIZE}|"
        f"{CHUNK_OVERLAP}|"
        f"{MIN_RELEVANCE_SCORE}|"
        f"{top_k}|"
        f"{normalized_question}"
    )

    digest = hashlib.sha256(
        key_data.encode("utf-8")
    ).hexdigest()

    return f"{RAG_CACHE_PREFIX}{digest}"


def _get_rag_cache(key):
    try:
        cached_value = redis_client.get(key)

        if cached_value is not None:
            return json.loads(cached_value)

    except Exception:
        # Redis failure must not break RAG.
        pass

    return None


def _set_rag_cache(key, result):
    try:
        redis_client.setex(
            key,
            RAG_CACHE_TTL_SECONDS,
            json.dumps(result, ensure_ascii=False),
        )

    except Exception:
        # Continue without caching if Redis is unavailable.
        pass


def _invalidate_rag_cache():
    try:
        # Delete matching keys in batches instead of loading
        # every cache key into memory at once.
        batch = []

        for key in redis_client.scan_iter(
            match=f"{RAG_CACHE_PREFIX}*",
            count=200,
        ):
            batch.append(key)

            if len(batch) >= 200:
                redis_client.delete(*batch)
                batch.clear()

        if batch:
            redis_client.delete(*batch)

    except Exception:
        # Old entries expire after their TTL.
        pass


# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOCUMENT_DIR = PROJECT_ROOT / "app" / "Document"

VECTOR_TABLE = "college_document_chunks"

EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIMENSIONS = 768

CHUNK_SIZE = 700
CHUNK_OVERLAP = 100

TOP_K = 4
MIN_RELEVANCE_SCORE = 0.65

# Increment this when chunking/indexing logic changes in a way
# that requires regenerating all document embeddings.
INDEXER_VERSION = "3"

# Set this to true only when you intentionally want to clear
# the entire index because no supported documents remain.
ALLOW_EMPTY_INDEX = (
    os.getenv("RAG_ALLOW_EMPTY_INDEX", "false").strip().lower()
    == "true"
)


# ============================================================
# GEMINI CLIENT
# ============================================================

def get_client():
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY is missing from your .env file."
        )

    return genai.Client(api_key=api_key)


def embed_text(client, text, task_type):
    """
    Generate an embedding using Gemini.

    task_type:
        RETRIEVAL_DOCUMENT -> documents being indexed
        RETRIEVAL_QUERY    -> user questions
    """

    response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
        config=types.EmbedContentConfig(
            task_type=task_type,
            output_dimensionality=EMBEDDING_DIMENSIONS,
        ),
    )

    if not response.embeddings:
        raise RuntimeError(
            "Gemini returned an empty embedding response."
        )

    vector = response.embeddings[0].values

    if vector is None:
        raise RuntimeError(
            "Gemini returned an embedding without vector values."
        )

    return vector


# ============================================================
# DOCUMENT LOADING: TEXT + PDF OCR/VISION + DOCX IMAGES
# ============================================================

SUPPORTED_EXTENSIONS = {
    ".txt",
    ".md",
    ".pdf",
    ".docx",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".bmp",
    ".gif",
}

VISION_ENABLED = (
    os.getenv("RAG_VISION_ENABLED", "true").strip().lower()
    == "true"
)

VISION_MODEL = os.getenv(
    "GEMINI_VISION_MODEL",
    "gemini-3.6-flash",
)

# Avoid sending unusually large images to the Vision API.
MAX_IMAGE_BYTES = 15 * 1024 * 1024


def _get_mime_type(path):
    """Return an image MIME type based on the file extension."""

    mime_type, _ = mimetypes.guess_type(str(path))

    if not mime_type or not mime_type.startswith("image/"):
        raise ValueError(
            f"Unsupported image MIME type for: {path}"
        )

    return mime_type


def _describe_image(
    image_bytes,
    mime_type,
    context="",
    client=None,
):
    """
    Extract readable text and useful visual information
    from an image using Gemini Vision.

    Returns ordinary text so that the existing RAG chunking
    and embedding pipeline can process it.
    """

    if not VISION_ENABLED:
        return ""

    if not image_bytes:
        return ""

    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise ValueError(
            "Image exceeds the configured 15 MB limit. "
            "Resize or compress it before indexing."
        )

    if client is None:
        client = get_client()

    prompt = f"""
You are extracting information from a college document image.

Document context:
{context or "No additional context available."}

Instructions:
1. Transcribe all readable text accurately.
2. Preserve dates, amounts, percentages, names, IDs,
   headings, labels and numbered rules.
3. For tables, write each row in a readable text format.
4. For timetables, preserve day, time, subject and room.
5. For fee documents, preserve amounts, due dates and fines.
6. Describe diagrams, charts, stamps or visual information
   only when they convey useful document information.
7. If some text is unreadable, say so instead of guessing.
8. Do not invent missing information.
9. Return plain text suitable for a search index.
"""

    response = client.models.generate_content(
        model=VISION_MODEL,
        contents=[
            types.Part.from_bytes(
                data=image_bytes,
                mime_type=mime_type,
            ),
            prompt,
        ],
    )

    extracted = getattr(response, "text", None)

    if not extracted or not extracted.strip():
        raise RuntimeError(
            "Gemini Vision returned no readable text."
        )

    return extracted.strip()


def _extract_pdf_text(path, client=None):
    """
    Extract selectable PDF text first.

    If a page is scanned or contains embedded images,
    render that page and use Gemini Vision.

    Each extracted section includes its original page number.
    """

    if not VISION_ENABLED:
        # Preserve the old selectable-text behavior.
        reader = PdfReader(str(path))

        if reader.is_encrypted:
            raise ValueError(
                "PDF is encrypted and cannot be read without "
                "a password."
            )

        page_texts = []

        for page_number, page in enumerate(
            reader.pages,
            start=1,
        ):
            text = (page.extract_text() or "").strip()

            if text:
                page_texts.append(
                    f"Page {page_number}:\n{text}"
                )

        return "\n\n".join(page_texts).strip()

    if client is None:
        client = get_client()

    page_texts = []

    # PyMuPDF can extract page text and render scanned pages.
    with fitz.open(str(path)) as pdf:
        if pdf.needs_pass:
            raise ValueError(
                "PDF is encrypted and requires a password."
            )

        for page_index, page in enumerate(pdf, start=1):
            page_number = page_index

            selectable_text = (
                page.get_text("text") or ""
            ).strip()

            # Detect embedded raster images on this page.
            try:
                image_list = page.get_images(full=True)
                has_images = bool(image_list)
            except Exception:
                has_images = False

            sections = []

            if selectable_text:
                sections.append(
                    "Extracted PDF text:\n" + selectable_text
                )

            # Use Vision for scanned pages or pages containing
            # images. The rendered page preserves page context.
            needs_vision = (
                not selectable_text or has_images
            )

            if needs_vision:
                pixmap = page.get_pixmap(
                    matrix=fitz.Matrix(1.5, 1.5),
                    alpha=False,
                )

                image_bytes = pixmap.tobytes("png")

                vision_text = _describe_image(
                    image_bytes=image_bytes,
                    mime_type="image/png",
                    context=(
                        f"PDF file: {path.name}; "
                        f"page number: {page_number}"
                    ),
                    client=client,
                )

                if vision_text:
                    sections.append(
                        "Image/OCR extracted information:\n"
                        + vision_text
                    )

            if sections:
                page_texts.append(
                    f"Document: {path.name}\n"
                    f"Page {page_number}:\n"
                    + "\n\n".join(sections)
                )

    return "\n\n".join(page_texts).strip()


def _extract_docx_text(path, client=None):
    """
    Extract DOCX paragraphs, tables and embedded images.

    Embedded raster images are read from the DOCX ZIP package
    and sent to Gemini Vision.
    """

    document = WordDocument(str(path))
    parts = []

    # Extract paragraphs.
    for paragraph in document.paragraphs:
        text = paragraph.text.strip()

        if text:
            parts.append(text)

    # Extract tables.
    for table_number, table in enumerate(
        document.tables,
        start=1,
    ):
        table_rows = []

        for row in table.rows:
            cells = [
                cell.text.strip().replace("\n", " ")
                for cell in row.cells
            ]

            if any(cells):
                table_rows.append(" | ".join(cells))

        if table_rows:
            parts.append(
                f"Table {table_number}:\n"
                + "\n".join(table_rows)
            )

    # Extract embedded images from the DOCX package.
    if VISION_ENABLED:
        with zipfile.ZipFile(path, "r") as archive:
            image_names = sorted(
                name
                for name in archive.namelist()
                if name.startswith("word/media/")
                and not name.endswith("/")
            )

            for image_name in image_names:
                image_bytes = archive.read(image_name)

                extension = Path(image_name).suffix.lower()

                mime_type = mimetypes.guess_type(
                    image_name
                )[0]

                if (
                    not mime_type
                    or not mime_type.startswith("image/")
                    or mime_type == "image/svg+xml"
                ):
                    continue

                extracted = _describe_image(
                    image_bytes=image_bytes,
                    mime_type=mime_type,
                    context=(
                        f"DOCX file: {path.name}; "
                        f"embedded image: {image_name}"
                    ),
                    client=client,
                )

                if extracted:
                    parts.append(
                        f"Embedded image ({image_name}):\n"
                        f"{extracted}"
                    )

    return "\n\n".join(parts).strip()


def _extract_markdown_images(path, markdown_text, client=None):
    """
    Extract local images referenced by Markdown, for example:

        ![College timetable](images/timetable.png)

    The image path must remain inside app/Document.
    External URLs are intentionally not downloaded.
    """

    if not VISION_ENABLED:
        return ""

    pattern = re.compile(
        r"!\[([^\]]*)\]\(([^)]+)\)"
    )

    extracted_parts = []

    for match in pattern.finditer(markdown_text):
        alt_text = match.group(1).strip()
        target = match.group(2).strip()

        # Support paths containing optional Markdown titles.
        target = target.split('"')[0].strip()
        target = target.split("'")[0].strip()

        # Ignore URLs, anchors and data URLs.
        if re.match(
            r"^(https?://|data:|#)",
            target,
            flags=re.IGNORECASE,
        ):
            continue

        # Ignore query/fragment suffixes.
        target = target.split("#", 1)[0]
        target = target.split("?", 1)[0]

        image_path = (path.parent / target).resolve()

        try:
            image_path.relative_to(DOCUMENT_DIR.resolve())
        except ValueError:
            # Do not allow references outside the document folder.
            continue

        if not image_path.is_file():
            continue

        try:
            mime_type = _get_mime_type(image_path)
            image_bytes = image_path.read_bytes()

            extracted = _describe_image(
                image_bytes=image_bytes,
                mime_type=mime_type,
                context=(
                    f"Markdown file: {path.name}; "
                    f"image alt text: {alt_text or 'not provided'}"
                ),
                client=client,
            )

            if extracted:
                extracted_parts.append(
                    f"Markdown image: {target}\n"
                    f"Alt text: {alt_text}\n"
                    f"Extracted information:\n{extracted}"
                )

        except Exception as exc:
            raise RuntimeError(
                f"Failed to process Markdown image "
                f"'{target}' referenced by '{path.name}': {exc}"
            ) from exc

    return "\n\n".join(extracted_parts).strip()


def load_documents(return_report=False):
    """
    Load documents recursively from app/Document.

    Text and Markdown:
        Read text; analyze local Markdown image references.

    PDF:
        Extract selectable text and use Vision for scanned
        pages or pages with embedded images.

    DOCX:
        Extract paragraphs, tables and embedded images.

    Standalone images:
        Extract readable text and useful visual information.

    Output remains compatible with the existing indexer:
        [{"source": "...", "text": "..."}]

    Failed files are preserved from accidental index deletion.
    """

    if not DOCUMENT_DIR.exists():
        raise FileNotFoundError(
            f"RAG document directory does not exist: "
            f"{DOCUMENT_DIR}"
        )

    if not DOCUMENT_DIR.is_dir():
        raise NotADirectoryError(
            f"RAG document path is not a directory: "
            f"{DOCUMENT_DIR}"
        )

    documents = []

    report = {
        "files_scanned": 0,
        "supported_files": [],
        "unsupported_files": [],
        "failed_files": [],
        "empty_text_files": [],
        "preserve_sources": [],
    }

    # Reuse one Gemini client per indexing run.
    client = None

    def get_vision_client():
        nonlocal client

        if client is None:
            client = get_client()

        return client

    for path in sorted(DOCUMENT_DIR.rglob("*")):
        if not path.is_file():
            continue

        report["files_scanned"] += 1

        source = path.relative_to(
            PROJECT_ROOT
        ).as_posix()

        extension = path.suffix.lower()

        if extension not in SUPPORTED_EXTENSIONS:
            report["unsupported_files"].append({
                "source": source,
                "extension": extension or "(no extension)",
                "reason": "Unsupported file format",
            })
            continue

        report["supported_files"].append(source)

        try:
            if extension == ".txt":
                content = path.read_text(
                    encoding="utf-8-sig"
                ).strip()

            elif extension == ".md":
                markdown_text = path.read_text(
                    encoding="utf-8-sig"
                ).strip()

                image_text = ""

                if VISION_ENABLED:
                    image_text = _extract_markdown_images(
                        path,
                        markdown_text,
                        client=get_vision_client(),
                    )

                content = "\n\n".join(
                    part
                    for part in [
                        markdown_text,
                        image_text,
                    ]
                    if part
                ).strip()

            elif extension == ".pdf":
                content = _extract_pdf_text(
                    path,
                    client=(
                        get_vision_client()
                        if VISION_ENABLED
                        else None
                    ),
                )

            elif extension == ".docx":
                content = _extract_docx_text(
                    path,
                    client=(
                        get_vision_client()
                        if VISION_ENABLED
                        else None
                    ),
                )

            else:
                # Standalone image file.
                content = _describe_image(
                    image_bytes=path.read_bytes(),
                    mime_type=_get_mime_type(path),
                    context=(
                        f"Standalone college document image: "
                        f"{path.name}"
                    ),
                    client=get_vision_client(),
                )

        except Exception as exc:
            report["failed_files"].append({
                "source": source,
                "reason": (
                    f"{type(exc).__name__}: {str(exc)}"
                ),
            })

            # Preserve an old indexed version if extraction fails.
            report["preserve_sources"].append(source)
            continue

        if not content or not content.strip():
            report["empty_text_files"].append({
                "source": source,
                "reason": (
                    "No text could be extracted from this file."
                ),
            })

            # Keep the old indexed source when extraction returns
            # empty content; do not accidentally delete its chunks.
            report["preserve_sources"].append(source)
            continue

        documents.append({
            "source": source,
            "text": content,
        })

    report["preserve_sources"] = list(
        dict.fromkeys(report["preserve_sources"])
    )

    if return_report:
        return documents, report

    return documents

# ============================================================
# DOCUMENT CHUNKING
# ============================================================

def split_into_chunks(text):
    """
    Split documents by Markdown headings, paragraphs,
    and numbered rules.

    Long paragraphs are split into smaller overlapping chunks.
    """

    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")
    text = text.strip()

    if not text:
        return []

    # Remove lines containing only square brackets.
    text = re.sub(r"(?m)^\s*\[\s*$", "", text)
    text = re.sub(r"(?m)^\s*\]\s*$", "", text)

    # Normalize excessive blank lines.
    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    heading_pattern = re.compile(
        r"(?m)^(#{1,6}\s+.+?)\s*$"
    )

    matches = list(
        heading_pattern.finditer(text)
    )

    sections = []

    if not matches:
        sections.append(("Document", text))

    else:
        # Text before the first Markdown heading.
        preamble = text[:matches[0].start()].strip()

        if preamble:
            sections.append(("Document", preamble))

        # Separate each Markdown heading and its content.
        for index, match in enumerate(matches):

            title = (
                match.group(1)
                .strip()
                .lstrip("#")
                .strip()
            )

            body_start = match.end()

            if index + 1 < len(matches):
                body_end = matches[index + 1].start()
            else:
                body_end = len(text)

            body = text[body_start:body_end].strip()

            sections.append((title, body))

    chunks = []

    def add_text(section_title, content):
        content = " ".join(content.split()).strip()

        if not content:
            return

        # Keep the section name with each chunk so that
        # the context is understandable after retrieval.
        prefix = f"{section_title}: "

        max_body = max(
            100,
            CHUNK_SIZE - len(prefix)
        )

        if len(content) <= max_body:
            chunks.append(prefix + content)
            return

        start = 0

        while start < len(content):

            end = min(
                start + max_body,
                len(content)
            )

            piece = content[start:end].strip()

            if piece:
                chunks.append(prefix + piece)

            if end >= len(content):
                break

            start = max(
                start + 1,
                end - CHUNK_OVERLAP
            )

    for title, body in sections:

        if not body:
            continue

        paragraphs = [
            part.strip()
            for part in re.split(
                r"\n\s*\n",
                body
            )
            if part.strip()
        ]

        for paragraph in paragraphs:

            # Separate numbered rules, such as:
            # 1. Attendance must be at least 75%.
            # 2. Students may borrow 3 books.
            rules = re.split(
                r"(?m)(?=^\s*\d+\.\s+)",
                paragraph
            )

            rules = [
                rule.strip()
                for rule in rules
                if rule.strip()
            ]

            is_numbered = (
                rules
                and re.match(
                    r"^\s*\d+\.\s+",
                    rules[0]
                )
            )

            if len(rules) > 1 or is_numbered:

                for rule in rules:

                    rule = re.sub(
                        r"^\s*\d+\.\s+",
                        "",
                        rule
                    ).strip()

                    add_text(title, rule)

            else:
                add_text(title, paragraph)

    return [
        chunk
        for chunk in chunks
        if chunk.strip()
    ]


# ============================================================
# DATABASE CONNECTION HELPERS
# ============================================================

def _raw_connection():
    """
    Obtain a raw DBAPI connection from the SQLAlchemy engine.
    """

    return engine.raw_connection()


def _vector_literal(vector):
    """
    Convert a vector into PostgreSQL pgvector literal format.
    """

    values = np.asarray(
        vector,
        dtype=np.float32
    ).reshape(-1)

    if values.size != EMBEDDING_DIMENSIONS:
        raise ValueError(
            f"Expected {EMBEDDING_DIMENSIONS}-dimensional embedding, "
            f"received {values.size} dimensions."
        )

    if not np.isfinite(values).all():
        raise ValueError(
            "Embedding contains invalid numeric values."
        )

    return "[" + ",".join(
        str(float(value))
        for value in values
    ) + "]"


# ============================================================
# CREATE / MIGRATE VECTOR TABLE
# ============================================================

def _initialize_vector_table():
    """
    Create the pgvector table if it does not exist.

    Also adds document_hash to an existing table created
    by the older full-rebuild implementation.
    """

    raw = _raw_connection()

    try:
        conn = getattr(
            raw,
            "driver_connection",
            raw
        )

        with raw.cursor() as cursor:

            cursor.execute(
                "CREATE EXTENSION IF NOT EXISTS vector"
            )

            raw.commit()

            register_vector(conn)

            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {VECTOR_TABLE} (
                    id BIGSERIAL PRIMARY KEY,
                    source TEXT NOT NULL,
                    chunk_number INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    embedding VECTOR({EMBEDDING_DIMENSIONS}) NOT NULL,
                    document_hash TEXT NOT NULL DEFAULT '',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    CONSTRAINT uq_college_document_chunk
                        UNIQUE (source, chunk_number)
                )
            """)

            # Migrate an existing table safely.
            # Old rows receive an empty hash and will be
            # re-embedded on the first incremental indexing run.
            cursor.execute(f"""
                ALTER TABLE {VECTOR_TABLE}
                ADD COLUMN IF NOT EXISTS document_hash
                    TEXT NOT NULL DEFAULT ''
            """)

        raw.commit()

    except Exception:
        raw.rollback()
        raise

    finally:
        raw.close()


def _table_exists():
    """
    Check whether the vector table exists in public schema.
    """

    raw = _raw_connection()

    try:
        with raw.cursor() as cursor:

            cursor.execute(
                "SELECT to_regclass(%s)",
                (f"public.{VECTOR_TABLE}",)
            )

            result = cursor.fetchone()

            return bool(result and result[0])

    finally:
        raw.close()



def get_indexed_document_stats():
    """
    Return the number of indexed chunks for each source.

    Example:
    {
        "app/Document/uploads/college_rules.pdf": 14,
        "app/Document/uploads/notice.docx": 3
    }
    """

    if not _table_exists():
        return {}

    raw = _raw_connection()

    try:
        with raw.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT source, COUNT(*)
                FROM {VECTOR_TABLE}
                GROUP BY source
                ORDER BY source
                """
            )

            rows = cursor.fetchall()

        return {
            source: int(chunk_count)
            for source, chunk_count in rows
        }

    finally:
        raw.close()


def delete_indexed_document_source(source: str) -> int:
    """
    Delete chunks belonging to exactly one document source.

    This does not call Gemini and does not affect other
    documents in the vector table.
    """

    if not _table_exists():
        return 0

    raw = _raw_connection()

    try:
        with raw.cursor() as cursor:
            cursor.execute(
                f"""
                DELETE FROM {VECTOR_TABLE}
                WHERE source = %s
                """,
                (source,),
            )

            deleted_chunks = max(cursor.rowcount, 0)

        raw.commit()

        # Redis cache clear after successful document deletion
        _invalidate_rag_cache()

        return deleted_chunks

    except Exception:
        raw.rollback()
        raise

    finally:
        raw.close()


# ============================================================
# DOCUMENT HASHING
# ============================================================

def _document_hash(source, text):
    """
    Generate a SHA-256 fingerprint of a document and the
    settings used to index it.

    If document content, source path, embedding model,
    dimensions, chunk settings, or indexer version changes,
    the hash changes.
    """

    fingerprint = {
        "source": source,
        "text": text,
        "embedding_model": EMBEDDING_MODEL,
        "embedding_dimensions": EMBEDDING_DIMENSIONS,
        "chunk_size": CHUNK_SIZE,
        "chunk_overlap": CHUNK_OVERLAP,
        "indexer_version": INDEXER_VERSION,
    }

    serialized = json.dumps(
        fingerprint,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )

    return hashlib.sha256(
        serialized.encode("utf-8")
    ).hexdigest()


def _get_existing_document_hashes():
    """
    Return one stored hash per indexed document.

    Example:
        {
            "app/Document/college_rules.md": "abc123...",
            "app/Document/library_rules.txt": "def456..."
        }
    """

    if not _table_exists():
        return {}

    raw = _raw_connection()

    try:
        with raw.cursor() as cursor:

            cursor.execute(f"""
                SELECT
                    source,
                    MAX(document_hash)
                FROM {VECTOR_TABLE}
                GROUP BY source
            """)

            rows = cursor.fetchall()

            return {
                source: document_hash
                for source, document_hash in rows
            }

    finally:
        raw.close()


# ============================================================
# INCREMENTAL RAG INDEXING
# ============================================================

def build_rag_index():
    """
    Synchronize document chunks with PostgreSQL + pgvector.

    Unchanged documents:
        Keep existing embeddings.

    New documents:
        Generate embeddings and insert chunks.

    Modified documents:
        Generate new embeddings and replace old chunks.

    Deleted documents:
        Remove their chunks from the index.

    Embedding failure:
        Do not modify the existing index.

    Database failure:
        Roll back all changes made in this run.
    """

    # Step 1: Read current source documents.
    documents, load_report = load_documents(
        return_report=True
    )

    print("RAG document scan report:")
    print(json.dumps(load_report, indent=2, ensure_ascii=False))

    if not documents and (
        load_report["failed_files"]
        or load_report["empty_text_files"]
    ):
        raise RuntimeError(
            "No readable documents were extracted. "
            "Indexing stopped; inspect the report before retrying."
        )

    # Step 2: Ensure the vector table and hash column exist.
    _initialize_vector_table()

    # Step 3: Load the currently indexed document hashes.
    existing_hashes = _get_existing_document_hashes()

    # Safety guard: an accidentally empty document folder
    # should not erase a previously populated index.
    if (
        not documents
        and existing_hashes
        and not ALLOW_EMPTY_INDEX
    ):
        raise ValueError(
            "No readable, non-empty .txt, .md, .pdf, or .docx "
            "documents were found, "
            "but the existing RAG index contains documents. "
            "The existing index was preserved. If you intentionally "
            "want to clear the entire index, set "
            "RAG_ALLOW_EMPTY_INDEX=true in .env and run indexing again."
        )

    # Step 4: Split the documents into chunks.
    prepared_documents = []

    for document in documents:

        chunks = split_into_chunks(
            document["text"]
        )

        if chunks:
            prepared_documents.append(
                (document, chunks)
            )

    current_sources = {
        document["source"]
        for document, _ in prepared_documents
    }


    if (
        not prepared_documents
        and existing_hashes
        and not ALLOW_EMPTY_INDEX
    ):
        raise ValueError(
            "No usable document chunks were generated. "
            "The existing RAG index was preserved."
        )

    # Step 5: Find files that have been deleted, emptied,
    # or no longer produce any usable chunks.
    # Do not remove an existing source if its current file
    # exists but could not be read, or is a textless PDF.
    preserve_sources = set(
        load_report["preserve_sources"]
    )

    deleted_sources = (
        set(existing_hashes.keys())
        - current_sources
        - preserve_sources
    )

    # Step 6: Separate unchanged and changed documents.
    changed_documents = []
    unchanged_sources = []

    for document, chunks in prepared_documents:

        current_hash = _document_hash(
            document["source"],
            document["text"]
        )

        stored_hash = existing_hashes.get(
            document["source"]
        )

        if stored_hash == current_hash:
            unchanged_sources.append(
                document["source"]
            )

        else:
            changed_documents.append((
                document,
                chunks,
                current_hash
            ))

    # Step 7: Generate embeddings only for changed documents.
    #
    # IMPORTANT:
    # No existing database rows are deleted or modified
    # during this stage. If Gemini fails, the old index stays.
    client = (
        get_client()
        if changed_documents
        else None
    )

    records_to_insert = []

    for document, chunks, document_hash in changed_documents:

        for chunk_number, chunk in enumerate(
            chunks,
            start=1
        ):

            vector = embed_text(
                client,
                chunk,
                "RETRIEVAL_DOCUMENT"
            )

            records_to_insert.append({
                "source": document["source"],
                "chunk_number": chunk_number,
                "content": chunk,
                "embedding": _vector_literal(vector),
                "document_hash": document_hash,
            })

    # Step 8: Apply deletions and replacements in one
    # database transaction.
    #
    # If anything fails, rollback restores the previous index.
    raw = _raw_connection()

    try:
        conn = getattr(
            raw,
            "driver_connection",
            raw
        )

        register_vector(conn)

        with raw.cursor() as cursor:

            # Remove deleted documents.
            if deleted_sources:

                deleted_list = sorted(
                    deleted_sources
                )

                placeholders = ", ".join(
                    ["%s"] * len(deleted_list)
                )

                cursor.execute(
                    f"""
                    DELETE FROM {VECTOR_TABLE}
                    WHERE source IN ({placeholders})
                    """,
                    tuple(deleted_list),
                )

            # Remove previous chunks of changed documents.
            changed_sources = [
                document["source"]
                for document, _, _ in changed_documents
            ]

            if changed_sources:

                placeholders = ", ".join(
                    ["%s"] * len(changed_sources)
                )

                cursor.execute(
                    f"""
                    DELETE FROM {VECTOR_TABLE}
                    WHERE source IN ({placeholders})
                    """,
                    tuple(changed_sources),
                )

            # Insert new chunks for changed documents.
            if records_to_insert:

                cursor.executemany(
                    f"""
                    INSERT INTO {VECTOR_TABLE}
                        (
                            source,
                            chunk_number,
                            content,
                            embedding,
                            document_hash
                        )
                    VALUES (
                        %s,
                        %s,
                        %s,
                        %s::vector,
                        %s
                    )
                    """,
                    [
                        (
                            item["source"],
                            item["chunk_number"],
                            item["content"],
                            item["embedding"],
                            item["document_hash"],
                        )
                        for item in records_to_insert
                    ],
                )

            cursor.execute(
                f"SELECT COUNT(*) FROM {VECTOR_TABLE}"
            )

            total_chunks = int(
                cursor.fetchone()[0]
            )

        # Commit only after every change succeeds.
        raw.commit()

    except Exception:
        raw.rollback()
        raise

    finally:
        raw.close()


    # Step 9: Invalidate cached retrieval results only
    # after the PostgreSQL transaction succeeds.
    if changed_documents or deleted_sources:
        _invalidate_rag_cache()

    # Step 10: Return indexing statistics.
    return {
        "documents_loaded": len(documents),
        "documents_added_or_updated": len(changed_documents),
        "documents_unchanged": len(unchanged_sources),
        "documents_deleted": len(deleted_sources),
        "chunks_embedded_this_run": len(records_to_insert),
        "chunks_indexed_total": total_chunks,
        "storage": "PostgreSQL + pgvector",
        "table": VECTOR_TABLE,
        "sources": sorted(current_sources),
    }



# ============================================================
# RAG RETRIEVAL
# ============================================================

def retrieve_context_with_sources(
    question,
    top_k=TOP_K
):
    """
    Retrieve relevant chunks from pgvector.

    Returns:
        {
            "context": "...",
            "sources": [...]
        }

    If the table does not exist or no chunks meet the
    relevance threshold, return empty context and sources.
    """

    if not _table_exists():
        return {
            "context": "",
            "sources": []
        }

    if not question or not question.strip():
        return {
            "context": "",
            "sources": []
        }



    question = question.strip()
    top_k = max(1, int(top_k))

    cache_key = _rag_cache_key(
        question,
        top_k,
    )

    cached_result = _get_rag_cache(cache_key)

    if cached_result is not None:
        print("REDIS CACHE HIT")
        return cached_result

    print("REDIS CACHE MISS")


    client = get_client()

    # Generate an embedding for the user's question.
    query_vector = embed_text(
        client,
        question.strip(),
        "RETRIEVAL_QUERY"
    )

    query_literal = _vector_literal(
        query_vector
    )

    raw = _raw_connection()

    try:
        conn = getattr(
            raw,
            "driver_connection",
            raw
        )

        register_vector(conn)

        with raw.cursor() as cursor:

            cursor.execute(
                f"""
                SELECT
                    source,
                    chunk_number,
                    content,
                    1 - (embedding <=> %s::vector)
                        AS relevance_score
                FROM {VECTOR_TABLE}
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (
                    query_literal,
                    query_literal,
                    max(1, int(top_k)),
                ),
            )

            rows = cursor.fetchall()

    finally:
        raw.close()

    # Step 1: Apply the relevance threshold.
    selected = []

    for source, chunk_number, content, score in rows:

        score = float(score)

        if score >= MIN_RELEVANCE_SCORE:
            selected.append({
                "source": source,
                "chunk_number": int(chunk_number),
                "text": content,
                "relevance_score": round(
                    score,
                    4
                ),
            })

    # Step 2: No relevant context found.
    if not selected:
        result = {
            "context": "",
            "sources": [],
        }

        _set_rag_cache(cache_key, result)
        return result
    

    # Step 3: Build context and source citations.
    context_sections = []
    sources = []

    for item in selected:

        citation = (
            f"{item['source']} "
            f"(chunk {item['chunk_number']})"
        )

        context_sections.append(
            f"[Source: {citation}]\n"
            f"[Cosine similarity: "
            f"{item['relevance_score']:.4f}]\n"
            f"Content:\n"
            f"{item['text']}"
        )

        sources.append({
            "source": item["source"],
            "chunk_number": item["chunk_number"],
            "relevance_score": item["relevance_score"],
            "excerpt": item["text"][:300],
        })


    result = {
        "context": "\n\n---\n\n".join(context_sections),
        "sources": sources,
    }

    _set_rag_cache(cache_key, result)
    return result




# ============================================================
# BACKWARD COMPATIBILITY
# ============================================================

def retrieve_context(
    question,
    top_k=TOP_K
):
    """
    Compatibility helper for existing project code that
    expects only the context string.
    """

    result = retrieve_context_with_sources(
        question,
        top_k
    )

    return result["context"]