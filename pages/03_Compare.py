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

st.set_page_config(layout="wide")

# 3) App imports
from lib.data import (
    load_df, get_teams, get_players_for_team,
    inject_theme_css, metric_num
)
from lib.agent_tools import act_player_summary

# 4) Load data
DATA_PATH = ROOT / "database.csv"
DF = load_df(str(DATA_PATH))

inject_theme_css()
st.title("Compare Players")

# ------------------- UI: Pick players -------------------
# Add a spacer column to push selectors further apart
t_left, t_gap, t_right = st.columns([1, 0.3, 1])
team_a = t_left.selectbox("Team A", get_teams(DF), key="cmp_team_a")
player_a = t_left.selectbox("Player A", get_players_for_team(DF, team_a), key="cmp_player_a")

team_b = t_right.selectbox("Team B", get_teams(DF), key="cmp_team_b")
player_b = t_right.selectbox("Player B", get_players_for_team(DF, team_b), key="cmp_player_b")

# ------------------- Compute summaries -------------------
left_summary = act_player_summary(team_a, player_a)
right_summary = act_player_summary(team_b, player_b)

# Guard for errors
if left_summary.get("error") or right_summary.get("error"):
    st.error("Could not load one of the players. Please pick valid team/player.")
    st.stop()

# Helper to sum a numeric column for a given player from raw DF
def sum_col(team: str, player: str, col: str):
    if col not in DF.columns:
        return None
    s = pd.to_numeric(DF[(DF["Team"] == team) & (DF["Player"] == player)][col], errors="coerce")
    return float(s.sum()) if not s.empty else None

# ------------------- Player Overviews (match Player page stats) -------------------
st.markdown("#### Player Overviews")
L, gap_over, R = st.columns([1, 0.3, 1])

with L:
    st.subheader(f"{player_a} ({team_a})")
    r1c1, r1c2, r1c3, r1c4 = st.columns(4)
    metric_num(r1c1, "Minutes", left_summary.get("minutes_sum"))
    metric_num(r1c2, "Avg Minutes", left_summary.get("avg_minutes"))
    metric_num(r1c3, "Goals", left_summary.get("Goals"))
    metric_num(r1c4, "Assists", left_summary.get("Assists"))

    r2c1, r2c2, r2c3, r2c4 = st.columns(4)
    metric_num(r2c1, "Passes Completed", sum_col(team_a, player_a, "Passes Completed"))
    tack_sum_a = sum_col(team_a, player_a, "Tackles")
    apps_a = left_summary.get("appearances")
    tack_avg_a = round(tack_sum_a / apps_a, 2) if (tack_sum_a is not None and apps_a) else None
    metric_num(r2c2, "Tackles", tack_sum_a)
    metric_num(r2c3, "Tackles (avg)", tack_avg_a)
    metric_num(r2c4, "Games Played", f"{apps_a}/15")

    # Cards
    r3c1, r3c2 = st.columns(2)
    metric_num(r3c1, "Yellow Cards", sum_col(team_a, player_a, "Yellow Cards"))
    metric_num(r3c2, "Red Cards", sum_col(team_a, player_a, "Red Cards"))

with R:
    st.subheader(f"{player_b} ({team_b})")
    r1c1, r1c2, r1c3, r1c4 = st.columns(4)
    metric_num(r1c1, "Minutes", right_summary.get("minutes_sum"))
    metric_num(r1c2, "Avg Minutes", right_summary.get("avg_minutes"))
    metric_num(r1c3, "Goals", right_summary.get("Goals"))
    metric_num(r1c4, "Assists", right_summary.get("Assists"))

    r2c1, r2c2, r2c3, r2c4 = st.columns(4)
    metric_num(r2c1, "Passes Completed", sum_col(team_b, player_b, "Passes Completed"))
    tack_sum_b = sum_col(team_b, player_b, "Tackles")
    apps_b = right_summary.get("appearances")
    tack_avg_b = round(tack_sum_b / apps_b, 2) if (tack_sum_b is not None and apps_b) else None
    metric_num(r2c2, "Tackles", tack_sum_b)
    metric_num(r2c3, "Tackles (avg)", tack_avg_b)
    metric_num(r2c4, "Games Played", f"{apps_b}/15")

    r3c1, r3c2 = st.columns(2)
    metric_num(r3c1, "Yellow Cards", sum_col(team_b, player_b, "Yellow Cards"))
    metric_num(r3c2, "Red Cards", sum_col(team_b, player_b, "Red Cards"))

