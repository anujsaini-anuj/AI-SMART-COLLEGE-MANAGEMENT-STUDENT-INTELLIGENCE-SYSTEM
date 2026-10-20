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


load_dotenv()


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
INDEXER_VERSION = "2"

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
# DOCUMENT LOADING: TXT, MARKDOWN, PDF, DOCX
# ============================================================

SUPPORTED_EXTENSIONS = {
    ".txt",
    ".md",
    ".pdf",
    ".docx",
}


def _extract_pdf_text(path):
    """
    Extract selectable text from a PDF.
    OCR is intentionally not used.
    """

    reader = PdfReader(str(path))

    if reader.is_encrypted:
        raise ValueError(
            "PDF is encrypted and cannot be read without a password."
        )

    page_texts = []

    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""

        if text.strip():
            page_texts.append(
                f"Page {page_number}:\n{text.strip()}"
            )

    return "\n\n".join(page_texts).strip()


def _extract_docx_text(path):
    """
    Extract text from DOCX paragraphs and tables.
    No OCR is used.
    """

    document = WordDocument(str(path))

    parts = []

    # Extract paragraphs.
    for paragraph in document.paragraphs:
        text = paragraph.text.strip()

        if text:
            parts.append(text)

    # Extract table contents.
    for table_number, table in enumerate(
        document.tables,
        start=1
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

    return "\n\n".join(parts).strip()


def load_documents(return_report=False):
    """
    Load supported files recursively from app/Document.

    Supported:
        .txt, .md, .pdf, .docx

    PDF:
        Extract selectable text only. No OCR.

    DOCX:
        Extract paragraphs and tables.

    Unsupported files and extraction failures are reported.

    Existing callers can still use load_documents() and
    receive only the document list. The indexer can call
    load_documents(return_report=True) to receive the report.
    """

    if not DOCUMENT_DIR.exists():
        raise FileNotFoundError(
            f"RAG document directory does not exist: {DOCUMENT_DIR}"
        )

    if not DOCUMENT_DIR.is_dir():
        raise NotADirectoryError(
            f"RAG document path is not a directory: {DOCUMENT_DIR}"
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

    for path in sorted(DOCUMENT_DIR.rglob("*")):

        if not path.is_file():
            continue

        report["files_scanned"] += 1

        source = path.relative_to(
            PROJECT_ROOT
        ).as_posix()

        extension = path.suffix.lower()

        # Report unsupported file formats instead of
        # silently skipping them.
        if extension not in SUPPORTED_EXTENSIONS:
            report["unsupported_files"].append({
                "source": source,
                "extension": extension or "(no extension)",
                "reason": "Unsupported file format",
            })
            continue

        report["supported_files"].append(source)

        try:
            if extension in {".txt", ".md"}:
                content = path.read_text(
                    encoding="utf-8-sig"
                ).strip()

            elif extension == ".pdf":
                content = _extract_pdf_text(path)

            elif extension == ".docx":
                content = _extract_docx_text(path)

            else:
                # Defensive fallback if supported formats
                # are extended in the future.
                continue

        except Exception as exc:
            report["failed_files"].append({
                "source": source,
                "reason": (
                    f"{type(exc).__name__}: {str(exc)}"
                ),
            })

            # Do not remove a previously indexed source merely
            # because its current file could not be read.
            report["preserve_sources"].append(source)
            continue

        if not content:
            report["empty_text_files"].append({
                "source": source,
                "reason": (
                    "No extractable text found. "
                    "If this is a scanned PDF, OCR would be "
                    "required, but OCR is disabled."
                    if extension == ".pdf"
                    else "The file contains no extractable text."
                ),
            })

            # A scanned/textless PDF must not cause an existing
            # indexed version of the same source to be deleted.
            if extension == ".pdf":
                report["preserve_sources"].append(source)

            continue

        documents.append({
            "source": source,
            "text": content,
        })

    # Remove duplicate preservation paths while retaining order.
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

    # Step 9: Return indexing statistics.
    return {
        "documents_loaded": len(documents),

        "documents_added_or_updated": len(
            changed_documents
        ),

        "documents_unchanged": len(
            unchanged_sources
        ),

        "documents_deleted": len(
            deleted_sources
        ),

        "chunks_embedded_this_run": len(
            records_to_insert
        ),

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
        return {
            "context": "",
            "sources": []
        }

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

    return {
        "context": "\n\n---\n\n".join(
            context_sections
        ),
        "sources": sources,
    }


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