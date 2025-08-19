# pages/02_Player.py
import streamlit as st
import pandas as pd
from lib.data import (
    load_df, get_teams, get_players_for_team, metric_num,
    build_game_labels, init_router_state, goto, inject_theme_css
)

st.set_page_config(layout="wide")

# ---------- boot ----------
DF = load_df("database.csv")
init_router_state()
inject_theme_css()

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

# Compute appearances and average minutes per appearance
apps = 0
if "_GAME_KEY" in p_with_keys.columns:
    if "Minutes" in p_with_keys.columns:
        per_game_played = (
            p_with_keys.groupby("_GAME_KEY")["Minutes"]
            .apply(lambda s: (pd.to_numeric(s, errors="coerce").fillna(0) > 0).any())
        )
        apps = int(per_game_played.sum())
    else:
        apps = int(p_with_keys["_GAME_KEY"].nunique())

minutes_sum = float(num_sum.get("Minutes", 0.0)) if "Minutes" in num_sum.index else 0.0
avg_minutes = round(minutes_sum / apps, 1) if apps > 0 else pd.NA

# Tackles totals and per-game average
_tackles_present = "Tackles" in num_sum.index
_tackles_total = num_sum.get("Tackles") if _tackles_present else pd.NA
_tackles_avg = round((_tackles_total / apps), 2) if (_tackles_present and apps > 0) else pd.NA

# ----- Profile row -----
st.markdown("#### Profile")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Team", team)
metric_if(c2, "Position", has(pdf, "Position"), first_or_none(pdf["Position"]))
metric_if(c3, "Minutes (sum)", "Minutes" in num_sum.index, num_sum.get("Minutes"))
metric_if(c4, "Age", has(pdf, "Age"), first_or_none(pdf["Age"]))

# ----- Key stats row -----
st.markdown("#### Key Stats")
k1, k2, k3, k4, k5 = st.columns(5)
metric_if(k1, "Minutes", "Minutes" in num_sum.index, num_sum.get("Minutes"))
metric_if(k2, "Goals", "Goals" in num_sum.index, num_sum.get("Goals"))
metric_if(k3, "Assists", "Assists" in num_sum.index, num_sum.get("Assists"))
metric_if(k4, "Passes Completed", "Passes Completed" in num_sum.index, num_sum.get("Passes Completed"))
metric_if(k5, "Avg Minutes", (apps > 0) and ("Minutes" in num_sum.index), avg_minutes)

# ----- Games row -----
st.markdown("#### Participation")
TOTAL_GAMES = 15
g1, g2 = st.columns([1, 3])
g1.metric("Games Played", f"{apps}/{TOTAL_GAMES}")

# ----- Defensive row -----
st.markdown("#### Defensive")
d1, d2, d3, d4 = st.columns(4)
metric_if(d1, "Tackles", _tackles_present, _tackles_total)
metric_if(d2, "Tackles (avg)", (_tackles_present and apps > 0), _tackles_avg)
metric_if(d3, "Red Cards", "Red Cards" in num_sum.index, num_sum.get("Red Cards"))
metric_if(d4, "Yellow Cards", "Yellow Cards" in num_sum.index, num_sum.get("Yellow Cards"))

# ---------- per-game log ----------
st.markdown("### Per-game log (all tracked columns)")
order_cols = [c for c in ["_GAME_LABEL", "Minutes", "Goals", "Assists",
                           "Passes Completed", "Tackles", "Red Cards", "Yellow Cards"]
              if c in p_with_keys.columns]
log_df = p_with_keys[order_cols] if order_cols else p_with_keys
st.dataframe(log_df, use_container_width=True)

st.button("◀ Back to Team", on_click=lambda: goto("team", team, None))
