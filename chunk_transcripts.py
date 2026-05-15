import json
import os
from pathlib import Path

TRANSCRIPTS_DIR = "transcripts"
SUMMARIES_DIR = "summaries"
CHUNKS_DIR = "chunks"

CHUNK_SIZE = 300  # mots par chunk
OVERLAP = 50      # mots de chevauchement entre chunks


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = OVERLAP):
    """Découpe un texte en chunks de `chunk_size` mots avec `overlap` mots de chevauchement."""
    if not text:
        return []

    words = text.split()
    chunks = []
    start = 0

    # Sécurité : éviter boucle infinie si overlap >= chunk_size
    step = max(1, chunk_size - overlap)

    while start < len(words):
        end = start + chunk_size
        chunk_words = words[start:end]
        chunks.append(" ".join(chunk_words))
        start += step

    return chunks


def find_timestamp_for_chunk(chunk_start_word: int, words_per_second: float = 2.5):
    """Estime le timestamp (en secondes) à partir de la position du mot dans le texte."""
    return int(chunk_start_word / words_per_second)


def process_transcript(filepath: Path):
    """Chunk un transcript YouTube (clé attendue: full_text + url)."""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    video_id = data["video_id"]
    title = data.get("title", "")
    url = data.get("url", "")
    upload_date = data.get("upload_date", None)
    full_text = data.get("full_text", "")

    raw_chunks = chunk_text(full_text)
    chunks = []

    word_cursor = 0
    for i, chunk_text_content in enumerate(raw_chunks):
        chunk_word_count = len(chunk_text_content.split())
        timestamp_seconds = find_timestamp_for_chunk(word_cursor)
        yt_link = f"{url}&t={timestamp_seconds}" if url else None

        chunks.append({
            "chunk_id": f"{video_id}_transcript_chunk_{i}",
            "doc_type": "transcript",
            "video_id": video_id,
            "title": title,
            "url": url,
            "youtube_link_timestamped": yt_link,
            "upload_date": upload_date,
            "chunk_index": i,
            "total_chunks": len(raw_chunks),
            "text": chunk_text_content,
            "start_word": word_cursor,
            "source_file": filepath.name,
        })

        word_cursor += max(0, chunk_word_count - OVERLAP)

    return chunks


def process_summary(filepath: Path):
    """Chunk un résumé (clé attendue: summary)."""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    video_id = data["video_id"]
    title = data.get("title", "")
    url = data.get("url", "")
    upload_date = data.get("upload_date", None)
    summary_text = data.get("summary", "")

    raw_chunks = chunk_text(summary_text)
    chunks = []

    word_cursor = 0
    for i, chunk_text_content in enumerate(raw_chunks):
        chunk_word_count = len(chunk_text_content.split())

        chunks.append({
            "chunk_id": f"{video_id}_summary_chunk_{i}",
            "doc_type": "summary",
            "video_id": video_id,
            "title": title,
            "url": url,
            "upload_date": upload_date,
            "chunk_index": i,
            "total_chunks": len(raw_chunks),
            "text": chunk_text_content,
            "start_word": word_cursor,
            "source_file": filepath.name,
        })

        word_cursor += max(0, chunk_word_count - OVERLAP)

    return chunks


def main():
    os.makedirs(CHUNKS_DIR, exist_ok=True)

    transcript_chunks = []
    summary_chunks = []

    # 1) Transcripts
    transcript_files = list(Path(TRANSCRIPTS_DIR).glob("*.json"))
    for filepath in transcript_files:
        print(f"Chunking transcript : {filepath.name}...")
        chunks = process_transcript(filepath)
        transcript_chunks.extend(chunks)
        print(f" → {len(chunks)} chunks générés")

    # 2) Summaries
    summary_files = list(Path(SUMMARIES_DIR).glob("*.json"))
    for filepath in summary_files:
        print(f"Chunking summary : {filepath.name}...")
        chunks = process_summary(filepath)
        summary_chunks.extend(chunks)
        print(f" → {len(chunks)} chunks générés")

    # Sauvegardes séparées
    transcript_out = Path(CHUNKS_DIR) / "transcript_chunks.json"
    summary_out = Path(CHUNKS_DIR) / "summary_chunks.json"

    with open(transcript_out, "w", encoding="utf-8") as f:
        json.dump(transcript_chunks, f, ensure_ascii=False, indent=2)

    with open(summary_out, "w", encoding="utf-8") as f:
        json.dump(summary_chunks, f, ensure_ascii=False, indent=2)

    print(f"\nTranscripts : {len(transcript_chunks)} chunks → {transcript_out}")
    print(f"Summaries   : {len(summary_chunks)} chunks → {summary_out}")


if __name__ == "__main__":
    main()
