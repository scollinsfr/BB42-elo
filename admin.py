import streamlit as st
import pandas as pd
import os

# Fichiers CSV dans le Drive
BASE_PATH = "/content/drive/MyDrive/badminton_elo"
PLAYERS_FILE = os.path.join(BASE_PATH, "joueurs.csv")
MATCHES_FILE = os.path.join(BASE_PATH, "historique.csv")

# Initialisation
if not os.path.exists(PLAYERS_FILE):
    pd.DataFrame(columns=["Nom", "Elo"]).to_csv(PLAYERS_FILE, index=False)
if not os.path.exists(MATCHES_FILE):
    pd.DataFrame(columns=["Joueur1", "Joueur2", "Score1", "Score2"]).to_csv(MATCHES_FILE, index=False)

# Lecture
joueurs = pd.read_csv(PLAYERS_FILE)
matches = pd.read_csv(MATCHES_FILE)

st.title("🏸 Administration Badminton (ELO)")

# --- Ajouter un joueur ---
st.subheader("Ajouter un joueur")
nouveau_nom = st.text_input("Nom du joueur")
if st.button("Ajouter joueur"):
    if nouveau_nom and nouveau_nom not in joueurs["Nom"].values:
        joueurs = joueurs._append({"Nom": nouveau_nom, "Elo": 1000}, ignore_index=True)
        joueurs.to_csv(PLAYERS_FILE, index=False)
        st.success(f"{nouveau_nom} ajouté avec succès !")
        st.rerun()

# --- Supprimer un joueur ---
st.subheader("Supprimer un joueur")
if not joueurs.empty:
    joueur_suppr = st.selectbox("Choisir un joueur à supprimer", joueurs["Nom"])
    if st.button("Supprimer joueur"):
        joueurs = joueurs[joueurs["Nom"] != joueur_suppr]
        joueurs.to_csv(PLAYERS_FILE, index=False)
        st.warning(f"{joueur_suppr} supprimé.")
        st.rerun()

# --- Supprimer un match ---
st.subheader("Supprimer un match")
if not matches.empty:
    match_suppr = st.selectbox("Choisir un match à supprimer", matches.index)
    if st.button("Supprimer match"):
        matches = matches.drop(match_suppr)
        matches.to_csv(MATCHES_FILE, index=False)
        st.warning("Match supprimé.")
        st.rerun()

# --- Voir les données ---
st.subheader("Classement actuel")
st.dataframe(joueurs)

st.subheader("Historique des matchs")
st.dataframe(matches)
