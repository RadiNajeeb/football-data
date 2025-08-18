# pages/01_Teams.py

# 1) Put project root on sys.path (so "lib" is importable when running from /pages)
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# 2) Third-party
import streamlit as st
import pandas as pd

# 3) Import the module (not names). This avoids "cannot import name ..." issues.
try:
    import lib.data as data
except Exception as e:
    # Minimal debug to understand what's wrong in the Cloud environment
    st.error(f"Could not import lib.data: {e}")
    st.write("ROOT on sys.path:", str(ROOT) in sys.path)
    st.write("Exists lib/data.py:", (ROOT / 'lib' / 'data.py').exists())
    st.stop()

# 4) OPTIONAL: show where the module came from (remove after it works)
# st.caption(f"lib.data loaded from: {getattr(data, '__file__', '?')}")

# ------------------ your page starts here ------------------

# Use attributes from the module instead of name imports
DATA_PATH = ROOT / "database.csv"
DF = data.load_df(str(DATA_PATH))
data.init_router_state()

st.title("Teams in La Liga")

teams = data.get_teams(DF)
team = st.selectbox(
    "Team", teams,
    index=(teams.index(getattr(st.session_state, "team", "")) if getattr(st.session_state, "team", "") in teams else 0),
    key="teams_team"
)

team_df = DF[DF["Team"] == team].copy()
if team_df.empty:
    st.warning("No data for this team.")
    st.stop()

scope = st.radio("Scope", ["Per game", "All games (aggregate)"], horizontal=True)

if scope == "Per game":
    t_with_keys, games = data.build_game_labels(team_df)
    labels = games["_GAME_LABEL"].tolist()
    default_idx = max(len(labels) - 1, 0)
    chosen_label = st.selectbox("Game", labels, index=default_idx, key=f"{team}_game_pick")
    game_key = games.loc[games["_GAME_LABEL"] == chosen_label, "_GAME_KEY"].iloc[0]

    game_df = t_with_keys[t_with_keys["_GAME_KEY"] == game_key].copy()

    st.subheader(f"{team} — {chosen_label}")
    data.kpi_row(game_df, aggregate=False)

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

    right = st.columns([2, 1])[1]
    numeric_cols = game_df.select_dtypes(include="number").columns.tolist()
    sort_by = right.selectbox("Sort by", ["None"] + numeric_cols)
    ascending = right.checkbox("Ascending", value=False)

    view_df = game_df.copy()
    if sort_by != "None" and sort_by in view_df.columns:
        view_df = view_df.sort_values(sort_by, ascending=ascending, kind="mergesort")

    with st.expander("Choose columns"):
        defaults = data.safe_cols(view_df, ["Player","Position","Minutes","Goals","Assists","GCA","SCA"])
        cols = st.multiselect("Columns", list(view_df.columns), default=defaults or list(view_df.columns))
        if cols:
            view_df = view_df[cols]

    st.dataframe(view_df, use_container_width=True)

else:
    agg_df = data.aggregate_team(team_df)

    st.subheader(f"{team} — All games (aggregate)")
    data.kpi_row(team_df, aggregate=True)

    prof = data.team_profile_kpis(team_df)
    st.markdown("#### Team snapshot (season/selected dataset)")
    a1, a2, a3, a4 = st.columns(4)
    a1.metric("Avg Age (unique players)", f"{prof['avg_age']:.2f}" if pd.notna(prof["avg_age"]) else "—")
    a2.metric("Median Age", f"{prof['median_age']:.1f}" if pd.notna(prof["median_age"]) else "—")
    a3.metric("GCA (total)", int(prof["gca_total"]) if pd.notna(prof["gca_total"]) else "—")
    a4.metric("SCA (total)", int(prof["sca_total"]) if pd.notna(prof["sca_total"]) else "—")

    b1, b2 = st.columns(2)
    b1.metric("xG (total)", f"{prof['xg_total']:.2f}" if pd.notna(prof["xg_total"]) else "—")
    b2.metric("xA (total)", f"{prof['xa_total']:.2f}" if pd.notna(prof["xa_total"]) else "—")

    right = st.columns([2, 1])[1]
    num_cols = [c for c in agg_df.columns if c not in ["Player","Position"]]
    sort_by = right.selectbox("Sort by", ["None"] + num_cols)
    ascending = right.checkbox("Ascending", value=False, key=f"{team}_agg_asc")

    view_df = agg_df.copy()
    if sort_by != "None" and sort_by in view_df.columns:
        view_df = view_df.sort_values(sort_by, ascending=ascending, kind="mergesort")

    with st.expander("Choose columns"):
        defaults = data.safe_cols(view_df, ["Player","Position","Minutes","Goals","Assists","GCA","SCA","xG","xA"])
        cols = st.multiselect("Columns", list(view_df.columns), default=defaults or list(view_df.columns), key=f"{team}_agg_cols")
        if cols:
            view_df = view_df[cols]

    st.dataframe(view_df, use_container_width=True)
