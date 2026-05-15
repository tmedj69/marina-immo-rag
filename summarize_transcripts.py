import json
import os
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv
import time

load_dotenv()

TRANSCRIPTS_DIR = "transcripts"
SUMMARIES_DIR = "summaries"
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def summarize_transcript(full_text, title):
    """
    Génère un résumé structuré de la vidéo.
    On envoie le texte en plusieurs blocs si trop long,
    puis on fait un résumé final des résumés.
    """
    words = full_text.split()
    blocks = []
    block_size = 3000
    
    for i in range(0, len(words), block_size):
        block = " ".join(words[i:i + block_size])
        blocks.append(block)
    
    print(f"  {len(blocks)} blocs à résumer...")
    
    # Étape 1 : résumé de chaque bloc
    block_summaries = []
    for i, block in enumerate(blocks):
        print(f"    Bloc {i+1}/{len(blocks)}...")
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """Tu analyses une transcription d'une vidéo YouTube de Marina Immo, 
une agence immobilière spécialisée à Dubaï et Bali.

Extrais et liste UNIQUEMENT les informations concrètes et factuelles :
- Chiffres, prix, rentabilités mentionnés
- Conseils et stratégies d'investissement
- Comparaisons de marchés (Dubaï vs Bali vs autres)
- Risques et opportunités évoqués
- Recommandations pratiques

Format : bullet points courts et précis.
Ne mets pas de chapeau introductif, va droit au but."""
                },
                {
                    "role": "user",
                    "content": f"Vidéo : {title}\n\nTranscription :\n{block}"
                }
            ],
            temperature=0.1
        )
        block_summaries.append(response.choices[0].message.content)
        time.sleep(0.3)
    
    # Étape 2 : résumé final qui consolide tous les blocs
    print(f"    Consolidation finale...")
    combined = "\n\n".join(block_summaries)
    
    final_response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": """Tu consolides des notes extraites d'une vidéo YouTube de Marina Immo.

Produis un résumé structuré avec ces sections :
## Contexte
(sujet principal de la vidéo, qui parle)

## Points clés
(les infos les plus importantes, chiffres, conseils)

## Marchés abordés
(Dubaï / Bali / autres — ce qui est dit sur chaque marché)

## Conseils pratiques
(recommandations concrètes pour les investisseurs)

## Mots clés
(liste de 10-15 mots clés pour la recherche sémantique)

Sois précis et factuel. Pas de remplissage."""
            },
            {
                "role": "user",
                "content": f"Vidéo : {title}\n\nNotes extraites :\n{combined}"
            }
        ],
        temperature=0.1
    )
    
    return final_response.choices[0].message.content


def process_all():
    os.makedirs(SUMMARIES_DIR, exist_ok=True)
    files = list(Path(TRANSCRIPTS_DIR).glob("*.json"))
    print(f"{len(files)} vidéos à résumer\n")
    
    for filepath in files:
        output_path = Path(SUMMARIES_DIR) / filepath.name
        
        if output_path.exists():
            print(f"✓ Déjà fait : {filepath.stem}")
            continue
        
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        print(f"→ {data['title'][:60]}...")
        summary = summarize_transcript(data["full_text"], data["title"])
        
        # On sauvegarde résumé + métadonnées
        output = {
            "video_id": data["video_id"],
            "title": data["title"],
            "url": data["url"],
            "upload_date": data.get("upload_date", ""),
            "summary": summary,
            "full_text": data["full_text"]  # on garde le brut aussi
        }
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        print(f"  ✓ Résumé sauvegardé\n")


if __name__ == "__main__":
    process_all()