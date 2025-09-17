import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from datetime import datetime

# --- Connexion Google Sheets ---
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
# UTILITAIRES
# --------------------------

def load_players():
    values = ws_joueurs.get_all_values()
    if not values or len(values) == 0:
        return pd.DataFrame(columns=["Nom","Sexe","elo_SH","elo_SD","elo_DH","elo_DD","elo_DM"])
    df = pd.DataFrame(values[1:], columns=values[0])
    for col in ["elo_SH","elo_SD","elo_DH","elo_DD","elo_DM"]:
        if col not in df.columns:
            df[col] = 1000
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(1000).astype(int)
    return df

def update_player_elo(player_name, col_elo, new_value):
    values = ws_joueurs.get_all_values()
    if not values or len(values)<1:
        return
    headers = values[0]
    try:
        col_index = headers.index(col_elo)+1
    except ValueError:
        st.error(f"Colonne {col_elo} introuvable.")
        return
    row_index = None
    for i,row in enumerate(values[1:],start=2):
        if len(row)>0 and row[0]==player_name:
            row_index=i
            break
    if row_index:
        ws_joueurs.update_cell(row_index,col_index,int(new_value))
    else:
        st.error(f"Impossible de trouver le joueur {player_name}.")

# ----- Points simples -----
def get_points_simple(elo_w, elo_l):
    diff = abs(elo_w - elo_l)
    table = [
        (0,49,20,14,20,14),
        (50,99,17,13,23,15),
        (100,199,14,12,26,16),
        (200,299,11,10,32,18),
        (300,399,9,7,38,20),
        (400,599,7,4,43,22),
        (600,799,5,1,53,24),
        (800,999,4,0,61,26),
        (1000,999999,3,0,70,28)
    ]
    for minv,maxv,winner,loser,winner2,loser2 in table:
        if minv<=diff<=maxv:
            if elo_w>=elo_l:
                return winner,loser
            else:
                return winner2,loser2
    return 20,14

# ----- Points doubles -----
def get_points_double(elo_w, elo_l):
    diff = abs(elo_w - elo_l)
    table = [
        (0,49,40,28,40,28),
        (50,99,34,26,46,30),
        (100,199,28,24,52,32),
        (200,299,22,20,64,36),
        (300,399,18,14,76,40),
        (400,599,14,8,86,44),
        (600,799,10,2,106,48),
        (800,999,8,0,122,52),
        (1000,999999,6,0,140,56)
    ]
    for minv,maxv,winner,loser,winner2,loser2 in table:
        if minv<=diff<=maxv:
            if elo_w>=elo_l:
                return winner,loser
            else:
                return winner2,loser2
    return 20,14

# ----- Répartition doubles -----
def repartition_double(elo_low,elo_high,pts):
    diff = elo_high-elo_low
    table = [
        (0,399,0.5,0.5,0.5,0.5),
        (400,499,0.54,0.46,0.46,0.54),
        (500,599,0.57,0.43,0.43,0.57),
        (600,699,0.61,0.39,0.39,0.61),
        (700,799,0.64,0.36,0.36,0.64),
        (800,899,0.68,0.32,0.32,0.68),
        (900,999,0.71,0.29,0.29,0.71),
        (1000,999999,0.75,0.25,0.25,0.75)
    ]
    for minv,maxv,j1_win,j2_win,j1_lose,j2_lose in table:
        if minv<=diff<=maxv:
            if pts>=0:
                return round(pts*j1_win),round(pts*j2_win)
            else:
                return round(-pts*j1_lose),round(-pts*j2_lose)
    return round(pts/2),round(pts/2)

# --------------------------
# ADD MATCH
# --------------------------
def add_match(date,type_match,winners,losers,elo_avant,elo_apres):
    ws_historique.append_row([date,type_match,winners,losers,elo_avant,elo_apres])

# --------------------------
# THEME
# --------------------------
dark = st.checkbox("🌙 Mode sombre", value=True)

dark_css = """
<style>
[data-testid="stAppViewContainer"] {background-color:#0d1117;color:#e6edf3;}
h1,h2,h3 {color:#00aaff !important;}
.stButton>button {background-color:#00aaff;color:white;border-radius:8px;font-weight:600;}
a,p,span,label {color:#e6edf3 !important;}
</style>
"""

