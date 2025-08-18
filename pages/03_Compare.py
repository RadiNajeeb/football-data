# pages/03_Compare.py

# 1) Path shim
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# 2) Third-party
import streamlit as st
import pandas as pd

# 3) Explicit imports (adjust to what you actually use on this page)
from lib.data import (
    load_df, get_teams, get_players_for_team,
    safe_cols
)
# from lib.utils import <helpers if any>

# 4) Load data
DATA_PATH = ROOT / "database.csv"
DF = load_df(str(DATA_PATH))

# ------------------- YOUR PAGE LOGIC -------------------
st.title("Compare Players/Teams")

mode = st.radio("Compare", ["Players", "Teams"], horizontal=True)

if mode == "Players":
    t1, t2 = st.columns(2)
    team_a = t1.selectbox("Team A", get_teams(DF), key="cmp_team_a")
    player_a = t1.selectbox("Player A", get_players_for_team(DF, team_a), key="cmp_player_a")

    team_b = t2.selectbox("Team B", get_teams(DF), key="cmp_team_b")
    player_b = t2.selectbox("Player B", get_players_for_team(DF, team_b), key="cmp_player_b")

    a_df = DF[(DF["Team"] == team_a) & (DF["Player"] == player_a)].copy()
    b_df = DF[(DF["Team"] == team_b) & (DF["Player"] == player_b)].copy()

    st.subheader(f"{player_a} vs {player_b}")
    left, right = st.columns(2)
    left.dataframe(a_df[safe_cols(a_df)], use_container_width=True)
    right.dataframe(b_df[safe_cols(b_df)], use_container_width=True)

else:
    team_a = st.selectbox("Team A", get_teams(DF), key="cmp_ta")
    team_b = st.selectbox("Team B", get_teams(DF), key="cmp_tb")
    a_df = DF[DF["Team"] == team_a].copy()
    b_df = DF[DF["Team"] == team_b].copy()

    st.subheader(f"{team_a} vs {team_b}")
    left, right = st.columns(2)
    left.dataframe(a_df[safe_cols(a_df)], use_container_width=True)
    right.dataframe(b_df[safe_cols(b_df)], use_container_width=True)
