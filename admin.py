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

st.title("Administration Badminton ELO")

# --- Ajouter joueur ---
st.header("Ajouter un joueur")
nom = st.text_input("Nom")
sexe = st.selectbox("Sexe", ["M", "F"])
if st.button("Ajouter joueur"):
    if nom in df_joueurs['Nom'].values:
        st.error("Ce joueur existe déjà")
    else:
        new_row = [nom, sexe, 1000, 1000, 1000, 1000, 1000]
        ws_joueurs.append_row(new_row)
        st.success(f"Joueur {nom} ajouté")

# --- Supprimer joueur ---
st.header("Supprimer un joueur")
nom_suppr = st.selectbox("Choisir un joueur", df_joueurs['Nom'].tolist())
if st.button("Supprimer joueur"):
    idx = df_joueurs.index[df_joueurs['Nom'] == nom_suppr][0] + 2  # +2 car gspread index base 1 + header
    ws_joueurs.delete_rows(idx)
    st.success(f"Joueur {nom_suppr} supprimé")

# --- Annuler dernier match ---
st.header("Annuler dernier match")
if st.button("Annuler dernière saisie"):
    hist = ws_historique.get_all_values()
    if len(hist) <= 1:
        st.error("Aucun match à annuler")
    else:
        ws_historique.delete_rows(len(hist))
        st.success("Dernière saisie annulée")
