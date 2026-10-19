
import json
import os
from pathlib import Path

import numpy as np
from dotenv import load_dotenv
from google import genai
from google.genai import types


load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DOCUMENT_DIR = PROJECT_ROOT / "app" / "Document"
INDEX_PATH = PROJECT_ROOT / "data" / "rag_index.json"

EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIMENSIONS = 768

CHUNK_SIZE = 1200
CHUNK_OVERLAP = 200
TOP_K = 4


def get_client():
    """Create Gemini client using the configured API key."""
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise ValueError("GEMINI_API_KEY is not configured")

    return genai.Client(api_key=api_key)


def load_documents():
    """Load supported text and Markdown files."""
    DOCUMENT_DIR.mkdir(parents=True, exist_ok=True)

    documents = []

    for path in sorted(DOCUMENT_DIR.rglob("*")):
        if not path.is_file():
            continue

        if path.suffix.lower() not in {".txt", ".md"}:
            continue

        text = path.read_text(encoding="utf-8").strip()

        if text:
            documents.append({
                "source": str(path.relative_to(PROJECT_ROOT)),
                "text": text
            })

    return documents


def split_into_chunks(text):
    """Split text into overlapping chunks."""
    text = " ".join(text.split())

    if not text:
        return []

    chunks = []
    start = 0

    while start < len(text):
        end = min(start + CHUNK_SIZE, len(text))
        chunks.append(text[start:end])

        if end == len(text):
            break

        start = end - CHUNK_OVERLAP

    return chunks


def embed_text(client, text, task_type):
    """Generate one embedding vector."""
    response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
        config=types.EmbedContentConfig(
            task_type=task_type,
            output_dimensionality=EMBEDDING_DIMENSIONS
        )
    )

    return response.embeddings[0].values


def build_rag_index():
    """
    Read knowledge documents, create embeddings,
    and save the index locally.
    """
    client = get_client()
    documents = load_documents()

    if not documents:
        raise ValueError(
            "No .txt or .md documents found in Document/"
        )

    records = []

    for document in documents:
        chunks = split_into_chunks(document["text"])

        for chunk in chunks:
            vector = embed_text(
                client,
                chunk,
                "RETRIEVAL_DOCUMENT"
            )

            records.append({
                "source": document["source"],
                "text": chunk,
                "embedding": vector
            })

    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)

    temporary_path = INDEX_PATH.with_suffix(".tmp")

    temporary_path.write_text(
        json.dumps(records, ensure_ascii=False),
        encoding="utf-8"
    )

    temporary_path.replace(INDEX_PATH)

    return {
        "documents_loaded": len(documents),
        "chunks_indexed": len(records),
        "index_path": str(INDEX_PATH)
    }






def retrieve_context(question, top_k=TOP_K):
    """
    Retrieve the most relevant college document chunks.
    Print similarity scores to help debug retrieval.
    """
    if not INDEX_PATH.exists():
        print("RAG index not found. Build the index first.")
        return ""

    records = json.loads(
        INDEX_PATH.read_text(encoding="utf-8")
    )

    if not records:
        print("RAG index is empty.")
        return ""

    client = get_client()

    query_vector = np.array(
        embed_text(client, question, "RETRIEVAL_QUERY"),
        dtype=np.float32
    )

    query_norm = np.linalg.norm(query_vector)

    if query_norm == 0:
        print("Query embedding has zero length.")
        return ""

    scored_chunks = []

    for record in records:
        vector = np.array(
            record["embedding"],
            dtype=np.float32
        )

        vector_norm = np.linalg.norm(vector)

        if vector_norm == 0:
            continue

        similarity = float(
            np.dot(query_vector, vector)
            / (query_norm * vector_norm)
        )

        scored_chunks.append((
            similarity,
            record["source"],
            record["text"]
        ))

    scored_chunks.sort(
        key=lambda item: item[0],
        reverse=True
    )

    print(f"\nRAG query: {question}")
    print("Top retrieval results:")

    for score, source, text in scored_chunks[:top_k]:
        print(f"\nSimilarity: {score:.4f}")
        print(f"Source: {source}")
        print(f"Text: {text[:300]}")

    if not scored_chunks:
        print("No valid chunks found.")
        return ""

    sections = []

    for score, source, text in scored_chunks[:top_k]:
        sections.append(
            f"Source: {source}\n"
            f"Relevance score: {score:.3f}\n"
            f"Content:\n{text}"
        )

    return "\n\n---\n\n".join(sections)
