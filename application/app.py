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
 
# ================= RESTRICTION RÉSEAU (MONKEY-PATCH) =================
_original_request = requests.Session.request
 
def _restricted_request(self, method, url, **kwargs):
    """Intercepte chaque requête HTTP et bloque les domaines non autorisés."""
    domain = urlparse(url).netloc.split(":")[0]  # Retire le port si présent
    if domain not in DOMAINES_AUTORISES:
        
        raise PermissionError(f"🚫 Requête bloquée : domaine '{domain}' non autorisé.")
    return _original_request(self, method, url, **kwargs)
 
# Application du patch — fait une seule fois au démarrage du script
requests.Session.request = _restricted_request
 
 
# ================= FONCTIONS =================
def fetch_content_from_url_safe(url):
    """Récupère le texte uniquement depuis les sites autorisés, limité à 3000 caractères."""
    
    allowed_url = next(
        (allowed for allowed in SOURCES_AUTORISEES.values() if url.startswith(allowed)),
        None
    )
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
        
        return "\n".join(lines)[:300000000000000000000000]
    except PermissionError as e:
        
        st.warning(str(e))
        return ""
    except requests.RequestException as e:
     
        st.warning(f"Erreur lors de la récupération de la source : {e}")
        return ""
 
 
def choisir_source(question):
    """Choisit la source la plus pertinente selon les mots-clés de la question."""
    q = question.lower()
    if any(mot in q for mot in ["covid", "virus", "pandemic", "vaccin", "rendez-vous"]):
        return SOURCES_AUTORISEES.get("MSSS Québec") or SOURCES_AUTORISEES.get("Santé Canada")
    elif any(mot in q for mot in ["cancer", "diabetes", "maladie", "disease"]):
        return SOURCES_AUTORISEES.get("Santé Canada") or next(iter(SOURCES_AUTORISEES.values()))
    elif any(mot in q for mot in ["symptom", "traitement", "illness"]):
        return SOURCES_AUTORISEES.get("NHS UK") or next(iter(SOURCES_AUTORISEES.values()))
    else:
        return next(iter(SOURCES_AUTORISEES.values()))
 
 
# ================= PROMPT SYSTEM =================
SYSTEM_PROMPT = """
Tu es SYMP.T.O.M, un assistant médical pédagogique destiné au grand public au CANADA.
 
IMPORTANT :
- Tu n'es PAS un médecin.
- Tu ne poses pas de diagnostic.
- Tu ne prescris aucun traitement.
- Tu ne donnes pas d'instructions médicales personnalisées.
- TU DOIS DONNER DES CONSEILS DE BIEN ETRE C FULLL IMPORTANT!!!
 
RÈGLES OBLIGATOIRES :
1. Réponds uniquement aux questions liées à la santé.
2. Utilise exclusivement les informations fournies dans le contenu de la source autorisée.
3. Ne complète jamais avec des connaissances extérieures.
4. Cite toujours clairement la source utilisée à la fin de ta réponse.
5. Si l'information n'est pas disponible dans le contenu fourni, indique-le honnêtement.
6. Adopte un ton clair, rassurant et pédagogique.
7. Ne conserve aucune donnée personnelle.
8. Si la situation semble urgente ou grave, recommande de consulter un professionnel de santé ou le service d'urgence local (au Canada, composer le 911).
9. SOIS GENTIL, les personnes qui viennent te voir sont probablement en état de stress.
 
ADAPTATION CANADA :
- Toujours fournir les informations adaptées au Canada (ex: numéros d'urgence, recommandations locales).
- Ne jamais mentionner des numéros d'urgence d'autres pays.
- Se concentrer sur les ressources officielles canadiennes lorsqu'elles existent.
"""
 
# ================= STATE  =================
if "screen" not in st.session_state:
    st.session_state.screen = "welcome"
if "consent_given" not in st.session_state:
    st.session_state.consent_given = False
if "conversation" not in st.session_state:
    st.session_state.conversation = [{"role": "system", "content": SYSTEM_PROMPT}]
if "conversation_for_ia" not in st.session_state:
    st.session_state.conversation_for_ia = [{"role": "system", "content": SYSTEM_PROMPT}]
 
 
