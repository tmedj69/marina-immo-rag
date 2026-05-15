import yt_dlp
import json
import os

CHANNEL_URL = "https://www.youtube.com/@marinaimmodubai"

def fetch_playlist(url, label):
    """Récupère les vidéos d'une playlist/section spécifique."""
    ydl_opts = {
        "quiet": True,
        "extract_flat": True,
        "skip_download": True,
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        result = ydl.extract_info(url, download=False)

    videos = []
    entries = result.get("entries", [])
    
    # Parfois les entries sont imbriquées (playlist de playlists)
    for entry in entries:
        if entry is None:
            continue
        # Si c'est une sous-playlist, on l'ignore (cas des 3 sections qu'on a eu)
        if entry.get("_type") == "playlist":
            continue
        vid_id = entry.get("id")
        if not vid_id:
            continue
        videos.append({
            "id": vid_id,
            "title": entry.get("title"),
            "url": f"https://www.youtube.com/watch?v={vid_id}",
            "duration": entry.get("duration"),
            "upload_date": entry.get("upload_date"),
            "type": label  # "video", "live", ou "short"
        })
    
    return videos


if __name__ == "__main__":
    all_videos = []

    # On cible directement les 3 sections
    sections = [
        (f"{CHANNEL_URL}/streams", "live"),   # streams = lives
    ]

    for url, label in sections:
        print(f"Récupération des {label}s...")
        videos = fetch_playlist(url, label)
        videos = videos[:8]  # on garde que les 8 premiers (= les plus récents)
        print(f"  → {len(videos)} {label}s trouvés")
        all_videos.extend(videos)

    # Dédoublonnage par ID au cas où
    seen = set()
    unique_videos = []
    for v in all_videos:
        if v["id"] not in seen:
            seen.add(v["id"])
            unique_videos.append(v)

    os.makedirs("data", exist_ok=True)
    with open("data/videos.json", "w", encoding="utf-8") as f:
        json.dump(unique_videos, f, ensure_ascii=False, indent=2)

    print(f"\nTotal : {len(unique_videos)} vidéos → data/videos.json")
    for v in unique_videos[:5]:
        print(f"  - [{v['type']}] {v['title']}")