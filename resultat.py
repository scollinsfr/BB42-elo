import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from datetime import datetime

# --- Connexion Google Sheets via secret ---
creds_json = st.secrets["GOOGLE_CREDS_JSON"]
creds_dict = json.loads(creds_json)
scope = ["https://spreadsheets.google.com/feeds",'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

# Feuilles
sheet = client.open("BadmintonElo")
ws_joueurs = sheet.worksheet("Joueurs")
ws_historique = sheet.worksheet("Historique")


# --------------------------
# FONCTIONS UTILITAIRES
# --------------------------

def load_players():
    values = ws_joueurs.get_all_values()
    df = pd.DataFrame(values[1:], columns=values[0])
    # Convertir les colonnes ELO en int
    for col in ["elo_SH", "elo_SD", "elo_DH", "elo_DD", "elo_DM"]:
        df[col] = df[col].astype(int)
    return df

def save_players(df):
    ws_joueurs.clear()
    ws_joueurs.append_row(df.columns.tolist())
    for row in df.values.tolist():
        ws_joueurs.append_row(row)

def update_elo(player, column, new_elo):
    df = load_players()
    df.loc[df["Nom"] == player, column] = new_elo
    save_players(df)

def add_match(date, type_match, joueurs, score, elo_avant, elo_apres):
    row = [date, type_match, joueurs, score, elo_avant, elo_apres]
    ws_historique.append_row(row)


# --------------------------
# STREAMLIT UI
# --------------------------

# Style personnalisé (même que admin.py)
st.markdown(
    """
    <style>
    .main {
        background-color: #0d1117;
        color: #e6edf3;
    }
    h1, h2, h3 {
        color: #00aaff !important;
    }
    .stButton button {
        background-color: #00aaff !important;
        color: white !important;
        border-radius: 8px;
        font-weight: bold;
    }
    .stDataFrame {
        border: 2px solid #00aaff;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Logo (même emplacement que admin.py)
logo_url = ""  # exemple: "https://tonsite.com/logo.png"
if logo_url:
    st.image(logo_url, width=200)

st.title("🏸 Résultats Badminton ELO")

# Charger joueurs
df_joueurs = load_players()

# Saisie d’un match
st.header("➕ Enregistrer un match")

with st.form("match_form"):
    type_match = st.selectbox("Type de match", ["SH", "SD", "DH", "DD", "DM"])
    joueurs = st.multiselect("Joueurs", df_joueurs["Nom"].tolist(), max_selections=4)
    score = st.text_input("Score (ex: 21-15 / 19-21 / 21-18)")
    submitted = st.form_submit_button("Enregistrer le match")

    if submitted:
        if len(joueurs) < 2:
            st.error("⚠️ Sélectionne au moins 2 joueurs")
        elif not score.strip():
            st.error("⚠️ Le score est obligatoire")
        else:
            date = datetime.now().strftime("%Y-%m-%d %H:%M")
            # Placeholder pour les elos (à calculer selon ton système)
            elo_avant = "TODO"
            elo_apres = "TODO"
            add_match(date, type_match, ", ".join(joueurs), score, elo_avant, elo_apres)
            st.success("✅ Match enregistré !")

# Historique
st.header("📜 Historique des matchs")
values = ws_historique.get_all_values()
if len(values) > 1:
    df_hist = pd.DataFrame(values[1:], columns=values[0])
    st.dataframe(df_hist, use_container_width=True)
else:
    st.info("ℹ️ Aucun match enregistré")
