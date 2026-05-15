from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import NoTranscriptFound, TranscriptsDisabled
import json
import os
import time

def get_transcript(video_id, languages=["fr", "fr-FR", "en"]):
    try:
        ytt_api = YouTubeTranscriptApi()
        transcript_list = ytt_api.fetch(video_id, languages=languages)
        
        segments = [{"text": seg.text, "start": seg.start, "duration": seg.duration} 
                    for seg in transcript_list]
        
        full_text = " ".join([seg["text"] for seg in segments])
        
        return {
            "full_text": full_text,
            "segments": segments
        }
    
    except NoTranscriptFound:
        print(f"  ⚠️  Pas de transcription pour {video_id}")
        return None
    except TranscriptsDisabled:
        print(f"  ⚠️  Transcriptions désactivées pour {video_id}")
        return None
    except Exception as e:
        print(f"  ❌ Erreur pour {video_id}: {e}")
        return None


def fetch_all_transcripts(videos_path="data/videos.json"):
    with open(videos_path, "r", encoding="utf-8") as f:
        videos = json.load(f)

    success, failed = 0, 0

    for video in videos:
        vid_id = video["id"]
        output_path = f"transcripts/{vid_id}.json"

        # Skip si déjà récupéré (pratique pour reprendre après une interruption)
        if os.path.exists(output_path):
            print(f"  ✓ Déjà fait : {video['title'][:50]}")
            continue

        print(f"  → {video['title'][:50]}...")
        transcript = get_transcript(vid_id)

        if transcript:
            # On enrichit avec les métadonnées de la vidéo
            output = {
                "video_id": vid_id,
                "title": video["title"],
                "url": video["url"],
                "upload_date": video["upload_date"],
                **transcript
            }
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(output, f, ensure_ascii=False, indent=2)
            success += 1
        else:
            failed += 1

        time.sleep(0.5)  # petit délai pour ne pas spammer l'API YouTube

    print(f"\nTerminé : {success} OK, {failed} échecs")


if __name__ == "__main__":
    fetch_all_transcripts()