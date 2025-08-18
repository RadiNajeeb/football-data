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

# ---------- compute games played vs total team games ----------
p_with_keys, _ = build_game_labels(pdf)

if has(pdf, "Minutes"):
    apps = int((p_with_keys.assign(_m=pdf["Minutes"].fillna(0))["_m"] > 0).groupby(p_with_keys["_GAME_KEY"]).any().sum())
else:
    apps = int(p_with_keys["_GAME_KEY"].nunique())

team_df = DF[DF["Team"] == team].copy()
_, t_games = build_game_labels(team_df)
total_team_games = int(t_games["_GAME_KEY"].nunique())

# ---------- profile strip ----------
num_sum = pdf.select_dtypes(include="number").sum(numeric_only=True)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Team", team)
metric_if(c2, "Position", has(pdf, "Position"), first_or_none(pdf["Position"]))
metric_if(c3, "Minutes (sum)", "Minutes" in num_sum.index, num_sum.get("Minutes"))
metric_if(c4, "Age", has(pdf, "Age"), first_or_none(pdf["Age"]))

# ---------- overview ----------
st.markdown("### Overview")
o1, o2, o3, o4 = st.columns(4)

o1.metric("Appearances", f"{apps} / {total_team_games}")

starts = None
for start_col in ["Starts", "Start", "isStarter", "Starter"]:
    if has(pdf, start_col):
        try:
            col = pdf[start_col]
            if pd.api.types.is_bool_dtype(col):
                starts = int(col.fillna(False).sum())
            else:
                s = col.astype(str).str.lower()
                starts = int(((s.isin(["1", "true", "y", "yes"])) |
                              (pd.to_numeric(s, errors="coerce") > 0)).sum())
            break
        except Exception:
            pass
o2.metric("Starts", starts if starts is not None else "—")

mins_total = float(num_sum.get("Minutes", 0.0))
o3.metric("Average Minutes on ground", f"{(mins_total / apps):.1f}" if apps > 0 else "—")
o4.metric("Games Logged", len(pdf))

# ---------- single-stat picker (replaces aggregated totals & all charts) ----------
st.markdown("### Choose a stat to view")

# Curated list, but only show options that actually exist in the dataset
candidate_stats = [
    "Goals", "Assists", "Shots", "xG", "xA", "GCA", "SCA",
    "Yellow", "Red", "Touches", "Key Passes", "Passes Completed", "Passes Attempted",
    "Tackles", "Interceptions", "Blocks", "Clearances", "Aerials Won", "Aerials Lost"
]
available_stats = [c for c in candidate_stats if c in pdf.columns]

# Fallback: if curated names don't exist, allow any numeric column
if not available_stats:
    available_stats = sorted(pdf.select_dtypes(include="number").columns.tolist())

stat = st.selectbox("Stat", available_stats)

# Show the total (season/selected dataset) for the chosen stat
value = float(pdf[stat].sum()) if stat in pdf.columns else None

s1, s2 = st.columns([1,3])
metric_if(s1, stat + " (total)", value is not None, value)

with s2:
    st.caption("Per-game values for this player:")
    # show a compact per-game table with just the chosen stat
    cols = ["_GAME_LABEL"] + ([stat] if stat in pdf.columns else [])
    pg = p_with_keys[cols].copy() if all(c in p_with_keys.columns for c in cols) else pdf[cols]
    st.dataframe(pg, use_container_width=True)

# ---------- per-game log (full) ----------
st.markdown("### Per-game log (all tracked columns)")
order_cols = [c for c in ["_GAME_LABEL", "Minutes", "Goals", "Assists", "Shots", "xG", "xA", "GCA", "SCA"]
              if c in p_with_keys.columns]
log_df = p_with_keys[order_cols] if order_cols else p_with_keys
st.dataframe(log_df, use_container_width=True)

st.button("◀ Back to Team", on_click=lambda: goto("team", team, None))