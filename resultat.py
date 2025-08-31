import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from datetime import datetime

K_FACTOR = 32

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

st.title("Saisie des matchs Badminton ELO")

# --- Sélection du match ---
joueurs = df_joueurs['Nom'].tolist()
st.header("Équipe 1")
equipe1 = st.multiselect("Choisir les joueurs équipe 1", joueurs)
st.header("Équipe 2")
equipe2 = st.multiselect("Choisir les joueurs équipe 2", [j for j in joueurs if j not in equipe1])

type_match = st.selectbox("Type de match", ["SH", "SD", "DH", "DD", "DM"])
gagnant = st.selectbox("Équipe gagnante", ["Équipe 1", "Équipe 2"])

# --- Fonctions ELO ---
def calcul_elo(e1, e2, score1):
    exp1 = 1 / (1 + 10 ** ((e2 - e1) / 400))
    exp2 = 1 - exp1
    new_e1 = e1 + K_FACTOR * (score1 - exp1)
    new_e2 = e2 + K_FACTOR * ((1 - score1) - exp2)
    return round(new_e1), round(new_e2)

def appliquer_elo(j1_names, j2_names, type_match):
    e1 = df_joueurs.loc[df_joueurs['Nom'].isin(j1_names), f'elo_{type_match}'].mean()
    e2 = df_joueurs.loc[df_joueurs['Nom'].isin(j2_names), f'elo_{type_match}'].mean()
    score1 = 1 if gagnant == "Équipe 1" else 0
    new_e1, new_e2 = calcul_elo(e1, e2, score1)
    delta1 = new_e1 - e1
    delta2 = new_e2 - e2
    for j in j1_names:
        idx = df_joueurs.index[df_joueurs['Nom']==j][0]+2
        ws_joueurs.update_cell(idx, df_joueurs.columns.get_loc(f'elo_{type_match}')+1, int(df_joueurs.loc[df_joueurs['Nom']==j, f'elo_{type_match}'].values[0]+delta1))
    for j in j2_names:
        idx = df_joueurs.index[df_joueurs['Nom']==j][0]+2
        ws_joueurs.update_cell(idx, df_joueurs.columns.get_loc(f'elo_{type_match}')+1, int(df_joueurs.loc[df_joueurs['Nom']==j, f'elo_{type_match}'].values[0]+delta2))
    return

# --- Valider match ---
if st.button("Valider match"):
    if not equipe1 or not equipe2:
        st.error("Sélectionner les deux équipes")
    elif set(equipe1) & set(equipe2):
        st.error("Un joueur est présent dans les deux équipes")
    else:
        appliquer_elo(equipe1, equipe2, type_match)
        # Historique
        date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ws_historique.append_row([date, type_match, ",".join(equipe1), ",".join(equipe2), gagnant, "", ""])
        st.success("Match enregistré")
