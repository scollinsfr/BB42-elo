import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from datetime import datetime

# --------------------------
# CONFIGURATION GOOGLE SHEETS
# --------------------------

# Charger credentials depuis Streamlit Secrets
creds_json = st.secrets["GOOGLE_CREDS_JSON"]
creds_dict = json.loads(creds_json)

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
client = gspread.service_account_from_dict(creds_dict, scopes=scope)

# Noms des feuilles
PLAYERS_SHEET_NAME = "BadmintonElo"   # Feuille joueurs
HISTORY_SHEET_NAME = "Historique"     # Feuille historique

# Charger ou créer feuilles
try:
    sheet_players = client.open(PLAYERS_SHEET_NAME).sheet1
except gspread.SpreadsheetNotFound:
    # Créer une nouvelle feuille si non existante
    sheet_players = client.create(PLAYERS_SHEET_NAME).sheet1
    sheet_players.append_row(["Nom", "Sexe", "elo_SH", "elo_SD", "elo_DH", "elo_DD", "elo_DM"])

try:
    sheet_history = client.open(HISTORY_SHEET_NAME).sheet1
except gspread.SpreadsheetNotFound:
    sheet_history = client.create(HISTORY_SHEET_NAME).sheet1
    sheet_history.append_row(["Date", "TypeMatch", "Equipe1", "Equipe2", "Gagnant", "ELOAvant", "ELOApres"])

# --------------------------
# FONCTIONS UTILITAIRES
# --------------------------

def load_players():
    values = sheet_players.get_all_values()
    df = pd.DataFrame(values[1:], columns=values[0])
    # Convertir les colonnes ELO en int
    for col in ["elo_SH", "elo_SD", "elo_DH", "elo_DD", "elo_DM"]:
        df[col] = df[col].astype(int)
    return df

def save_players(df):
    sheet_players.clear()
    sheet_players.append_row(df.columns.tolist())
    for row in df.values.tolist():
        sheet_players.append_row(row)

def add_player(name, sexe):
    df = load_players()
    if name in df['Nom'].tolist():
        st.error("Ce joueur existe déjà !")
        return
    new_row = [name, sexe, 1000, 1000, 1000, 1000, 1000]
    df.loc[len(df)] = new_row
    save_players(df)
    st.success(f"Joueur {name} ajouté.")

def remove_player(name):
    df = load_players()
    if name not in df['Nom'].tolist():
        st.error("Joueur introuvable !")
        return
    df = df[df['Nom'] != name].reset_index(drop=True)
    save_players(df)
    st.success(f"Joueur {name} supprimé.")

# --------------------------
# STREAMLIT UI
# --------------------------

st.title("Administration Badminton ELO")

st.header("Ajouter un joueur")
with st.form("add_form"):
    name_new = st.text_input("Nom du joueur")
    sexe_new = st.selectbox("Sexe", ["M", "F"])
    submitted = st.form_submit_button("Ajouter")
    if submitted:
        if not name_new.strip():
            st.error("Nom vide")
        else:
            add_player(name_new.strip(), sexe_new)

st.header("Supprimer un joueur")
df_joueurs = load_players()
if 'Nom' in df_joueurs.columns and not df_joueurs.empty:
    name_remove = st.selectbox("Choisir un joueur", df_joueurs['Nom'].tolist())
    if st.button("Supprimer"):
        remove_player(name_remove)
else:
    st.info("Aucun joueur disponible pour suppression")

st.header("Historique des matchs")
values = sheet_history.get_all_values()
if len(values) > 1:
    df_hist = pd.DataFrame(values[1:], columns=values[0])
    st.dataframe(df_hist)
else:
    st.info("Aucun match enregistré")

