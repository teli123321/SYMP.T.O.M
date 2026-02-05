import streamlit as st
from openai import OpenAI

st.set_page_config(page_title="SYMP.T.O.M", layout="wide")

# ================= CSS DESIGN =================
# Defaults — modifiables via la barre latérale lorsque le consentement est donné
DEFAULT_BG = "#f9f9f9"
DEFAULT_SIDEBAR = "#1e4ed8"
DEFAULT_USER_BUBBLE = "#ff7aa2"
DEFAULT_USER_TEXT = "#ffffff"
DEFAULT_BOT_BUBBLE = "#ffffff"
DEFAULT_BOT_TEXT = "#000000"

# Le CSS sera injecté de façon dynamique plus bas (après les sélecteurs de couleur).

# ================= IA =================
client = OpenAI()
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
- Tu réponds UNIQUEMENT aux questions liées à la santé, aux symptômes, au corps humain ou à l'orientation médicale.
- Si une question n'est PAS liée à la santé (ex : couleurs, maths, culture générale, opinions), tu dois répondre exactement :
"Je suis conçu uniquement pour répondre à des questions liées à la santé."

Autres règles :
- Tu expliques de façon simple et rassurante.
- Tu peux reformuler une question médicale mal posée.
- Tu ne poses pas de diagnostic.
- Tu ne dois pas inventer de faits médicaux.
- Si l'information est incertaine, tu l'expliques honnêtement.
- Tu peux suggérer quel type de professionnel consulter.
- tu cites toujours tes sources parmi les suivantes : Mayo Clinic, NHS, WHO, Johns Hopkins.
- Tu es une aide informatique pour le système de santé canadien, pas un substitut à un avis médical professionnel.
Si tu n'es pas sûr que la question soit médicale, refuse de répondre.
Tu es un assistant médical pédagogique pour le grand public.
Tu n'es PAS un médecin.
tu peux répondre au forme de politesse et de salutations de base.
You must not request or store any personal data.
All data is ephemeral and must not be retained. : {list(SOURCES_AUTORISEES.keys())}.
"""


# ================= MÉMOIRE =================
if "conversation" not in st.session_state:
    st.session_state.conversation = [{"role":"system","content":SYSTEM_PROMPT}]

if "consent" not in st.session_state:
    st.session_state.consent = False

# ================= IA FUNCTION =================
def demander_ia(q):
    st.session_state.conversation.append({"role":"user","content":q})

    r = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=st.session_state.conversation,
        temperature=TEMPERATURE
    )

    rep = r.choices[0].message.content
    st.session_state.conversation.append({"role":"assistant","content":rep})

# ================= CONSENT SCREEN =================
if not st.session_state.consent:
    st.markdown("""
    ⚠️ **Consentement**

    Ce programme est un outil informatique.  
    Il ne remplace pas un médecin.

    En continuant, tu confirmes comprendre ces limites.
    """)
    
    if st.button("J'ai compris et je consens"):
        st.session_state.consent = True
        st.rerun()

else:

    # ================= APPEARANCE (couleurs) =================
    # Contrôles de couleur dans la barre latérale
    with st.sidebar:
        st.title("Apparence 🎨")
        bg_color = st.color_picker("Couleur de fond", DEFAULT_BG)
        sidebar_color = st.color_picker("Couleur barre latérale", DEFAULT_SIDEBAR)
        user_bubble = st.color_picker("Bulle utilisateur", DEFAULT_USER_BUBBLE)
        user_text = st.color_picker("Texte bulle utilisateur", DEFAULT_USER_TEXT)
        bot_bubble = st.color_picker("Bulle assistant", DEFAULT_BOT_BUBBLE)
        bot_text = st.color_picker("Texte bulle assistant", DEFAULT_BOT_TEXT)
        # Option de réinitialisation
        if st.button("Réinitialiser les couleurs"):
            # Pour réinitialiser, on recharge la page (les valeurs par défaut seront réappliquées)
            st.rerun()

    # Injecter le CSS dynamique basé sur les sélections
    st.markdown(f"""
    <style>
    body {{ background-color: {bg_color}; }}
    [data-testid="stSidebar"] {{ background: {sidebar_color}; }}
    .user-bubble {{
        background:{user_bubble};
        color:{user_text};
        padding:12px;
        border-radius:20px;
        margin:10px;
        max-width:60%;
        margin-left:auto;
    }}
    .bot-bubble {{
        background:{bot_bubble};
        color:{bot_text};
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

    # LEFT BAR
    with col1:
        st.image("https://static.vecteezy.com/system/resources/previews/037/761/852/non_2x/cute-pink-robot-with-buttons-vector.jpg", width=150)
        st.write("## SYMP.T.O.M")

    # CHAT AREA
    with col2:
        st.title("🧠 SYMP.T.O.M Assistant Médical")

        for msg in st.session_state.conversation:
            if msg["role"]=="user":
                st.markdown(f"<div class='user-bubble'>🤒 : {msg['content']}</div>", unsafe_allow_html=True)
            elif msg["role"]=="assistant":
                st.markdown(f"<div class='bot-bubble'>🤖 {msg['content']}</div>", unsafe_allow_html=True)

        # INPUT FORM
        with st.form("chat_form", clear_on_submit=True):
            user_input = st.text_input("Message")
            send = st.form_submit_button("Envoyer")

        if send and user_input:
            demander_ia(user_input)
            st.rerun()

        # DELETE BUTTON
        if st.button("🧨 Supprimer la conversation"):
            st.session_state.conversation = [{"role":"system","content":SYSTEM_PROMPT}]
            st.rerun()