light_css = """
<style>
[data-testid="stAppViewContainer"] {background-color:#ffffff;color:#111;}
h1,h2,h3 {color:#0077cc !important;}
.stButton>button {background-color:#0077cc;color:white;border-radius:8px;font-weight:600;}
a,p,span,label {color:#111 !important;}
</style>
"""

st.markdown(dark_css if dark else light_css, unsafe_allow_html=True)

# --------------------------
# PAGE
# --------------------------
st.image("logo.jpg", width=100)
st.title("🏸 Résultats Badminton ELO")
df_joueurs = load_players()

st.header("➕ Enregistrer un match")
with st.form("match_form"):
    type_match = st.selectbox("Type de match",["SH","SD","DH","DD","DM"])
    noms = df_joueurs["Nom"].tolist() if not df_joueurs.empty else []
    winners = st.multiselect("Équipe gagnante", noms, max_selections=2)
    losers = st.multiselect("Équipe perdante", noms, max_selections=2)
    submitted = st.form_submit_button("Enregistrer le match")

    if submitted:
        if len(winners)<1 or len(losers)<1:
            st.error("⚠️ Sélectionne au moins 1 joueur dans chaque équipe")
        elif set(winners)&set(losers):
            st.error("⚠️ Un même joueur ne peut pas être dans les deux équipes")
        else:
            date_full = datetime.now()
            date_display = date_full.strftime("%Y-%m-%d")
            date_sheet = date_full.strftime("%Y-%m-%d %H:%M")
            col_elo = "elo_"+type_match

            # Simple
            if type_match in ["SH","SD"]:
                elo_winners = df_joueurs.loc[df_joueurs["Nom"].isin(winners),col_elo].values[0]
                elo_losers = df_joueurs.loc[df_joueurs["Nom"].isin(losers),col_elo].values[0]
                pts_w, pts_l = get_points_simple(elo_winners,elo_losers)

                elo_avant = [elo_winners,elo_losers]
                update_player_elo(winners[0],col_elo,elo_winners+pts_w)
                update_player_elo(losers[0],col_elo,elo_losers-pts_l)
                elo_apres = [elo_winners+pts_w,elo_losers-pts_l]

            # Double
            else:
                j1,j2 = winners
                j3,j4 = losers
                elo_vals = [df_joueurs.loc[df_joueurs["Nom"]==p,col_elo].values[0] for p in [j1,j2,j3,j4]]
                pts_w, pts_l = get_points_double(sum(elo_vals[:2])/2,sum(elo_vals[2:])/2)
                pts_j1, pts_j2 = repartition_double(min(elo_vals[0],elo_vals[1]),max(elo_vals[0],elo_vals[1]),pts_w)
                pts_j3, pts_j4 = repartition_double(min(elo_vals[2],elo_vals[3]),max(elo_vals[2],elo_vals[3]),pts_l)

                elo_avant = elo_vals
                update_player_elo(j1,col_elo,elo_vals[0]+pts_j1)
                update_player_elo(j2,col_elo,elo_vals[1]+pts_j2)
                update_player_elo(j3,col_elo,elo_vals[2]-pts_j3)
                update_player_elo(j4,col_elo,elo_vals[3]-pts_j4)
                elo_apres = [df_joueurs.loc[df_joueurs["Nom"]==p,col_elo].values[0] for p in [j1,j2,j3,j4]]

            add_match(date_sheet,type_match,", ".join(winners),", ".join(losers),
                      "/".join([str(int(e)) for e in elo_avant]),
                      "/".join([str(int(e)) for e in elo_apres]))
            st.success("✅ Match enregistré et ELO mis à jour !")

# --------------------------
# HISTORIQUE
# --------------------------
st.header("📜 Historique des matchs")
values = ws_historique.get_all_values()
if len(values)>1:
    df_hist = pd.DataFrame(values[1:],columns=values[0])
    # Affichage simplifié : date + type + vainqueurs + perdants
    df_hist_display = df_hist[["Date","Type de match","Vainqueurs","Perdants"]]

    def color_match(val):
        colors = {"SH":"#3399ff","DH":"#33cc33","SD":"#ff66b2","DD":"#ff9933","DM":"#9933ff"}
        return f"background-color:{colors.get(val,'')};color:white;"

    if "Type de match" in df_hist_display.columns:
        styled = df_hist_display.style.applymap(color_match, subset=["Type de match"])
        st.dataframe(styled,use_container_width=True)
    else:
        st.dataframe(df_hist_display,use_container_width=True)
else:
    st.info("ℹ️ Aucun match enregistré")
