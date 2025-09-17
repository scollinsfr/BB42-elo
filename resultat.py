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

def update_player_elo(player_name, col_elo, new_value):
    values = ws_joueurs.get_all_values()
    if not values or len(values) < 1:
        return
    headers = values[0]
    try:
        col_index = headers.index(col_elo) + 1
    except ValueError:
        st.error(f"Colonne {col_elo} introuvable dans la feuille Joueurs.")
        return
    row_index = None
    for i, row in enumerate(values[1:], start=2):
        if len(row) > 0 and row[0] == player_name:
            row_index = i
            break
    if row_index:
        ws_joueurs.update_cell(row_index, col_index, int(new_value))
    else:
        st.error(f"Impossible de trouver la ligne pour le joueur {player_name}.")

def calculate_elo(winner_elo, loser_elo, k=32):
    expected_win = 1 / (1 + 10 ** ((loser_elo - winner_elo) / 400))
    new_winner_elo = round(winner_elo + k * (1 - expected_win))
    new_loser_elo = round(loser_elo - k * (1 - expected_win))
    return new_winner_elo, new_loser_elo

def add_match(date, type_match, winners, losers, elo_avant, elo_apres):
    row = [date, type_match, winners, losers, elo_avant, elo_apres]
    ws_historique.append_row(row)


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

if dark:
    st.markdown(dark_css, unsafe_allow_html=True)
else:
    st.markdown(light_css, unsafe_allow_html=True)


# --------------------------
# PAGE
# --------------------------

st.image("logo.jpg", width=100)

st.title("🏸 Résultats Badminton ELO")

df_joueurs = load_players()

st.header("➕ Enregistrer un match")

with st.form("match_form"):
    type_match = st.selectbox("Type de match", ["SH", "SD", "DH", "DD", "DM"])
    noms = df_joueurs["Nom"].tolist() if not df_joueurs.empty else []
    winners = st.multiselect("Équipe gagnante", noms, max_selections=2)
    losers = st.multiselect("Équipe perdante", noms, max_selections=2)
    submitted = st.form_submit_button("Enregistrer le match")

    if submitted:
        if len(winners) < 1 or len(losers) < 1:
            st.error("⚠️ Sélectionne au moins 1 joueur dans chaque équipe")
        elif set(winners) & set(losers):
            st.error("⚠️ Un même joueur ne peut pas être dans les deux équipes")
        else:
            date = datetime.now().strftime("%Y-%m-%d %H:%M")
            col_elo = "elo_" + type_match

            elo_winners_avant = df_joueurs.loc[df_joueurs["Nom"].isin(winners), col_elo].mean()
            elo_losers_avant = df_joueurs.loc[df_joueurs["Nom"].isin(losers), col_elo].mean()

            new_winner_elo, new_loser_elo = calculate_elo(elo_winners_avant, elo_losers_avant)

            for p in winners:
                update_player_elo(p, col_elo, new_winner_elo)
            for p in losers:
                update_player_elo(p, col_elo, new_loser_elo)

            add_match(
                date,
                type_match,
                ", ".join(winners),
                ", ".join(losers),
                f"{int(elo_winners_avant)}/{int(elo_losers_avant)}",
                f"{new_winner_elo}/{new_loser_elo}"
            )

            st.success("✅ Match enregistré et ELO mis à jour !")


# --------------------------
# HISTORIQUE AVEC COULEURS
# --------------------------

st.header("📜 Historique des matchs")
values = ws_historique.get_all_values()
if len(values) > 1:
    df_hist = pd.DataFrame(values[1:], columns=values[0])

    # fonction de coloration selon type
    def color_match(val):
        colors = {
            "SH": "background-color: #3399ff; color: white;",   # bleu
            "DH": "background-color: #33cc33; color: white;",   # vert
            "SD": "background-color: #ff66b2; color: white;",   # rose
            "DD": "background-color: #ff9933; color: white;",   # orange
            "DM": "background-color: #9933ff; color: white;",   # violet
        }
        return colors.get(val, "")

    # appliquer style uniquement sur la colonne Type de match
    if "Type de match" in df_hist.columns:
        styled = df_hist.style.applymap(color_match, subset=["Type de match"])
        st.write(styled.to_html(), unsafe_allow_html=True)  # ✅ permet d'afficher le style
    else:
        st.dataframe(df_hist, use_container_width=True)
else:
    st.info("ℹ️ Aucun match enregistré")
