# pages/03_Compare.py
import streamlit as st
import pandas as pd
from lib.data import load_df, get_teams, get_players_for_team, build_game_labels

st.set_page_config(layout="wide")  # make the page full width

DF = load_df("database.csv")

st.title("Compare Players")

# ---------------- Shared metric choices (apply to both sides) ----------------
# Curated metrics (only include if present), plus a virtual metric "Avg Minutes".
curated = ["Goals", "Assists", "Shots", "xG", "xA", "GCA", "SCA", "Minutes"]
numeric_cols = DF.select_dtypes(include="number").columns.tolist()
curated_avail = [m for m in curated if m in numeric_cols]
other_numeric = [c for c in numeric_cols if c not in curated_avail]

# Add our virtual metric at the end
metric_options = curated_avail + other_numeric + ["Avg Minutes"]

default_metrics = [m for m in ["Goals", "Assists", "Minutes", "Avg Minutes"] if m in metric_options]

metrics = st.multiselect(
    "Metrics (apply to both sides)",
    metric_options,
    default=default_metrics,
)

st.divider()

# ---------------- Helpers ----------------
def appearances_for(pdf: pd.DataFrame) -> int:
    """Games the player featured in. Prefer Minutes>0; else number of rows."""
    if pdf.empty:
        return 0
    # Count appearances per game (any row with Minutes>0 for that game)
    p_with_keys, _ = build_game_labels(pdf)
    if "Minutes" in p_with_keys.columns:
        return int(
            p_with_keys.groupby("_GAME_KEY")["Minutes"]
            .apply(lambda s: (pd.to_numeric(s, errors="coerce").fillna(0) > 0).any())
            .sum()
        )
    return int(p_with_keys["_GAME_KEY"].nunique())

def team_total_games(df: pd.DataFrame, team: str) -> int:
    """Count only games actually played by the team (sum of Minutes per game > 0)."""
    tdf = df[df["Team"] == team].copy()
    if tdf.empty:
        return 0
    t_with_keys, _ = build_game_labels(tdf)
    if "Minutes" in t_with_keys.columns:
        per_game_minutes = (
            pd.to_numeric(t_with_keys["Minutes"], errors="coerce")
            .fillna(0)
            .groupby(t_with_keys["_GAME_KEY"])
            .sum()
        )
        return int((per_game_minutes > 0).sum())
    return int(t_with_keys["_GAME_KEY"].nunique())

def summarize_player(df: pd.DataFrame, team: str | None, player: str | None, want_metrics: list[str]) -> dict:
    """Return totals + virtual metrics for a single player."""
    if not team or not player:
        return {}

    pdf = df[(df["Team"] == team) & (df["Player"] == player)].copy()
    if pdf.empty:
        return {}

    totals = pdf.select_dtypes(include="number").sum(numeric_only=True)

    out = {}
    # real numeric metrics
    for m in want_metrics:
        if m in totals.index:
            out[m] = float(totals[m])

    # virtual: Avg Minutes = Minutes / Appearances
    apps = appearances_for(pdf)
    mins_total = float(totals["Minutes"]) if "Minutes" in totals.index else 0.0
    if "Avg Minutes" in want_metrics:
        out["Avg Minutes"] = (mins_total / apps) if apps > 0 else None

    # identity / extras
    out["_player"] = player
    out["_team"] = team
    out["_apps"] = apps
    out["_minutes"] = mins_total if mins_total else None
    if "Position" in pdf.columns:
        p = pdf["Position"].dropna()
        out["_position"] = p.iloc[0] if not p.empty else "—"
    if "Age" in pdf.columns:
        a = pdf["Age"].dropna()
        out["_age"] = int(a.iloc[0]) if not a.empty else None

    return out

def fmt_num(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "—"
    return int(v) if isinstance(v, (int, float)) and float(v).is_integer() else f"{v:.2f}"

def header_block(values: dict, total_games: int):
    """Top identity + quick facts for a side."""
    if not values:
        return
    st.subheader(values.get("_player", "—"))

    c1, c2, c3, c4, c5, c6 = st.columns(6)  # appearances included in the top row

    c1.metric("Team", values.get("_team", "—"))
    c2.metric("Position", values.get("_position", "—"))

    m = values.get("_minutes", None)
    c3.metric("Minutes (sum)", "—" if m is None else int(m) if isinstance(m, (int, float)) and float(m).is_integer() else f"{m:.1f}")

    a = values.get("_age", None)
    c4.metric("Age", "—" if a is None else a)

    apps = values.get("_apps", None)
    c5.metric("Appearances", f"{apps}/{total_games}" if (apps is not None and total_games is not None) else "—")

    # header Avg Minutes computed from existing minutes/apps
    avg_m = (m / apps) if (m is not None and apps and apps > 0) else None
    c6.metric("Avg Minutes", "—" if avg_m is None else f"{avg_m:.2f}")

def metric_grid(values: dict, metric_names: list[str]):
    if not values:
        st.info("Pick a team and a player.")
        return
    rows = (len(metric_names) + 3) // 4
    idx = 0
    for _ in range(rows):
        cols = st.columns(4)
        for c in cols:
            if idx >= len(metric_names):
                break
            name = metric_names[idx]
            c.metric(name, fmt_num(values.get(name)))
            idx += 1

# ---------------- Two-side layout ----------------
left, right = st.columns(2, gap="large")

with left:
    st.markdown("### Player 1")
    teams = get_teams(DF)
    team_a = st.selectbox("Team A", teams, key="cmp_team_a")
    players_a = get_players_for_team(DF, team_a)
    player_a = st.selectbox("Player A", players_a, key="cmp_player_a")
    vals_a = summarize_player(DF, team_a, player_a, metrics)
    total_a = team_total_games(DF, team_a)
    header_block(vals_a, total_a)
    metric_grid(vals_a, metrics)

with right:
    st.markdown("### Player 2")
    teams = get_teams(DF)
    team_b = st.selectbox("Team B", teams, key="cmp_team_b")
    players_b = get_players_for_team(DF, team_b)
    player_b = st.selectbox("Player B", players_b, key="cmp_player_b")
    vals_b = summarize_player(DF, team_b, player_b, metrics)
    total_b = team_total_games(DF, team_b)
    header_block(vals_b, total_b)
    metric_grid(vals_b, metrics)

st.divider()

# ---------------- Combined table (rows = metrics) ----------------
if metrics and vals_a and vals_b:
    table = pd.DataFrame({
        "Metric": metrics,
        vals_a.get("_player", "Side A"): [vals_a.get(m) for m in metrics],
        vals_b.get("_player", "Side B"): [vals_b.get(m) for m in metrics],
    })
    # Pretty numbers
    for col in table.columns[1:]:
        table[col] = table[col].apply(
            lambda v: None if v is None else (int(v) if isinstance(v, (int, float)) and float(v).is_integer() else round(float(v), 2))
        )
    st.markdown("### Side-by-side table")
    st.dataframe(table, use_container_width=True)