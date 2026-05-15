import json
import os
from dotenv import load_dotenv
import chromadb
from chromadb.utils import embedding_functions

load_dotenv()

TRANSCRIPT_CHUNKS_PATH = "chunks/transcript_chunks.json"
SUMMARY_CHUNKS_PATH = "chunks/summary_chunks.json"

CHROMA_DIR = "chroma_db"

TRANSCRIPTS_COLLECTION = "marina_immo_transcripts"
SUMMARIES_COLLECTION = "marina_immo_summaries"

BATCH_SIZE = 50  # on envoie 50 chunks à la fois à OpenAI


def load_chunks(path: str):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def upsert_in_batches(collection, chunks):
    total = len(chunks)
    for i in range(0, total, BATCH_SIZE):
        batch = chunks[i:i + BATCH_SIZE]

        ids = [c["chunk_id"] for c in batch]
        documents = [c["text"] for c in batch]

        metadatas = []
        for c in batch:
            md = {
                "doc_type": c.get("doc_type"),
                "video_id": c.get("video_id"),
                "title": c.get("title"),
                "url": c.get("url"),
                "upload_date": c.get("upload_date", ""),
                "chunk_index": c.get("chunk_index"),
                "total_chunks": c.get("total_chunks"),
                "source_file": c.get("source_file"),
            }
            # présent uniquement pour les transcripts
            if c.get("youtube_link_timestamped"):
                md["youtube_link_timestamped"] = c.get("youtube_link_timestamped")

            metadatas.append(md)

        collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
        print(f"  {min(i + BATCH_SIZE, total)}/{total} chunks embedés...")


def embed_and_store():
    print("Chargement des chunks...")
    transcript_chunks = load_chunks(TRANSCRIPT_CHUNKS_PATH)
    summary_chunks = load_chunks(SUMMARY_CHUNKS_PATH)

    print(f"{len(transcript_chunks)} transcript chunks chargés")
    print(f"{len(summary_chunks)} summary chunks chargés")

    # Client ChromaDB local (stocké dans chroma_db/)
    client = chromadb.PersistentClient(path=CHROMA_DIR)

    # Fonction d'embedding OpenAI
    openai_ef = embedding_functions.OpenAIEmbeddingFunction(
        api_key=os.getenv("OPENAI_API_KEY"),
        model_name="text-embedding-3-small"  # rapide et pas cher
    )

    # 1) Collection transcripts
    transcripts_col = client.get_or_create_collection(
        name=TRANSCRIPTS_COLLECTION,
        embedding_function=openai_ef,
        metadata={"hnsw:space": "cosine"}
    )
    print(f"Collection '{TRANSCRIPTS_COLLECTION}' prête")

    # 2) Collection summaries
    summaries_col = client.get_or_create_collection(
        name=SUMMARIES_COLLECTION,
        embedding_function=openai_ef,
        metadata={"hnsw:space": "cosine"}
    )
    print(f"Collection '{SUMMARIES_COLLECTION}' prête")

    if transcript_chunks:
        print("\nEmbedding + upsert transcripts...")
        upsert_in_batches(transcripts_col, transcript_chunks)

    if summary_chunks:
        print("\nEmbedding + upsert summaries...")
        upsert_in_batches(summaries_col, summary_chunks)

    print(f"\nTerminé ! Base vectorielle sauvegardée dans {CHROMA_DIR}/")


if __name__ == "__main__":
    embed_and_store()
