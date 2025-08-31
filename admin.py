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

# --- Charger joueurs ---
df_joueurs = pd.DataFrame(ws_joueurs.get_all_records())
df_matches = pd.DataFrame(ws_historique.get_all_records())


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
values = ws_historique.get_all_values()
if len(values) > 1:
    df_hist = pd.DataFrame(values[1:], columns=values[0])
    st.dataframe(df_hist)
else:
    st.info("Aucun match enregistré")

