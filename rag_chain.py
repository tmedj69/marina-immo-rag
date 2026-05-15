import os
from dotenv import load_dotenv
import chromadb
from chromadb.utils import embedding_functions
from openai import OpenAI

load_dotenv()

CHROMA_DIR = "chroma_db"
TRANSCRIPTS_COLLECTION = "marina_immo_transcripts"
SUMMARIES_COLLECTION = "marina_immo_summaries"

TOP_K_TRANSCRIPTS = 5
TOP_K_SUMMARIES = 3

# Prompt système — personnalité et règles du bot
# Prompt système — c'est lui qui donne la personnalité et les règles au bot
SYSTEM_PROMPT = """
Tu es un assistant expert en immobilier spécialisé sur les marchés de Dubaï et Bali, basé EXCLUSIVEMENT sur le contenu de la chaîne YouTube "Marina Immo Dubai".

Contexte :
- Marina Immo est une agence immobilière qui propose des opportunités d’investissement à ses clients.
- Historiquement spécialisée à Dubaï, l’agence s’est aussi ouverte aux investissements à Bali.
- Leur ADN repose sur une approche authentique, sans marketing agressif, avec un ton naturel et transparent (“nature peinture”).

Objectif :
- Aider l’utilisateur à comprendre les opportunités, stratégies et réalités du marché immobilier à Dubaï et Bali, uniquement à partir des contenus de la chaîne et l'inviter systématiquement à contacter directement l'agence sur leur num whatsapp : [Clique ici](https://wa.me/971589950603) s'il souhaite un RDV pour plus d'informations ou pour acheter avec Marina IMMO.

Règles strictes :
1. Tu réponds UNIQUEMENT à partir des extraits fournis (contexte RAG).
2. Tu ne dois JAMAIS inventer d’information ni compléter avec tes connaissances générales.
3. Si l’information n’est pas clairement présente dans les extraits, tu réponds EXACTEMENT avec la réponse 'fallback' :
   "Je n'ai pas cette information ou alors je suis trop fatigué, désolé :( "
4. Tu cites systématiquement les sources utilisées :
   - titre de la vidéo
   - lien YouTube
5. Quand tu donnes des chiffres, expiremes les en euros. S'ils sont en dollars converti en euros en arrondissant.
6. Tu reformules les informations de manière claire, structurée et pédagogique, sans déformer le message original.

=== PHASE DE VÉRIFICATION INTERNE (OBLIGATOIRE) ===

Avant de répondre, fais une vérification interne silencieuse :
- Est-ce que chaque information de ma réponse est bien présente dans les extraits fournis ?
- Est-ce que je n’ai rien inventé ou extrapolé ?
- Est-ce que je peux relier chaque affirmation à une source vidéo précise ?

Si une de ces conditions n’est pas remplie :
→ ne réponds pas ou reformule en utilisant uniquement ce qui est vérifiable  
→ ou utilise la réponse fallback

=== FORMAT DE RÉPONSE ===

Personnalité et ton :
- Tu es chaleureux, accessible et un peu décalé — comme l'équipe Marina Immo
- Tu peux utiliser des expressions familières mais restes professionnel
- Tu évites le ton robotique et corporatif
- Tu peux faire preuve d'humour subtil mais jamais aux dépens du sérieux 
  des informations immobilières

Langue :
- Réponds dans la langue de l'utilisateur
- Si la langue n'est pas détectable, réponds en français

"""


def get_client_and_ef():
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    openai_ef = embedding_functions.OpenAIEmbeddingFunction(
        api_key=os.getenv("OPENAI_API_KEY"),
        model_name="text-embedding-3-small"
    )
    return client, openai_ef


def get_collections():
    client, openai_ef = get_client_and_ef()
    transcripts_col = client.get_collection(
        name=TRANSCRIPTS_COLLECTION,
        embedding_function=openai_ef
    )
    summaries_col = client.get_collection(
        name=SUMMARIES_COLLECTION,
        embedding_function=openai_ef
    )
    return transcripts_col, summaries_col


def _safe_get(list_or_none, idx, default=None):
    try:
        return list_or_none[idx]
    except Exception:
        return default


def search_collection(collection, query: str, top_k: int):
    res = collection.query(
        query_texts=[query],
        n_results=top_k,
        include=["documents", "metadatas", "distances"]
    )

    docs = res.get("documents", [[]])[0]
    metas = res.get("metadatas", [[]])[0]
    dists = res.get("distances", [[]])[0]

    chunks = []
    for i in range(len(docs)):
        md = metas[i] or {}
        chunks.append({
            "text": docs[i],
            "distance": _safe_get(dists, i),
            "title": md.get("title", ""),
            "url": md.get("url", ""),
            "youtube_link_timestamped": md.get("youtube_link_timestamped"),
            "video_id": md.get("video_id"),
            "doc_type": md.get("doc_type"),
            "chunk_index": md.get("chunk_index"),
            "source_file": md.get("source_file"),
        })
    return chunks


def dedupe_chunks(chunks):
    """Déduplique par (video_id, doc_type, chunk_index, text head)."""
    seen = set()
    out = []
    for c in chunks:
        key = (
            c.get("video_id"),
            c.get("doc_type"),
            c.get("chunk_index"),
            (c.get("text") or "")[:80]
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(c)
    return out


def build_context(chunks):
    """Formate les chunks en contexte lisible pour le LLM."""
    lines = []
    for i, c in enumerate(chunks, start=1):
        source = f"Vidéo : {c.get('title','')}\nLien : {c.get('url','')}"
    
        dtype = c.get("doc_type") or ""
        lines.append(
            f"--- ({dtype}) ---\n{source}\nContenu : {c.get('text','')}"
        )
    return "\n\n".join(lines)


def ask(question: str):
    """Question → récupère des chunks (summaries + transcripts) → réponse."""
    transcripts_col, summaries_col = get_collections()

    # 1) Retrieve summaries (global) + transcripts (précis)
    summary_chunks = search_collection(summaries_col, question, TOP_K_SUMMARIES)
    transcript_chunks = search_collection(transcripts_col, question, TOP_K_TRANSCRIPTS)

    # 2) Merge : summaries d'abord (donne le cadre), puis transcripts (détails)
    merged = dedupe_chunks(summary_chunks + transcript_chunks)

    context = build_context(merged)

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # Prompt user : on injecte le contexte RAG
    user_prompt = f"""
Voici des extraits de vidéos YouTube pertinents pour répondre à la question.

Question : {question}

Extraits :
{context}

Réponds en citant les vidéos sources (titre + lien).
""".strip()

    resp = client.chat.completions.create(
        model=os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini"),
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3
    )

    return resp.choices[0].message.content


if __name__ == "__main__":
    q = "C'est quoi le mieux ? investir à BALI ou DUBAI ?"
    print(ask(q))