# ------------------- Profile & Participation -------------------
st.markdown("#### Profile & Participation")
p1, p2, p3, p4 = st.columns(4)
p1.metric("Pos A / B", f"{left_summary.get('position','—')} / {right_summary.get('position','—')}")
p2.metric("Age A / B", f"{left_summary.get('age','—')} / {right_summary.get('age','—')}")
apps_a = left_summary.get("appearances")
apps_b = right_summary.get("appearances")
team_games_a = left_summary.get("team_total_games")
team_games_b = right_summary.get("team_total_games")
p3.metric("Apps A", f"{apps_a}/{team_games_a}" if team_games_a else apps_a)
p4.metric("Apps B", f"{apps_b}/{team_games_b}" if team_games_b else apps_b)

# ------------------- Side-by-side metrics table (Player-page stats) -------------------
metrics_for_table = [
    "Minutes", "Avg Minutes", "Goals", "Assists", "Passes Completed",
    "Tackles", "Tackles (avg)", "Yellow Cards", "Red Cards", "Games Played"
]

rows = []
for key in metrics_for_table:
    ml = key.lower()
    if ml in ["avg minutes", "avg_minutes", "minutes/appearance"]:
        va = left_summary.get("avg_minutes"); vb = right_summary.get("avg_minutes")
    elif key == "Passes Completed":
        va = sum_col(team_a, player_a, "Passes Completed"); vb = sum_col(team_b, player_b, "Passes Completed")
    elif key == "Tackles":
        va = sum_col(team_a, player_a, "Tackles"); vb = sum_col(team_b, player_b, "Tackles")
    elif key == "Tackles (avg)":
        tsa = sum_col(team_a, player_a, "Tackles") or 0
        tpb_a = left_summary.get("appearances") or 0
        va = round(tsa / tpb_a, 2) if tpb_a > 0 else None
        tsb = sum_col(team_b, player_b, "Tackles") or 0
        tpb_b = right_summary.get("appearances") or 0
        vb = round(tsb / tpb_b, 2) if tpb_b > 0 else None
    elif key == "Yellow Cards":
        va = sum_col(team_a, player_a, "Yellow Cards"); vb = sum_col(team_b, player_b, "Yellow Cards")
    elif key == "Red Cards":
        va = sum_col(team_a, player_a, "Red Cards"); vb = sum_col(team_b, player_b, "Red Cards")
    elif key == "Games Played":
        va = f"{left_summary.get('appearances')}/15"; vb = f"{right_summary.get('appearances')}/15"
    elif ml in ["minutes", "minutes_sum", "total minutes"]:
        va = left_summary.get("minutes_sum"); vb = right_summary.get("minutes_sum")
    elif key in ["Goals", "Assists"]:
        va = left_summary.get(key); vb = right_summary.get(key)
    else:
        va = None; vb = None

    leader = "Tie"
    try:
        fa = float(va) if isinstance(va, (int, float)) else None
        fb = float(vb) if isinstance(vb, (int, float)) else None
        if fa is not None and fb is not None:
            if fa > fb: leader = player_a
            elif fb > fa: leader = player_b
    except Exception:
        pass

    rows.append({"Metric": key, player_a: va, player_b: vb, "Leader": leader})

cmp_df = pd.DataFrame(rows)
st.markdown("#### Side-by-side metrics")
st.dataframe(cmp_df, use_container_width=True)
