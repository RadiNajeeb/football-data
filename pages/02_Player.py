# pages/02_Player.py

# --- Make repo root importable when running from /pages (Streamlit Cloud safe) ---
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# ------------------------------------------------------------------------------

import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

# Use your own helpers (module import is robust)
import lib.data as data

# Load data using your helper (absolute path works locally & in Cloud)
DATA_PATH = ROOT / "database.csv"
DF = data.load_df(str(DATA_PATH))

st.title("Player Explorer")

# ---------------- Selections (reuse your helpers) ----------------
teams = data.get_teams(DF)
team = st.selectbox("Team", teams, index=0, key="players_team")

players = data.get_players_for_team(DF, team)
player = st.selectbox("Player", players, index=0, key="players_player")

# Filtered player dataframe (your CSV uses capitalized names)
p_df = DF[(DF["Team"] == team) & (DF["Player"] == player)].copy()
if p_df.empty:
    st.warning("No data for this player.")
    st.stop()

# ---------------- Basic headline metrics (totals) ----------------
def pick_col(df: pd.DataFrame, *aliases):
    """
    Return real column name for the first alias that exists (case-insensitive).
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
    ser = pd.to_numeric(df[col], errors="coerce").fillna(0)
    val = float(ser.sum())
    return int(val) if as_int else val

minutes     = sum_stat(p_df, "Minutes", "Mins", "Min") or 0
goals       = sum_stat(p_df, "Goals", "G") or 0
assists     = sum_stat(p_df, "Assists", "A") or 0
passes_cmp  = sum_stat(p_df, "Passes Completed", "Cmp", "PassesCompleted") or 0
tackles     = sum_stat(p_df, "Tackles", "Tkl") or 0
yc          = sum_stat(p_df, "Yellow Cards", "YC", "Yel") or 0
rc          = sum_stat(p_df, "Red Cards", "RC", "Red") or 0

st.subheader(player)
h1, h2, h3, h4 = st.columns(4)
h1.metric("Minutes", minutes)
h2.metric("Goals", goals)
h3.metric("Assists", assists)
h4.metric("Passes Completed", passes_cmp)

h5, h6, h7 = st.columns(3)
h5.metric("Tackles", tackles)
h6.metric("Red Cards", rc)
h7.metric("Yellow Cards", yc)

# ---------------- Advanced profile (rates, quality ratios, form) ----------------
def get_series(df: pd.DataFrame, *aliases):
    col = pick_col(df, *aliases)
    if col is None:
        return pd.Series(dtype=float)
    return pd.to_numeric(df[col], errors="coerce").fillna(0)

def per90(total):
    return float(total) / (minutes / 90.0) if minutes > 0 else 0.0

shots       = get_series(p_df, "Shots", "Sh").sum()
sot         = get_series(p_df, "Shots on Target", "SoT").sum()
passes_att  = get_series(p_df, "Passes Attempted", "Att", "Passes").sum()
kp          = get_series(p_df, "Key Passes", "KP").sum()
interc      = get_series(p_df, "Interceptions", "Int").sum()
drb_cmp     = get_series(p_df, "Dribbles Completed", "DrbCmp", "Dribbles Won").sum()
drb_att     = get_series(p_df, "Dribbles Attempted", "DrbAtt").sum()
duels_w     = get_series(p_df, "Duels Won").sum()
duels_t     = get_series(p_df, "Duels").sum()
aer_w       = get_series(p_df, "Aerials Won").sum()
aer_t       = get_series(p_df, "Aerials").sum()
xg          = get_series(p_df, "xG", "Expected Goals").sum()
xa          = get_series(p_df, "xA", "Expected Assists").sum()

adv = {
    "Goals/90":          per90(goals),
    "Assists/90":        per90(assists),
    "Shots/90":          per90(shots),
    "Key Passes/90":     per90(kp),
    "Tackles/90":        per90(tackles),
    "Interceptions/90":  per90(interc),
    "Dribbles/90":       per90(drb_cmp),
    "xG/90":             per90(xg),
    "xA/90":             per90(xa),
    "Pass Acc%":         (passes_cmp / passes_att * 100.0 if passes_att > 0 else np.nan),
    "Shot Acc%":         (sot / shots * 100.0 if shots > 0 else np.nan),
    "Dribble Succ%":     (drb_cmp / drb_att * 100.0 if drb_att > 0 else np.nan),
    "Duel Win%":         (duels_w / duels_t * 100.0 if duels_t > 0 else np.nan),
    "Aerial Win%":       (aer_w / aer_t * 100.0 if aer_t > 0 else np.nan),
    "Cards/90":          per90(yc + rc),
}

st.markdown("### Advanced profile")
keys = list(adv.keys())
cols = st.columns(5)
for i, k in enumerate(keys):
    v = adv[k]
    if pd.isna(v):
        txt = "—"
    else:
        txt = f"{v:.1f}%" if k.endswith("%") else f"{v:.2f}"
    cols[i % 5].metric(k, txt)

# Recent form sparkline (xG+xA over last 5 matches, if Date exists)
if "Date" in p_df.columns:
    last5 = p_df.sort_values("Date").tail(5).copy()
    last5["_xGA"] = get_series(last5, "xG", "Expected Goals").values + get_series(last5, "xA", "Expected Assists").values
    chart = alt.Chart(last5.reset_index(drop=True)).mark_line(point=True).encode(
        x=alt.X("index:O", title="Last 5"),
        y=alt.Y("_xGA:Q", title="xG+xA")
    ).properties(height=130)
    st.altair_chart(chart, use_container_width=True)

# Actions
a1, a2 = st.columns(2)
with a1:
    st.download_button(
        "Download player rows (CSV)",
        data=p_df.to_csv(index=False).encode("utf-8"),
        file_name=f"{player.replace(' ', '_')}.csv",
        mime="text/csv",
    )
with a2:
    # If you keep a compare page, this will deep-link to it:
    try:
        st.page_link("pages/03_Compare.py", label="Compare this player", icon="🔁")
    except Exception:
        pass

# Raw data at the bottom
with st.expander("Raw data"):
    default_cols = [c for c in ["Match", "Date", "Minutes", "Goals", "Assists", "Shots", "xG", "xA"] if c in p_df.columns]
    chosen = st.multiselect("Columns", list(p_df.columns), default=default_cols or list(p_df.columns))
    st.dataframe(p_df[chosen] if chosen else p_df, use_container_width=True)
