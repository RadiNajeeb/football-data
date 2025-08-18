# pages/02_Player.py
import streamlit as st
import pandas as pd
from lib.data import (
    load_df, get_teams, get_players_for_team, metric_num,
    build_game_labels, init_router_state, goto
)

# ---------- boot ----------
DF = load_df("database.csv")
init_router_state()

st.title("Player")

# ---------- selectors ----------
teams = get_teams(DF)
team = st.selectbox(
    "Team", teams,
    index=(teams.index(st.session_state.team) if st.session_state.team in teams else 0),
    key="player_team"
)

players = get_players_for_team(DF, team)
player = st.selectbox(
    "Player", players,
    index=(players.index(st.session_state.player) if st.session_state.player in players else 0),
    key="player_name"
)

pdf = DF[(DF["Team"] == team) & (DF["Player"] == player)].copy()
if pdf.empty:
    st.warning("No data for this player.")
    st.stop()

# ---------- helpers ----------
def first_or_none(series: pd.Series):
    s = series.dropna()
    return s.iloc[0] if not s.empty else None

def has(df: pd.DataFrame, col: str) -> bool:
    return col in df.columns

def metric_if(col, label, condition: bool, value):
    if condition:
        metric_num(col, label, value)
    else:
        col.metric(label, "—")

# ---------- compute games played ----------
p_with_keys, _ = build_game_labels(pdf)

# ---------- profile strip ----------
num_sum = pdf.select_dtypes(include="number").sum(numeric_only=True)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Team", team)
metric_if(c2, "Position", has(pdf, "Position"), first_or_none(pdf["Position"]))
metric_if(c3, "Minutes (sum)", "Minutes" in num_sum.index, num_sum.get("Minutes"))
metric_if(c4, "Age", has(pdf, "Age"), first_or_none(pdf["Age"]))

# ---------- key stats ----------
st.markdown("### Key Stats")

k1, k2, k3, k4, k5 = st.columns(5)
total_minutes = num_sum.get("Minutes", 0)
metric_if(k1, "Minutes (Total)", "Minutes" in num_sum.index, total_minutes)
metric_if(k2, "Avg Minutes/Game", apps > 0, f"{(total_minutes / apps):.1f}")
metric_if(k3, "Goals", "Goals" in num_sum.index, num_sum.get("Goals"))
metric_if(k4, "Assists", "Assists" in num_sum.index, num_sum.get("Assists"))
metric_if(k5, "Passes Completed", "Passes Completed" in num_sum.index, num_sum.get("Passes Completed"))


k5, k6, k7 = st.columns(3)
metric_if(k5, "Tackles", "Tackles" in num_sum.index, num_sum.get("Tackles"))
metric_if(k6, "Red Cards", "Red" in num_sum.index, num_sum.get("Red"))
metric_if(k7, "Yellow Cards", "Yellow" in num_sum.index, num_sum.get("Yellow"))

# ---------- per-game log ----------
st.markdown("### Per-game log (all tracked columns)")
order_cols = [c for c in ["_GAME_LABEL", "Minutes", "Goals", "Assists",
                          "Passes Completed", "Tackles", "Red", "Yellow"]
              if c in p_with_keys.columns]
log_df = p_with_keys[order_cols] if order_cols else p_with_keys
st.dataframe(log_df, use_container_width=True)

st.button("◀ Back to Team", on_click=lambda: goto("team", team, None))
