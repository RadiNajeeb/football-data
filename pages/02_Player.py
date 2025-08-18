# pages/02_Player.py

# --- Make project root importable when running from pages/ (Streamlit Cloud) ---
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# ------------------------------------------------------------------------------

import streamlit as st
import pandas as pd

# Use your local helpers
import lib.data as data  # module import is more robust than "from lib.data import ..."

# Load data (absolute path works both locally and in Cloud)
DATA_PATH = ROOT / "database.csv"
DF = data.load_df(str(DATA_PATH))

st.title("Player Explorer")

# -------- Selections (reuse your helpers so we don't rely on column names) ----
teams = data.get_teams(DF)
team = st.selectbox("Team", teams, index=0, key="players_team")

players = data.get_players_for_team(DF, team)
player = st.selectbox("Player", players, index=0, key="players_player")

# Filter for the chosen player (your CSV uses capitalized names)
p_df = DF[(DF["Team"] == team) & (DF["Player"] == player)].copy()
if p_df.empty:
    st.warning("No data for this player.")
    st.stop()

# ------------------------- Flexible stat lookup -------------------------------
def pick_col(df: pd.DataFrame, *aliases):
    """
    Return the first matching column in df from a list of aliases (case-insensitive).
    If none found, return None.
    """
    cols_lower = {c.lower(): c for c in df.columns}
    for name in aliases:
        c = cols_lower.get(name.lower())
        if c is not None:
            return c
    return None

def sum_stat(df: pd.DataFrame, *aliases, as_int=True):
    col = pick_col(df, *aliases)
    if col is None:
        return None
    ser = pd.to_numeric(df[col], errors="coerce")
    val = float(ser.fillna(0).sum())
    return int(val) if as_int else val

def mean_stat(df: pd.DataFrame, *aliases, decimals=2):
    col = pick_col(df, *aliases)
    if col is None:
        return None
    ser = pd.to_numeric(df[col], errors="coerce")
    if ser.notna().any():
        return round(float(ser.mean()), decimals)
    return None

# ---------------------------- Build metrics -----------------------------------
# Add/adjust aliases to match your CSV headers
metrics = [
    ("Matches",          sum_stat(p_df, "Matches", "Apps", "Appearances")),
    ("Minutes",          sum_stat(p_df, "Minutes", "Mins")),
    ("Goals",            sum_stat(p_df, "Goals", "G")),
    ("Assists",          sum_stat(p_df, "Assists", "A")),
    ("Shots",            sum_stat(p_df, "Shots", "Sh", "Total Shots")),
    ("Shots on Target",  sum_stat(p_df, "Shots on Target", "SoT")),
    ("xG (total)",       mean_stat(p_df, "xG", "Expected Goals", decimals=2)),  # mean shown; switch to sum_stat if you want totals
    ("xA (total)",       mean_stat(p_df, "xA", "Expected Assists", decimals=2)),
    ("Passes Completed", sum_stat(p_df, "Passes Completed", "Cmp", "PassesCompleted")),
    ("Key Passes",       sum_stat(p_df, "Key Passes", "KP")),
    ("Dribbles Completed", sum_stat(p_df, "Dribbles Completed", "Dribbles Won", "DrbCmp")),
    ("Tackles",          sum_stat(p_df, "Tackles", "Tkl")),
    ("Interceptions",    sum_stat(p_df, "Interceptions", "Int")),
    ("Yellow Cards",     sum_stat(p_df, "Yellow Cards", "YC", "Yel")),
    ("Red Cards",        sum_stat(p_df, "Red Cards", "RC", "Red")),
]

# Keep only the stats that actually exist in your data
metrics = [(name, val) for (name, val) in metrics if val is not None]

# Guarantee at least 6 metrics by prioritizing common ones
priority_order = ["Minutes", "Goals", "Assists", "Shots", "xG (total)", "xA (total)", "Passes Completed", "Tackles"]
metrics.sort(key=lambda x: (priority_order.index(x[0]) if x[0] in priority_order else 999, x[0]))

st.subheader(player)
cols = st.columns(4)
for i, (label, value) in enumerate(metrics[:12]):  # show up to 12 metrics neatly
    cols[i % 4].metric(label, value)

# ----------------------------- Raw data ---------------------------------------
with st.expander("Raw data"):
    # Suggest sensible defaults if available
    default_cols = [c for c in ["Match", "Date", "Minutes", "Goals", "Assists", "Shots", "xG", "xA"] if c in p_df.columns]
    chosen = st.multiselect("Columns", list(p_df.columns), default=default_cols or list(p_df.columns))
    st.dataframe(p_df[chosen] if chosen else p_df, use_container_width=True)
