# lib/data.py
import re
import pandas as pd
import streamlit as st

# ---------- Loading & cleaning ----------
NUMERIC_CANDIDATES = [
    # core
    "Age","Minutes","Goals","Assists","Shots","xG","xA",
    "Goals/90","Assists/90","Shots/90","xG/90","xA/90",
    # creators (new)
    "GCA","SCA","GCA/90","SCA/90"
]

def _coerce_numeric(series: pd.Series) -> pd.Series:
    """
    Extract the first numeric token from any messy string and coerce to number.
    Handles '25-159', '30 yrs', '12.5', etc. Non-numeric -> NaN.
    """
    extracted = series.astype(str).str.extract(r'(-?\d+(?:\.\d+)?)', expand=False)
    return pd.to_numeric(extracted, errors="coerce")

@st.cache_data
def load_df(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip()
    # normalize common headers
    rename = {"Club":"Team","Squad":"Team","Name":"Player","player":"Player","Pos":"Position"}
    df = df.rename(columns={k:v for k,v in rename.items() if k in df.columns})
    # numeric cleanup
    for col in NUMERIC_CANDIDATES:
        if col in df.columns:
            df[col] = _coerce_numeric(df[col])
    return df

# ---------- Router (deep-linkable) ----------
def _get_query_params():
    try:
        return st.query_params  # Streamlit ≥1.37
    except Exception:
        return {}

def init_router_state():
    qs = _get_query_params()
    if "view" not in st.session_state:
        st.session_state.view = qs.get("view", ["home"])[0] if isinstance(qs.get("view"), list) else qs.get("view", "home")
    if "team" not in st.session_state:
        st.session_state.team = qs.get("team", [None])[0] if isinstance(qs.get("team"), list) else qs.get("team")
    if "player" not in st.session_state:
        st.session_state.player = qs.get("player", [None])[0] if isinstance(qs.get("player"), list) else qs.get("player")

def goto(view: str, team: str|None=None, player: str|None=None):
    st.session_state.view = view
    st.session_state.team = team
    st.session_state.player = player
    try:
        params = {"view": view}
        if team: params["team"] = team
        if player: params["player"] = player
        st.query_params.update(params)
    except Exception:
        pass  # older Streamlit—just keep session_state

# ---------- Small utilities ----------
def get_teams(df: pd.DataFrame) -> list[str]:
    return sorted(df["Team"].dropna().unique().tolist())

def get_players_for_team(df: pd.DataFrame, team: str) -> list[str]:
    return sorted(df.loc[df["Team"] == team, "Player"].dropna().unique().tolist())

def metric_num(col, label: str, value):
    if pd.isna(value):
        col.metric(label, "—")
    else:
        try:
            iv = int(value)
            if abs(iv - float(value)) < 1e-9:
                col.metric(label, iv)
            else:
                col.metric(label, value)
        except Exception:
            col.metric(label, value)

def kpi_row(team_df: pd.DataFrame, aggregate: bool) -> None:
    """
    Team KPIs row.

    aggregate=True  -> group by Player first, then sum numeric columns (season/aggregate view).
    aggregate=False -> per-game view; show Match Minutes (max minutes any player played),
                       not the sum across players (which ~990).
    """
    if aggregate:
        # Aggregate across games: avoid double counting by grouping per player first
        num_cols = team_df.select_dtypes(include="number").columns.tolist()
        df = team_df.groupby("Player", dropna=True)[num_cols].sum(numeric_only=True).reset_index()

        players_val = team_df["Player"].nunique()
        minutes_label = "Minutes"
        minutes_val = df["Minutes"].sum() if "Minutes" in df.columns else pd.NA
        goals_val   = df["Goals"].sum()   if "Goals"   in df.columns else pd.NA
        assists_val = df["Assists"].sum() if "Assists" in df.columns else pd.NA

    else:
        # Per-game: compute match duration as the maximum minutes any player logged
        df = team_df  # single game's rows
        players_val = df["Player"].nunique()
        minutes_label = "Match Minutes"

        if "Minutes" in df.columns:
            mins = pd.to_numeric(df["Minutes"], errors="coerce")
            minutes_val = int(mins.max()) if not mins.dropna().empty else pd.NA
        else:
            minutes_val = pd.NA

        goals_val   = df["Goals"].sum()   if "Goals"   in df.columns else pd.NA
        assists_val = df["Assists"].sum() if "Assists" in df.columns else pd.NA

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Players", int(players_val))
    metric_num(c2, minutes_label, minutes_val)
    metric_num(c3, "Goals", goals_val)
    metric_num(c4, "Assists", assists_val)

def safe_cols(df, wanted):
    return [c for c in wanted if c in df.columns]

# ---------- UI helpers ----------
def inject_theme_css():
    """Inject global CSS for dark red theme and subtle animations."""
    st.markdown(
        """
        <style>
        :root {
            --primary: #8B0000; /* dark red */
            --bg: #1a0000; /* dark red background */
            --bg-2: #260000; /* deeper dark red */
            --text: #f5f5f5;
            --accent: #5c0b0b; /* accent red */
            --green: #0b5326; /* dark green for accents/buttons */
        }
        html, body, [data-testid="stAppViewContainer"] {
            background-color: var(--bg);
            color: var(--text);
        }
        [data-testid="stHeader"] { background: transparent; }
        
        /* Widen main container */
        [data-testid="stAppViewContainer"] > .main {
            max-width: 1680px;
            padding-left: 2rem;
            padding-right: 2rem;
        }
        
        /* Inputs and buttons */
        .stButton button, .stDownloadButton button {
            background: linear-gradient(135deg, var(--primary), var(--green));
            color: #ffffff;
            border: 1px solid rgba(255,255,255,0.14);
            border-radius: 10px;
            transition: transform 120ms ease, box-shadow 120ms ease, filter 120ms ease;
        }
        .stButton button:hover, .stDownloadButton button:hover {
            transform: translateY(-1px);
            box-shadow: 0 6px 18px rgba(139,0,0,0.45), 0 2px 10px rgba(11,83,38,0.35);
            filter: brightness(1.03);
        }
        
        /* Selects, radios */
        .stSelectbox, .stRadio, .stTextInput, .stNumberInput {
            background-color: transparent;
        }
        
        /* Dataframes */
        [data-testid="stDataFrame"] div { color: var(--text); }
        [data-testid="stDataFrame"] table { border: 1px solid rgba(255,255,255,0.08); }
        
        /* Metric cards */
        div[data-testid="stMetric"] {
            background: linear-gradient(135deg, rgba(139,0,0,0.30), rgba(11,83,38,0.28));
            border: 1px solid rgba(139,0,0,0.45);
            border-radius: 12px;
            padding: 12px 14px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.35), 0 0 12px rgba(11,83,38,0.15);
        }
        div[data-testid="stMetric"] > label {
            color: #f0eaea !important;
            font-weight: 600;
            white-space: normal;
            line-height: 1.2;
        }
        div[data-testid="stMetric"] [data-testid="stMetricValue"] {
            color: #ffffff !important;
            /* Ensure values always fit: responsive size and wrapping */
            font-size: clamp(16px, 2.2vw, 28px);
            line-height: 1.1;
            white-space: normal;
            word-break: break-word;
            overflow: visible;
            text-overflow: unset;
            max-width: 100%;
            display: block;
        }
        
        /* Section titles */
        h1, h2, h3 { animation: fadeInUp 450ms ease-out both; }
        @keyframes fadeInUp {
            from { opacity: 0; transform: translateY(6px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        /* Emphasize subheaders */
        .stMarkdown h4 { color: #ffd0d0; }
        
        /* Pulse small accents */
        .pulse { animation: pulse 1.6s ease-in-out infinite; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.7; } }
        </style>
        """,
        unsafe_allow_html=True,
    )

# ---------- Game detection & labeling ----------
def find_game_columns(df: pd.DataFrame) -> dict:
    def find(pattern):
        return next((c for c in df.columns if re.search(pattern, c, re.I)), None)
    return dict(
        date=find(r'date|match.?day|kick.?off'),
        opp=find(r'opponent|opp|against'),
        rnd=find(r'round|gw|gameweek|matchweek|md'),
        ha=find(r'home.?away|ha|isHome'),
        venue=find(r'venue|home|away'),
        mid=find(r'match.?id|fixture|game.?id'),
        mname=find(r'(?:^|_)match$|fixture$')
    )

def build_game_labels(team_df: pd.DataFrame):
    cols = find_game_columns(team_df)
    t = team_df.copy()

    # stable key
    if cols["mid"]:
        t["_GAME_KEY"] = t[cols["mid"]].astype(str)
    else:
        parts = [c for k,c in cols.items() if k in ("date","opp","rnd","mname") and c]
        if parts:
            t["_GAME_KEY"] = t[parts].astype(str).agg(" | ".join, axis=1)
        else:
            t["_GAME_KEY"] = t.index.astype(str)

    # friendly label
    def mk_label(row):
        d = str(row.get(cols["date"])) if cols["date"] else ""
        opp = str(row.get(cols["opp"])) if cols["opp"] else ""
        ha  = str(row.get(cols["ha"]))  if cols["ha"] else ""
        venue = str(row.get(cols["venue"])) if cols["venue"] else ""
        mname = str(row.get(cols["mname"])) if cols["mname"] else ""

        at_or_vs = "vs"
        if ha:
            if str(ha).strip().lower() in ("a","away","false","0"): at_or_vs = "@"
        elif venue and re.search(r'away', venue, re.I):
            at_or_vs = "@"

        if d and opp: return f"{d} {at_or_vs} {opp}"
        if mname:     return mname
        if opp:       return f"{at_or_vs} {opp}"
        return row["_GAME_KEY"]

    t["_GAME_LABEL"] = t.apply(mk_label, axis=1)

    try:
        dts = pd.to_datetime(t[cols["date"]], errors="coerce") if cols["date"] else None
        if dts is not None:
            games = t[["_GAME_KEY","_GAME_LABEL"]].assign(_date=dts).drop_duplicates().sort_values("_date")
        else:
            games = t[["_GAME_KEY","_GAME_LABEL"]].drop_duplicates()
    except Exception:
        games = t[["_GAME_KEY","_GAME_LABEL"]].drop_duplicates()

    return t, games

def aggregate_team(team_df: pd.DataFrame) -> pd.DataFrame:
    num_cols = team_df.select_dtypes(include="number").columns.tolist()
    group_cols = ["Player"] + [c for c in ["Position"] if c in team_df.columns]
    return team_df.groupby(group_cols, dropna=False)[num_cols].sum(numeric_only=True).reset_index()

# ---------- Team demographics/profile KPIs ----------
def _first_non_null(series: pd.Series):
    s = series.dropna()
    return s.iloc[0] if not s.empty else pd.NA

def team_unique_players_frame(team_df: pd.DataFrame) -> pd.DataFrame:
    """
    Collapse per-game rows to one row per player for demographics (Age/Position).
    """
    cols = ["Player"]
    if "Age" in team_df.columns: cols.append("Age")
    if "Position" in team_df.columns: cols.append("Position")
    if len(cols) == 1:
        return team_df[["Player"]].drop_duplicates()

    return (
        team_df[cols]
        .sort_values("Player")
        .groupby("Player", as_index=False)
        .agg({"Age": _first_non_null, "Position": _first_non_null})
    )

def team_profile_kpis(team_df: pd.DataFrame) -> dict:
    """
    KPIs for the team across ALL games:
      - avg_age, median_age (unique players)
      - totals for GCA, SCA, xG, xA (sums over per-game rows)
    """
    out = {
        "avg_age": pd.NA, "median_age": pd.NA, "age_n": 0,
        "gca_total": pd.NA, "sca_total": pd.NA, "xg_total": pd.NA, "xa_total": pd.NA,
    }

    up = team_unique_players_frame(team_df)
    if "Age" in up.columns:
        ages = pd.to_numeric(up["Age"], errors="coerce").dropna()
        if not ages.empty:
            out["avg_age"] = float(ages.mean())
            out["median_age"] = float(ages.median())
            out["age_n"] = int(ages.shape[0])

    nums = team_df.select_dtypes(include="number")
    if "GCA" in nums: out["gca_total"] = float(nums["GCA"].sum())
    if "SCA" in nums: out["sca_total"] = float(nums["SCA"].sum())
    if "xG"  in nums: out["xg_total"]  = float(nums["xG"].sum())
    if "xA"  in nums: out["xa_total"]  = float(nums["xA"].sum())

    return out