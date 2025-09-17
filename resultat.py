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

def add_match(date, type_match, winners, losers, elo_avant, elo_apres):
    row = [date, type_match, winners, losers, elo_avant, elo_apres]
    ws_historique.append_row(row)

# --------------------------
# TABLES DE POINTS
# --------------------------

# Simples (SH, SD)
simple_table = [
    (0,49,20,14),
    (50,99,17,13),
    (100,199,14,12),
    (200,299,11,10),
    (300,399,9,7),
    (400,599,7,4),
    (600,799,5,1),
    (800,999,4,0),
    (1000,float('inf'),3,0)
]

# Doubles (DD, DH, DM)
double_table = [
    (0,49, 40,28, 40,28),
    (50,99, 34,26, 46,30),
    (100,199,28,24, 52,32),
    (200,299,22,20, 64,36),
    (300,399,18,14, 76,40),
    (400,599,14,8, 86,44),
    (600,799,10,2,106,48),
    (800,999,8,0,122,52),
    (1000,float('inf'),6,0,140,56)
]

# --------------------------
# CALCUL DES POINTS
# --------------------------

def get_points_simple(winner_elo, loser_elo):
    ecart = abs(winner_elo - loser_elo)
    if winner_elo >= loser_elo:  # mieux classé gagne
        for min_e, max_e, w_pts, l_pts in simple_table:
            if min_e <= ecart <= max_e:
                return w_pts, l_pts
    else:  # moins bien classé gagne
        for min_e, max_e, l_pts, w_pts in simple_table:
            if min_e <= ecart <= max_e:
                return w_pts, l_pts
    return 20,14

def get_points_double(elo_winners, elo_losers):
    ecart = abs(elo_winners - elo_losers)
    if elo_winners >= elo_losers:  # paire gagnante mieux classée
        for min_e, max_e, w_pts, l_pts, _, _ in double_table:
            if min_e <= ecart <= max_e:
                return w_pts, l_pts
    else:  # paire gagnante moins bien classée
        for min_e, max_e, _, _, w_pts, l_pts in double_table:
            if min_e <= ecart <= max_e:
                return w_pts, l_pts
    return 40,28

def repartition_double(elo_j1, elo_j2, points):
    ecart = abs(elo_j2 - elo_j1)
    if ecart < 400:
        return points*0.5, points*0.5
    elif ecart < 500:
        return points*0.54, points*0.46
    elif ecart < 600:
        return points*0.57, points*0.43
    elif ecart < 700:
        return points*0.61, points*0.39
    elif ecart < 800:
        return points*0.64, points*0.36
    elif ecart < 900:
        return points*0.68, points*0.32
    elif ecart < 1000:
        return points*0.71, points*0.29
    else:
        return points*0.75, points*0.25

# --------------------------
# THEME (toggle sombre / clair en haut)
# --------------------------

dark = st.checkbox("🌙 Mode sombre", value=True)

dark_css = """
<style>
[data-testid="stAppViewContainer"] {background-color:#0d1117;color:#e6edf3;}
h1,h2,h3 {color:#00aaff !important;}
.stButton>button {background-color:#00aaff !important;color:white !important;border-radius:8px;font-weight:600;}
a,p,span,label {color:#e6edf3 !important;}
</style>
"""

light_css = """
<style>
[data-testid="stAppViewContainer"] {background-color:#ffffff;color:#111;}
h1,h2,h3 {color:#0077cc !important;}
.stButton>button {background-color:#0077cc !important;color:white !important;border-radius:8px;font-weight:600;}
a,p,span,label {color:#111 !important;}
</style>
"""

st.markdown(dark_css if dark else light_css, unsafe_allow_html=True)

# --------------------------
# PAGE
# --------------------------

logo_url = ""  # mets l'URL du logo ici
if logo_url:
    st.image(logo_url, width=150)

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
        if len(winners)<1 or len(losers)<1:
            st.error("⚠️ Sélectionne au moins 1 joueur dans chaque équipe")
        elif set(winners) & set(losers):
            st.error("⚠️ Un même joueur ne peut pas être dans les deux équipes")
        else:
            date = datetime.now().strftime("%Y-%m-%d %H:%M")
            col_elo = "elo_" + type_match

            elo_winners = df_joueurs.loc[df_joueurs["Nom"].isin(winners), col_elo].mean()
            elo_losers = df_joueurs.loc[df_joueurs["Nom"].isin(losers), col_elo].mean()

            if type_match in ["SH","SD"]:
                pts_w, pts_l = get_points_simple(elo_winners, elo_losers)
                for p in winners:
                    new_elo = df_joueurs.loc[df_joueurs["Nom"]==p,col_elo].values[0]+pts_w
                    update_player_elo(p,col_elo,new_elo)
                for p in losers:
                    new_elo = df_joueurs.loc[df_joueurs["Nom"]==p,col_elo].values[0]-pts_l
                    update_player_elo(p,col_elo,new_elo)
            else:  # doubles
                pts_w, pts_l = get_points_double(elo_winners, elo_losers)
                # répartition par joueur
                j1, j2 = winners
                j3, j4 = losers
                elo_j1 = df_joueurs.loc[df_joueurs["Nom"]==j1,col_elo].values[0]
                elo_j2 = df_joueurs.loc[df_joueurs["Nom"]==j2,col_elo].values[0]
                elo_j3 = df_joueurs.loc[df_joueurs["Nom"]==j3,col_elo].values[0]
                elo_j4 = df_joueurs.loc[df_joueurs["Nom"]==j4,col_elo].values[0]

                # paire gagnante
                pts_j1, pts_j2 = repartition_double(min(elo_j1,elo_j2), max(elo_j1,elo_j2), pts_w)
                update_player_elo(j1,col_elo,elo_j1+pts_j1)
                update_player_elo(j2,col_elo,elo_j2+pts_j2)
                # paire perdante
                pts_j3, pts_j4 = repartition_double(min(elo_j3,elo_j4), max(elo_j3,elo_j4), pts_l)
                update_player_elo(j3,col_elo,elo_j3-pts_j3)
                update_player_elo(j4,col_elo,elo_j4-pts_j4)

            add_match(date,type_match,", ".join(winners),", ".join(losers),
                      f"{elo_winners}/{elo_losers}",
                      f"{elo_winners+pts_w}/{elo_losers-pts_l}" if type_match in ["SH","SD"] else f"{elo_winners}/{elo_losers}")

            st.success("✅ Match enregistré et ELO mis à jour !")

# --------------------------
# HISTORIQUE AVEC COULEURS
# --------------------------

st.header("📜 Historique des matchs")
values = ws_historique.get_all_values()
if len(values)>1:
    df_hist = pd.DataFrame(values[1:], columns=values[0])
    def color_match(val):
        colors = {"SH":"background-color:#3399ff;color:white;",
                  "DH":"background-color:#33cc33;color:white;",
                  "SD":"background-color:#ff66b2;color:white;",
                  "DD":"background-color:#ff9933;color:white;",
                  "DM":"background-color:#9933ff;color:white;"}
        return colors.get(val,"")
    if "Type de match" in df_hist.columns:
        styled = df_hist.style.applymap(color_match, subset=["Type de match"])
        styled = styled.set_properties(**{"white-space":"nowrap"})
        st.dataframe(styled,use_container_width=True)
    else:
        st.dataframe(df_hist,use_container_width=True)
else:
    st.info("ℹ️ Aucun match enregistré")
