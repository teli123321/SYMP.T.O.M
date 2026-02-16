import os
import streamlit as st
from openai import OpenAI
import requests
from bs4 import BeautifulSoup
import time

# ================= CONFIG =================
st.set_page_config(page_title="SYMP.T.O.M", layout="centered")

api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    st.error("Clé OpenAI introuvable.")
    st.stop()

client = OpenAI(api_key=api_key)
TEMPERATURE = 0.3

# ================= SOURCES =================
SOURCES_AUTORISEES = {
    "Mayo Clinic": "https://www.mayoclinic.org/diseases-conditions",
    "NHS": "https://www.nhs.uk/conditions/",
    "WHO": "https://www.who.int/health-topics",
    "Johns Hopkins": "https://www.hopkinsmedicine.org/health"
}

# ================= FONCTIONS =================
def fetch_content_from_url(url):
    """Récupère le texte du site si possible"""
    if url not in SOURCES_AUTORISEES.values():
        return ""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=5)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for script in soup(["script", "style"]):
            script.extract()
        return soup.get_text(separator="\n")[:3000]  # limiter pour l'IA
    except:
        return ""

def choisir_source(question):
    q = question.lower()
    if "covid" in q or "virus" in q or "pandemic" in q:
        return SOURCES_AUTORISEES.get("WHO") or next(iter(SOURCES_AUTORISEES.values()))
    elif "cancer" in q or "diabetes" in q or "disease" in q:
        return SOURCES_AUTORISEES.get("Mayo Clinic") or next(iter(SOURCES_AUTORISEES.values()))
    elif "symptom" in q or "treatment" in q or "illness" in q:
        return SOURCES_AUTORISEES.get("NHS") or next(iter(SOURCES_AUTORISEES.values()))
    else:
        return next(iter(SOURCES_AUTORISEES.values()))

SYSTEM_PROMPT = """
Tu es un assistant médical pédagogique pour le grand public.
Tu n'es PAS un médecin.

RÈGLE :
- Répond uniquement aux questions liées à la santé.
- Cite toujours la source utilisée.
- Forme polie et rassurante.
- Ne conserve aucune donnée personnelle.
"""

# ================= STATE =================
if "screen" not in st.session_state:
    st.session_state.screen = "welcome"

if "conversation" not in st.session_state:
    st.session_state.conversation = [{"role":"system","content":SYSTEM_PROMPT}]
if "conversation_for_ia" not in st.session_state:
    st.session_state.conversation_for_ia = [{"role":"system","content":SYSTEM_PROMPT}]

# ================= IA FUNCTION =================
def demander_ia(message):
    url = choisir_source(message)
    contenu = fetch_content_from_url(url)

    # --- Ajouter uniquement la question pour l'utilisateur ---
    st.session_state.conversation.append({"role": "user", "content": message})

    # --- Ajouter le message interne pour l'IA ---
    internal_message = f"Question utilisateur: {message}\nContenu de la source ({url}):\n{contenu}"
    st.session_state.conversation_for_ia.append({"role": "user", "content": internal_message})

    # --- Appel à l'IA ---
    with st.spinner("🤔 SYMP.T.O.M réfléchit..."):
        time.sleep(1)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=st.session_state.conversation_for_ia,
            temperature=TEMPERATURE
        )

    reply = resp.choices[0].message.content
    reply_with_source = f"{reply}\n\n(Source : {next((k for k,v in SOURCES_AUTORISEES.items() if v==url), 'Source inconnue')})"
    st.session_state.conversation.append({"role":"assistant","content":reply_with_source})

# ================= STYLE =================
st.markdown("""
<style>
body { background: linear-gradient(135deg, #4facfe, #43e97b); padding-top:0px !important; }
.main-container { display:flex; justify-content:center; align-items:center; height:85vh; }
.card { background:white; padding:40px; border-radius:30px; box-shadow:0 15px 40px rgba(0,0,0,0.15); width:420px; text-align:center; }
.big-title { font-size:28px; font-weight:600; margin-bottom:15px; }
.subtitle { color:#666; margin-bottom:30px; }
.stButton>button { background: linear-gradient(90deg, #4facfe, #43e97b); color:white; border:none; border-radius:25px; padding:10px 25px; font-size:16px; }
</style>
""", unsafe_allow_html=True)

# ================= SCREENS =================
if st.session_state.screen == "welcome":
    st.markdown('<div class="main-container"><div class="card">', unsafe_allow_html=True)
    st.markdown("<div style='font-size:50px;'>🤖</div>", unsafe_allow_html=True)
    st.markdown('<div class="big-title">SYMP.T.O.M</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="subtitle">
    Assistant pédagogique en santé.<br>
    Je vous aide à comprendre vos symptômes<br>
    à partir de sources médicales fiables.
    </div>
    """, unsafe_allow_html=True)
    if st.button("Commencer la consultation"):
        st.session_state.screen = "consent"
        st.rerun()
    st.markdown('</div></div>', unsafe_allow_html=True)

elif st.session_state.screen == "consent":
    st.markdown('<div class="main-container"><div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="big-title">⚠️ Consentement</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="subtitle">
    Cet outil ne remplace pas un médecin.<br>
    Il fournit des informations éducatives uniquement.
    </div>
    """, unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Retour"):
            st.session_state.screen = "welcome"
            st.rerun()
    with col2:
        if st.button("J'accepte"):
            st.session_state.screen = "chat"
            st.rerun()
    st.markdown('</div></div>', unsafe_allow_html=True)

elif st.session_state.screen == "chat":
    st.markdown("## 🧠 SYMP.T.O.M")
    chat_container = st.container()
    with chat_container:
        for msg in st.session_state.conversation:
            if msg["role"]=="user":
                st.markdown(f"**Vous :** {msg['content']}")
            elif msg["role"]=="assistant":
                st.markdown(f"**SYMP.T.O.M :** {msg['content']}")
    user_input = st.text_input("Votre message")
    if st.button("Envoyer") and user_input:
        demander_ia(user_input)
        st.rerun()
    if st.button("Retour à l'accueil"):
        st.session_state.screen = "welcome"
        st.session_state.conversation = [{"role":"system","content":SYSTEM_PROMPT}]
        st.session_state.conversation_for_ia = [{"role":"system","content":SYSTEM_PROMPT}]
        st.rerun()
