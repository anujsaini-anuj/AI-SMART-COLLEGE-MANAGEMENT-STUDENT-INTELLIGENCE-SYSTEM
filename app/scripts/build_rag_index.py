from app.services.rag_service import build_rag_index


if __name__ == "__main__":
    result = build_rag_index()

    print("RAG index created successfully.")
    print(result)
