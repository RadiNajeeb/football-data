# pages/02_Player.py

# 1) Path shim so local packages import fine on Streamlit Cloud
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# 2) Third-party libs
import streamlit as st
import pandas as pd

# 3) Explicit imports from your code (adjust to what this page actually uses)
from lib.data import (
    load_df, get_players_for_team, get_teams,
    init_router_state, safe_cols, kpi_row
)
# from lib.utils import <add helpers this page needs>

# 4) Load data
DATA_PATH = ROOT / "database.csv"
DF = load_df(str(DATA_PATH))
init_router_state()

# ------------------- YOUR PAGE LOGIC -------------------
st.title("Player Explorer")

teams = get_teams(DF)
team = st.selectbox("Team", teams, index=0, key="players_team")

players = get_players_for_team(DF, team)
player = st.selectbox("Player", players, index=0, key="players_player")

p_df = DF[(DF["Team"] == team) & (DF["Player"] == player)].copy()
if p_df.empty:
    st.warning("No data for this player.")
    st.stop()

kpi_row(p_df, aggregate=False)

with st.expander("Raw data"):
    defaults = safe_cols(p_df, ["Match","Minutes","Goals","Assists"])
    cols = st.multiselect("Columns", list(p_df.columns), default=defaults or list(p_df.columns))
    st.dataframe(p_df[cols] if cols else p_df, use_container_width=True)
