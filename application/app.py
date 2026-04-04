import os
import streamlit as st
from openai import OpenAI
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import time

# ================= CONFIG =================
st.set_page_config(page_title="SYMP.T.O.M", layout="centered")

api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    st.error("Clé OpenAI introuvable.")
    st.stop()

client = OpenAI(api_key=api_key)
TEMPERATURE = 0.3

# ================= SOURCES AUTORISÉES =================
SOURCES_AUTORISEES = {
    "MSSS Québec": "https://www.quebec.ca/sante/",
    "Santé Canada": "https://www.canada.ca/fr/sante-canada.html",
    "NHS UK": "https://www.nhs.uk/conditions/",
    "WHO": "https://www.who.int/health-topics",
    "Johns Hopkins": "https://www.hopkinsmedicine.org/health"
}

DOMAINES_AUTORISES = {urlparse(url).netloc for url in SOURCES_AUTORISEES.values()}

# ================= RESTRICTION RÉSEAU =================
_original_request = requests.Session.request

def _restricted_request(self, method, url, **kwargs):
    domain = urlparse(url).netloc.split(":")[0]
    if domain not in DOMAINES_AUTORISES:
        raise PermissionError(f"🚫 Requête bloquée : domaine '{domain}' non autorisé.")
    return _original_request(self, method, url, **kwargs)

requests.Session.request = _restricted_request

# ================= FONCTIONS =================
def fetch_content_from_url_safe(url):
    allowed_url = next((allowed for allowed in SOURCES_AUTORISEES.values() if url.startswith(allowed)), None)
    if not allowed_url:
        return ""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=5)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for script in soup(["script", "style"]):
            script.extract()
        text = soup.get_text(separator="\n")
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return "\n".join(lines)[:5000] 
    except Exception:
        return ""

def choisir_source(question):
    q = question.lower()
    if any(mot in q for mot in ["covid", "virus", "vaccin", "rendez-vous"]):
        return SOURCES_AUTORISEES["MSSS Québec"]
    elif any(mot in q for mot in ["cancer", "diabetes", "maladie"]):
        return SOURCES_AUTORISEES["Santé Canada"]
    return SOURCES_AUTORISEES["NHS UK"]

# ================= PROMPT SYSTEM =================
SYSTEM_PROMPT = """Tu es SYMP.T.O.M, un assistant médical pédagogique destiné au grand public au CANADA.

IMPORTANT :
- Réponds dans la langue qu'utilise l'utilisateur
- Tu n'es PAS un médecin.
- Tu ne poses pas de diagnostic.
- Tu ne prescris aucun traitement.
- Tu ne donnes pas d'instructions médicales personnalisées.
- TU DOIS DONNER DES CONSEILS DE BIEN ETRE C FULLL IMPORTANT!!!

RÈGLES OBLIGATOIRES :

0. RÉPOND DANS LA LANGUE DE L'UTILISATEUR
1. Réponds uniquement aux questions liées à la santé.
2. Utilise exclusivement les informations fournies dans le contenu de la source autorisée.
3. Ne complète jamais avec des connaissances extérieures.
4. Cite toujours clairement la source utilisée à la fin de ta réponse.
5. Si l'information n'est pas disponible dans le contenu fourni, indique-le honnêtement.
6. Adopte un ton clair, rassurant et pédagogique.
7. Ne conserve aucune donnée personnelle.
8. SEULEMENT si la situtation est urgente, recommande le 911.
9. SOIS GENTIL, les personnes qui viennent te voir sont probablement en état de stress.
10. Tu peux poser des questions pour en savoir plus ou pour avoir une meilleure idée du problème

ADAPTATION CANADA :
- Toujours fournir les informations adaptées au Canada (ex: numéros d'urgence, recommandations locales).
- Ne jamais mentionner des numéros d'urgence d'autres pays.
- Se concentrer sur les ressources officielles canadiennes lorsqu'elles existent."""

