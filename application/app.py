import streamlit as st
from openai import OpenAI

# Vérifie que le secret est bien lu
if "openai" not in st.secrets or "api_key" not in st.secrets["openai"]:
    st.error("❌ Clé OpenAI introuvable ! Vérifie tes secrets Streamlit.")
    st.stop()

# Initialise le client OpenAI avec la clé du secret
client = OpenAI(api_key=st.secrets["openai"]["api_key"])


st.set_page_config(page_title="SYMP.T.O.M", layout="wide")

# ================= COULEURS FIXES =================
DEFAULT_BG = "#f9f9f9"
DEFAULT_SIDEBAR = "#1e4ed8"
DEFAULT_USER_BUBBLE = "#ff7aa2"
DEFAULT_USER_TEXT = "#ffffff"
DEFAULT_BOT_BUBBLE = "#ffffff"
DEFAULT_BOT_TEXT = "#000000"

# ================= IA =================
import streamlit as st
from openai import OpenAI

# Crée le client OpenAI en utilisant la clé stockée sur Streamlit Cloud
client = OpenAI(api_key=st.secrets["openai"]["api_key"])
TEMPERATURE = 0.3

SOURCES_AUTORISEES = {
    "Mayo Clinic": "https://www.mayoclinic.org/diseases-conditions",
    "NHS": "https://www.nhs.uk/conditions/",
    "WHO": "https://www.who.int/health-topics",
    "Johns Hopkins": "https://www.hopkinsmedicine.org/health"
}

SYSTEM_PROMPT = f"""
Tu es un assistant médical pédagogique pour le grand public.
Tu n'es PAS un médecin.

RÈGLE ABSOLUE :
- Répond UNIQUEMENT aux questions liées à la santé.
- Ne pose qu'UNE SEULE question de clarification à la fois.
- Après chaque réponse de l'utilisateur, attends sa réponse avant de poser la prochaine question.
- Si une question est de type Yes/No, attends que l'utilisateur réponde Oui ou Non.
- Cite toujours les sources : {list(SOURCES_AUTORISEES.keys())}.
- Forme polie et rassurante.
- Ne conserve aucune donnée personnelle.
"""

# ================= MÉMOIRE =================
if "conversation" not in st.session_state:
    st.session_state.conversation = [{"role":"system","content":SYSTEM_PROMPT}]
if "consent" not in st.session_state:
    st.session_state.consent = False
if "last_question_type" not in st.session_state:
    st.session_state.last_question_type = "text"  # "text" ou "yesno"
if "last_yesno_question" not in st.session_state:
    st.session_state.last_yesno_question = ""

# ================= IA FUNCTION =================
def demander_ia(q, yesno_response=False):
    """
    q : texte à envoyer à l'IA
    yesno_response : si True, on envoie la réponse Oui/Non à la question YesNo précédente
    """
    if yesno_response:
        # On reformule la réponse pour que l'IA sache à quelle question ça correspond
        full_message = f"Question: {st.session_state.last_yesno_question}\nRéponse: {q}"
    else:
        full_message = q

    st.session_state.conversation.append({"role":"user","content":full_message})

    with st.spinner("🤔 SYMP.T.O.M réfléchit..."):
        time.sleep(1)
        r = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=st.session_state.conversation,
            temperature=TEMPERATURE
        )

    rep = r.choices[0].message.content
    st.session_state.conversation.append({"role":"assistant","content":rep})

    # Détection simple de question Yes/No (1 question à la fois)
    lower_rep = rep.lower()
    if any(keyword in lower_rep for keyword in ["oui ?", "non ?", "as-tu", "ressens-tu", "avez-vous"]):
        st.session_state.last_question_type = "yesno"
        st.session_state.last_yesno_question = rep
    else:
        st.session_state.last_question_type = "text"
        st.session_state.last_yesno_question = ""

# ================= CONSENT SCREEN =================
if not st.session_state.consent:
    st.markdown("""
    ⚠️ **Consentement**
    Ce programme est un outil informatique.  
    Il ne remplace pas un médecin.
    """)
    if st.button("J'ai compris et je consens"):
        st.session_state.consent = True
        st.rerun()
else:
    # ================= CSS FIXE =================
    st.markdown(f"""
    <style>
    body {{ background-color: {DEFAULT_BG}; }}
    [data-testid="stSidebar"] {{ background: {DEFAULT_SIDEBAR}; }}
    .user-bubble {{
        background:{DEFAULT_USER_BUBBLE};
        color:{DEFAULT_USER_TEXT};
        padding:12px;
        border-radius:20px;
        margin:10px;
        max-width:60%;
        margin-left:auto;
    }}
    .bot-bubble {{
        background:{DEFAULT_BOT_BUBBLE};
        color:{DEFAULT_BOT_TEXT};
        padding:12px;
        border-radius:20px;
        margin:10px;
        max-width:60%;
        box-shadow:0px 4px 10px rgba(0,0,0,0.05);
    }}
    .stTextInput>div>div>input {{
        border-radius:20px;
        padding:12px;
    }}
    </style>
    """, unsafe_allow_html=True)

    # ================= LAYOUT =================
    col1, col2 = st.columns([1,4])

    with col1:
        st.image("https://static.vecteezy.com/system/resources/previews/037/761/852/non_2x/cute-pink-robot-with-buttons-vector.jpg", width=150)
        st.write("## SYMP.T.O.M")

    with col2:
        st.title("🧠 SYMP.T.O.M Assistant Médical")

        for msg in st.session_state.conversation:
            if msg["role"]=="user":
                st.markdown(f"<div class='user-bubble'>🤒 : {msg['content']}</div>", unsafe_allow_html=True)
            elif msg["role"]=="assistant":
                st.markdown(f"<div class='bot-bubble'>🤖 {msg['content']}</div>", unsafe_allow_html=True)

        # INPUT OU BOUTONS YES/NO
        if st.session_state.last_question_type == "text":
            with st.form("chat_form", clear_on_submit=True):
                user_input = st.text_input("Message")
                send = st.form_submit_button("Envoyer")
            if send and user_input:
                demander_ia(user_input)
                st.rerun()
        else:
            col_yes, col_no = st.columns(2)
            with col_yes:
                if st.button("✅ Oui"):
                    demander_ia("Oui", yesno_response=True)
                    st.rerun()
            with col_no:
                if st.button("❌ Non"):
                    demander_ia("Non", yesno_response=True)
                    st.rerun()

        # DELETE BUTTON
        if st.button("🧨 Supprimer la conversation"):
            st.session_state.conversation = [{"role":"system","content":SYSTEM_PROMPT}]
            st.session_state.last_question_type = "text"
            st.session_state.last_yesno_question = ""
            st.rerun()