# ================= IA FUNCTION =================
def demander_ia(message):
    """Envoie un message à l'IA avec le contenu de la source choisie."""
    url = choisir_source(message)
    contenu = fetch_content_from_url_safe(url)
 
    st.session_state.conversation.append({"role": "user", "content": message})
 
    if contenu:
        internal_message = f"Question utilisateur: {message}\n\nContenu de la source ({url}):\n{contenu}"
    else:
        internal_message = f"Question utilisateur: {message}\n\nAucune information autorisée disponible pour cette source."
 
    st.session_state.conversation_for_ia.append({"role": "user", "content": internal_message})
 
    with st.spinner("🤔 SYMP.T.O.M réfléchit..."):
        time.sleep(1)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=st.session_state.conversation_for_ia,
            temperature=TEMPERATURE
        )
 
    reply = resp.choices[0].message.content
    source_name = next((k for k, v in SOURCES_AUTORISEES.items() if v == url), "Source inconnue")
    reply_with_source = f"{reply}\n\n(Source : {source_name})"
    st.session_state.conversation.append({"role": "assistant", "content": reply_with_source})
 
 
# ================= CSS =================
st.markdown("""
<style>
body {
    background: linear-gradient(135deg, #4facfe, #43e97b);
    font-family: 'Arial', sans-serif;
}
.card {
    max-width: 450px;
    margin: 30px auto;
    background: white;
    border-radius: 25px;
    padding: 25px 20px;
    box-shadow: 0px 10px 30px rgba(0,0,0,0.2);
}
.msg-user {
    background: #4facfe;
    color: white;
    padding: 10px 15px;
    border-radius: 20px 20px 5px 20px;
    margin: 6px 0;
    text-align: right;
    font-size: 15px;
}
.msg-bot {
    background: #e6fffa;
    color: #222;
    padding: 10px 15px;
    border-radius: 20px 20px 20px 5px;
    margin: 6px 0;
    text-align: left;
    font-size: 15px;
}
.consent-box {
    background: #fff3e6;
    border-left: 5px solid #ffa500;
    padding: 15px;
    margin-bottom: 20px;
    border-radius: 10px;
}
</style>
""", unsafe_allow_html=True)
 
 
# ================= SCREENS =================
if st.session_state.screen == "welcome":
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("<h1 style='text-align:center;'>🤖 SYMP.T.O.M</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align:center;color:#333;'>Assistant pédagogique en santé</h3>", unsafe_allow_html=True)
 
    st.markdown('<div class="consent-box">', unsafe_allow_html=True)
    st.markdown("""
    <strong>Important :</strong><br>
    - SYMP.T.O.M n'est pas un médecin et ne fournit pas de diagnostics.<br>
    - Les informations sont pédagogiques et basées sur des sources fiables canadiennes.<br>
    - En utilisant cette application, vous acceptez de recevoir des informations générales et de suivre les recommandations locales si nécessaire.
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
 
    if st.button("J'accepte et commencer"):
        st.session_state.consent_given = True
        st.session_state.screen = "chat"
        st.rerun()
 
    st.markdown('</div>', unsafe_allow_html=True)
 
elif st.session_state.screen == "chat" and st.session_state.consent_given:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("<h2 style='text-align:center;'>🤖 SYMP.T.O.M (Canada)</h2>", unsafe_allow_html=True)
 
    for msg in st.session_state.conversation:
        if msg["role"] == "user":
            st.markdown(f'<div class="msg-user">{msg["content"]}</div>', unsafe_allow_html=True)
        elif msg["role"] == "assistant":
            st.markdown(f'<div class="msg-bot">{msg["content"]}</div>', unsafe_allow_html=True)
 
    with st.form(key="input_form", clear_on_submit=True):
        cols = st.columns([5, 1])
        user_text = cols[0].text_input("", key="current_msg", placeholder="Pose ta question en santé…")
        send_button = cols[1].form_submit_button("📤")
 
        if send_button and user_text:
            demander_ia(user_text)
            st.rerun()
 
    st.markdown('</div>', unsafe_allow_html=True)