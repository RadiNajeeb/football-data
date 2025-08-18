# app.py
import streamlit as st
import pandas as pd
from lib.data import (
    load_df, get_teams, get_players_for_team, kpi_row,
    goto, init_router_state
)

st.set_page_config(page_title="League Explorer", layout="wide")

# Load your CSV (change path if needed)
DF = load_df("database.csv")

# URL/query-param aware state
init_router_state()

st.title("Exploring La Liga")
st.subheader("This website will provide you stata about teams and players in La-Liga.")
st.caption("Browse teams → pick a player → explore stats. Use the header tabs to switch sections.")

left, right = st.columns(2)
with left:
    teams = get_teams(DF)
    team = st.selectbox("Team", teams,
                        index=(teams.index(st.session_state.team) if st.session_state.team in teams else 0),
                        key="home_team")

with right:
    players = get_players_for_team(DF, team)
    player = st.selectbox("Player", players,
                          index=(players.index(st.session_state.player) if st.session_state.player in players else 0),
                          key="home_player")

# Team KPIs (aggregated across games so totals make sense)
team_df = DF[DF["Team"] == team]
kpi_row(team_df, aggregate=True)

st.info("Navigate below or use the header tabs. Click **Go to Team** or **Open Player** to drill down.")
c1, c2 = st.columns(2)
c1.button("🔎 Go to Team", use_container_width=True, on_click=lambda: goto("team", team, None))
c2.button("👤 Open Player", use_container_width=True, on_click=lambda: goto("player", team, player))

st.divider()
st.subheader(team)
st.write("Jump into **Teams** or **Player** pages from the sidebar.")