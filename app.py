import random
import streamlit as st

from rag_chain import ask

print("### APP.PY LOADED ###", flush=True)

# Paths
LOGO_PATH = "img/marina_immo.png" 

# Config de la page
st.set_page_config(
    page_title="Marina Immo - IAcine",
    page_icon=LOGO_PATH,  # favicon
    layout="centered",
)

# CSS léger (optionnel)
st.markdown(
    """
<style>
/* Largeur confortable */
.block-container { max-width: 820px; }
</style>
""",
    unsafe_allow_html=True,
)

# Header
col1, col2 = st.columns([0.13, 0.87], gap="small")
with col1:
    st.image(LOGO_PATH, width=64)
with col2:
    st.markdown("## Marina Immo — IAcine pour vous servir")
    st.markdown("*Posez-moi vos questions sur l'immobilier à Dubaï et Bali*")

st.divider()

# Historique de conversation
if "messages" not in st.session_state:
    st.session_state.messages = []

# Message de bienvenue (une seule fois)
if "welcomed" not in st.session_state:
    accroches = [
        "Hello los amigos !👋",
        "Salut à toussssssaaaaa !👋",
    ]
    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": f"{random.choice(accroches)} Je suis IAcine, l'assistant de Marina Immo. Pose-moi une question sur l'immobilier à Dubaï ou Bali !",
        }
    )
    st.session_state.welcomed = True

# Affichage de l'historique
for message in st.session_state.messages:
    avatar = LOGO_PATH if message["role"] == "assistant" else None
    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"])

# Input utilisateur
if question := st.chat_input("Votre question sur l'immobilier à Dubaï ou Bali..."):
    
    print(f"[USER QUESTION] {question}")  

    # Ajout question
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    # Génération réponse
    with st.chat_message("assistant", avatar=LOGO_PATH):
        with st.spinner("Recherche dans les vidéos..."):
            answer = ask(question)

        st.markdown(answer)
        print(f"[BOT ANSWER] {answer}")

    # Sauvegarde réponse
    st.session_state.messages.append({"role": "assistant", "content": answer})
