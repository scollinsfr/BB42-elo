import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from datetime import datetime

# --- Connexion Google Sheets via secret ---
creds_json = st.secrets["GOOGLE_CREDS_JSON"]
creds_dict = json.loads(creds_json)
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
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
    if not values or len(values) == 0:
        return pd.DataFrame(columns=["Nom", "Sexe", "elo_SH", "elo_SD", "elo_DH", "elo_DD", "elo_DM"])
    df = pd.DataFrame(values[1:], columns=values[0])
    for col in ["elo_SH", "elo_SD", "elo_DH", "elo_DD", "elo_DM"]:
        if col not in df.columns:
            df[col] = 1000
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(1000).astype(int)
    return df

def update_player_field(player_name, field, new_value):
    values = ws_joueurs.get_all_values()
    if not values or len(values) < 1:
        return
    headers = values[0]
    try:
        col_index = headers.index(field) + 1
    except ValueError:
        st.error(f"Colonne {field} introuvable dans la feuille Joueurs.")
        return
    row_index = None
    for i, row in enumerate(values[1:], start=2):
        if len(row) > 0 and row[0] == player_name:
            row_index = i
            break
    if row_index:
        ws_joueurs.update_cell(row_index, col_index, new_value)
    else:
        st.error(f"Impossible de trouver la ligne pour le joueur {player_name}.")

def add_player(name, sexe):
    df = load_players()
    if name in df["Nom"].tolist():
        st.error("Ce joueur existe déjà !")
        return
    # Ajouter joueur avec ELO par défaut
    row = [name, sexe, 1000, 1000, 1000, 1000, 1000]
    ws_joueurs.append_row(row)
    st.success(f"✅ Joueur {name} ajouté.")

def remove_player(name):
    df = load_players()
    if name not in df["Nom"].tolist():
        st.error("Joueur introuvable !")
        return
    # trouver ligne et supprimer
    values = ws_joueurs.get_all_values()
    headers = values[0]
    row_index = None
    for i, row in enumerate(values[1:], start=2):
        if len(row) > 0 and row[0] == name:
            row_index = i
            break
    if row_index:
        ws_joueurs.delete_row(row_index)
        st.success(f"✅ Joueur {name} supprimé.")
    else:
        st.error("Impossible de supprimer le joueur.")


# --------------------------
# THEME (toggle sombre / clair en haut)
# --------------------------

dark = st.checkbox("🌙 Mode sombre", value=True)

dark_css = """
<style>
[data-testid="stAppViewContainer"] {
  background-color: #0d1117;
  color: #e6edf3;
}
h1, h2, h3 {
  color: #00aaff !important;
}
.stButton>button {
  background-color: #00aaff !important;
  color: white !important;
  border-radius: 8px;
  font-weight: 600;
}
a, p, span, label {
  color: #e6edf3 !important;
}
</style>
"""

light_css = """
<style>
[data-testid="stAppViewContainer"] {
  background-color: #ffffff;
  color: #111;
}
h1, h2, h3 {
  color: #0077cc !important;
}
.stButton>button {
  background-color: #0077cc !important;
  color: white !important;
  border-radius: 8px;
  font-weight: 600;
}
a, p, span, label {
  color: #111 !important;
}
</style>
"""

st.markdown(dark_css if dark else light_css, unsafe_allow_html=True)


# --------------------------
# PAGE
# --------------------------

st.image("logo.jpg", width=100)

st.title("⚙️ Administration Badminton ELO")

# --- Ajouter joueur ---
st.header("➕ Ajouter un joueur")
with st.form("add_form"):
    name_new = st.text_input("Nom du joueur")
    sexe_new = st.selectbox("Sexe", ["M", "F"])
    submitted = st.form_submit_button("Ajouter")
    if submitted:
        if not name_new.strip():
            st.error("Nom vide")
        else:
            add_player(name_new.strip(), sexe_new)

# --- Supprimer joueur ---
st.header("➖ Supprimer un joueur")
df_joueurs = load_players()
if not df_joueurs.empty:
    name_remove = st.selectbox("Choisir un joueur", df_joueurs["Nom"].tolist())
    if st.button("Supprimer"):
        remove_player(name_remove)
else:
    st.info("ℹ️ Aucun joueur disponible")

# --- Historique avec couleurs (Type de match) ---
st.header("📜 Historique des matchs")
values = ws_historique.get_all_values()
if len(values) > 1:
    df_hist = pd.DataFrame(values[1:], columns=values[0])

    def color_match(val):
        colors = {
            "SH": "background-color: #3399ff; color: white;",
            "DH": "background-color: #33cc33; color: white;",
            "SD": "background-color: #ff66b2; color: white;",
            "DD": "background-color: #ff9933; color: white;",
            "DM": "background-color: #9933ff; color: white;",
        }
        return colors.get(val, "")

    if "Type de match" in df_hist.columns:
        styled = df_hist.style.applymap(color_match, subset=["Type de match"])
        styled = styled.set_properties(**{"white-space": "nowrap"})
        st.dataframe(styled, use_container_width=True)
    else:
        st.dataframe(df_hist, use_container_width=True)
else:
    st.info("ℹ️ Aucun match enregistré")
