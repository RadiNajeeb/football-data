# pages/01_Teams.py
import pandas as pd
import streamlit as st
from lib.data import (
    load_df, get_teams, get_players_for_team,
    kpi_row, build_game_labels, aggregate_team, goto, init_router_state, safe_cols,
    team_profile_kpis, inject_theme_css
)

st.set_page_config(layout="wide")

# ---------- boot ----------
DF = load_df("database.csv")
init_router_state()
inject_theme_css()

st.title("Teams in La Liga")

# ---------- selectors ----------
teams = get_teams(DF)
team = st.selectbox(
    "Team", teams,
    index=(teams.index(st.session_state.team) if st.session_state.team in teams else 0),
    key="teams_team"
)

team_df = DF[DF["Team"] == team].copy()
if team_df.empty:
    st.warning("No data for this team.")
    st.stop()

scope = st.radio("Scope", ["Per game", "All games (aggregate)"], horizontal=True)

# ------------------ PER GAME ------------------
if scope == "Per game":
    t_with_keys, games = build_game_labels(team_df)
    labels = games["_GAME_LABEL"].tolist()
    default_idx = max(len(labels) - 1, 0)  # latest by default
    chosen_label = st.selectbox("Game", labels, index=default_idx, key=f"{team}_game_pick")
    game_key = games.loc[games["_GAME_LABEL"] == chosen_label, "_GAME_KEY"].iloc[0]

    game_df = t_with_keys[t_with_keys["_GAME_KEY"] == game_key].copy()

    st.subheader(f"{team} — {chosen_label}")
    kpi_row(game_df, aggregate=False)

    # ---- Extra subheading KPIs (this game) ----
    st.markdown("#### Team snapshot (this game)")
    c1, c2, c3, c4 = st.columns(4)

    g_appear = game_df.copy()
    if "Minutes" in g_appear.columns:
        g_appear = g_appear[g_appear["Minutes"].fillna(0) > 0]

    if "Age" in g_appear.columns:
        ages = g_appear.drop_duplicates("Player")["Age"]
        ages = pd.to_numeric(ages, errors="coerce").dropna()
        c1.metric("Avg Age (XI/bench used)", f"{ages.mean():.2f}" if not ages.empty else "—")
        c2.metric("Median Age", f"{ages.median():.1f}" if not ages.empty else "—")
    else:
        c1.metric("Avg Age (XI/bench used)", "—")
        c2.metric("Median Age", "—")

    c3.metric("GCA (team)", int(game_df["GCA"].sum()) if "GCA" in game_df.columns else "—")
    c4.metric("SCA (team)", int(game_df["SCA"].sum()) if "SCA" in game_df.columns else "—")

    # ---- Sorting & table ----
    right = st.columns([2,1])[1]
    numeric_cols = game_df.select_dtypes(include="number").columns.tolist()
    sort_by = right.selectbox("Sort by", ["None"] + numeric_cols)
    ascending = right.checkbox("Ascending", value=False)

    view_df = game_df.copy()
    if sort_by != "None" and sort_by in view_df.columns:
        view_df = view_df.sort_values(sort_by, ascending=ascending, kind="mergesort")

    with st.expander("Choose columns"):
        defaults = safe_cols(view_df, ["Player","Position","Minutes","Goals","Assists","GCA","SCA"])
        cols = st.multiselect("Columns", list(view_df.columns), default=defaults or list(view_df.columns))
        if cols: 
            view_df = view_df[cols]

    st.dataframe(view_df, use_container_width=True)

# ------------------ AGGREGATE ------------------
else:
    agg_df = aggregate_team(team_df)

    st.subheader(f"{team} — All games (aggregate)")
    kpi_row(team_df, aggregate=True)

    # ---- Extra subheading KPIs (season/profile) ----
    prof = team_profile_kpis(team_df)  # pass raw per-game df for correct totals
    st.markdown("#### Team snapshot (season/selected dataset)")
    a1, a2, a3, a4 = st.columns(4)
    a1.metric("Avg Age (unique players)", f"{prof['avg_age']:.2f}" if pd.notna(prof["avg_age"]) else "—")
    a2.metric("Median Age", f"{prof['median_age']:.1f}" if pd.notna(prof["median_age"]) else "—")
    a3.metric("GCA (total)", int(prof["gca_total"]) if pd.notna(prof["gca_total"]) else "—")
    a4.metric("SCA (total)", int(prof["sca_total"]) if pd.notna(prof["sca_total"]) else "—")

    b1, b2 = st.columns(2)
    b1.metric("xG (total)", f"{prof['xg_total']:.2f}" if pd.notna(prof["xg_total"]) else "—")
    b2.metric("xA (total)", f"{prof['xa_total']:.2f}" if pd.notna(prof["xa_total"]) else "—")

    # ---- Sorting & table ----
    right = st.columns([2,1])[1]
    num_cols = [c for c in agg_df.columns if c not in ["Player","Position"]]
    sort_by = right.selectbox("Sort by", ["None"] + num_cols)
    ascending = right.checkbox("Ascending", value=False, key=f"{team}_agg_asc")

    view_df = agg_df.copy()
    if sort_by != "None" and sort_by in view_df.columns:
        view_df = view_df.sort_values(sort_by, ascending=ascending, kind="mergesort")

    with st.expander("Choose columns"):
        defaults = safe_cols(view_df, ["Player","Position","Minutes","Goals","Assists","GCA","SCA","xG","xA"])
        cols = st.multiselect("Columns", list(view_df.columns), default=defaults or list(view_df.columns), key=f"{team}_agg_cols")
        if cols: 
            view_df = view_df[cols]

    st.dataframe(view_df, use_container_width=True)