# ================= STATE =================
if "screen" not in st.session_state: st.session_state.screen = "welcome"
if "conversation" not in st.session_state: st.session_state.conversation = []

# ================= IA FUNCTION =================
def demander_ia(message):
    url = choisir_source(message)
    contenu = fetch_content_from_url_safe(url)
    
    st.session_state.conversation.append({"role": "user", "content": message})
    
    messages_ia = [{"role": "system", "content": SYSTEM_PROMPT}]
    ctx = f"Question: {message}\n\nSource ({url}):\n{contenu}" if contenu else message
    messages_ia.append({"role": "user", "content": ctx})

    with st.spinner("💭 Analyse en cours..."):
        resp = client.chat.completions.create(model="gpt-4o-mini", messages=messages_ia, temperature=TEMPERATURE)
    
    reply = resp.choices[0].message.content
    source_name = next((k for k, v in SOURCES_AUTORISEES.items() if v == url), "Source")
    st.session_state.conversation.append({"role": "assistant", "content": f"{reply}\n\n📌 *Source : {source_name}*"})

# ================= CSS =================
st.markdown("""
<style>
    .stApp { background: linear-gradient(180deg, #A18CD1 0%, #FBC2EB 100%); }
    .main-card {
        background: rgba(255, 255, 255, 0.7);
        backdrop-filter: blur(15px);
        border-radius: 40px;
        padding: 30px;
        box-shadow: 0 20px 40px rgba(0,0,0,0.1);
        border: 1px solid rgba(255,255,255,0.3);
    }
    .msg-user {
        background: #7F5AF0; color: white; padding: 15px 20px;
        border-radius: 25px 25px 5px 25px; margin: 10px 0 10px auto;
        width: fit-content; max-width: 80%;
    }
    .msg-bot {
        background: white; color: #16161a; padding: 15px 20px;
        border-radius: 25px 25px 25px 5px; margin: 10px auto 10px 0;
        width: fit-content; max-width: 80%;
    }
    .stButton>button {
        background: #7F5AF0 !important; color: white !important;
        border-radius: 30px !important; width: 100%; font-weight: bold;
    }
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ================= RENDU =================

if st.session_state.screen == "welcome":
    st.markdown('<div class="main-card">', unsafe_allow_html=True)
    st.markdown("<h1 style='text-align:center; color:white;'>👋 Bonjour ! / Welcome!</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; color:#555;'>SYMP.T.O.M est prêt à vous aider.</p>", unsafe_allow_html=True)
    
    # --- CORRECTION ICI (Ajout des guillemets et retrait du symbole invalide en dehors du texte) ---
    st.warning("""
    ⚠️ **Important :**
    - SYMP.T.O.M n'est pas un médecin et ne fournit pas de diagnostics.
    - Les informations sont pédagogiques et basées sur des sources fiables.
    - En cas d'urgence, contactez le 911 immédiatement.
    - Toutes les données sont suprimées à la fin de chaque échange           
    """)
    
    if st.button("COMMENCER"):
        st.session_state.screen = "chat"
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

elif st.session_state.screen == "chat":
    st.markdown('<div class="main-card">', unsafe_allow_html=True)
    st.markdown("<h2 style='text-align:center; color:#7F5AF0;'>SYMP.T.O.M</h2>", unsafe_allow_html=True)

    chat_container = st.container()
    with chat_container:
        for msg in st.session_state.conversation:
            div_class = "msg-user" if msg["role"] == "user" else "msg-bot"
            st.markdown(f'<div class="{div_class}">{msg["content"]}</div>', unsafe_allow_html=True)

    with st.form(key="chat_form", clear_on_submit=True):
        user_input = st.text_input("Posez votre question...", placeholder="Ex: J'ai mal à la tête...")
        submit = st.form_submit_button("ENVOYER")
        
        if submit and user_input:
            demander_ia(user_input)
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)