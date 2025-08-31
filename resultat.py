import streamlit as st
import pandas as pd
import os
import math

BASE_PATH = "/content/drive/MyDrive/badminton_elo"
PLAYERS_FILE = os.path.join(BASE_PATH, "joueurs.csv")
MATCHES_FILE = os.path.join(BASE_PATH, "historique.csv")

# Lecture
joueurs = pd.read_csv(PLAYERS_FILE)

def calcul_elo(rating1, rating2, score1, score2, k=32):
    """Calcule les nouveaux ELO après un match"""
    expected1 = 1 / (1 + math.pow(10, (rating2 - rating1) / 400))
    expected2 = 1 - expected1
    result1 = 1 if score1 > score2 else 0
    result2 = 1 - result1
    new_rating1 = rating1 + k * (result1 - expected1)
    new_rating2 = rating2 + k * (result2 - expected2)
    return round(new_rating1), round(new_rating2)

st.title("🏸 Saisie Résultat Match")

if len(joueurs) < 2:
    st.warning("Pas assez de joueurs enregistrés.")
else:
    col1, col2 = st.columns(2)
    with col1:
        j1 = st.selectbox("Joueur 1", joueurs["Nom"])
        score1 = st.number_input("Score Joueur 1", min_value=0, max_value=30, step=1)
    with col2:
        j2 = st.selectbox("Joueur 2", [j for j in joueurs["Nom"] if j != j1])
        score2 = st.number_input("Score Joueur 2", min_value=0, max_value=30, step=1)

    if st.button("Valider résultat"):
        if j1 and j2 and score1 != score2:
            r1, r2 = joueurs.loc[joueurs["Nom"] == j1, "Elo"].values[0], joueurs.loc[joueurs["Nom"] == j2, "Elo"].values[0]
            new_r1, new_r2 = calcul_elo(r1, r2, score1, score2)

            # Mise à jour
            joueurs.loc[joueurs["Nom"] == j1, "Elo"] = new_r1
            joueurs.loc[joueurs["Nom"] == j2, "Elo"] = new_r2
            joueurs.to_csv(PLAYERS_FILE, index=False)

            # Historique
            new_match = pd.DataFrame([{"Joueur1": j1, "Joueur2": j2, "Score1": score1, "Score2": score2}])
            if os.path.exists(MATCHES_FILE):
                matches = pd.read_csv(MATCHES_FILE)
                matches = pd.concat([matches, new_match], ignore_index=True)
            else:
                matches = new_match
            matches.to_csv(MATCHES_FILE, index=False)

            st.success("Résultat enregistré ✅")
            st.rerun()
        else:
            st.error("Veuillez saisir un score valide (pas d'égalité).")

st.subheader("Classement actuel")
st.dataframe(joueurs.sort_values(by="Elo", ascending=False))
