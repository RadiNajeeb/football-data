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