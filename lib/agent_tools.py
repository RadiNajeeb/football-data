# lib/agent_tools.py
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
from lib.data import load_df, get_teams, get_players_for_team, build_game_labels

# --------- lazy df ----------
_DF: Optional[pd.DataFrame] = None
def df() -> pd.DataFrame:
    global _DF
    if _DF is None:
        _DF = load_df("database.csv")
    return _DF

# --------- helpers ----------
def _with_game_keys(frame: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    return build_game_labels(frame)

def _appearances(pdf: pd.DataFrame) -> int:
    if pdf.empty:
        return 0
    p_with_keys, _ = _with_game_keys(pdf)
    if "Minutes" in p_with_keys.columns:
        return int(
            p_with_keys.groupby("_GAME_KEY")["Minutes"]
            .apply(lambda s: (pd.to_numeric(s, errors="coerce").fillna(0) > 0).any())
            .sum()
        )
    return int(p_with_keys["_GAME_KEY"].nunique())

def _team_total_games(team: str) -> int:
    tdf = df()[df()["Team"] == team]
    if tdf.empty:
        return 0
    t_with_keys, _ = _with_game_keys(tdf)
    if "Minutes" in t_with_keys.columns:
        per_game_minutes = (
            pd.to_numeric(t_with_keys["Minutes"], errors="coerce")
            .fillna(0)
            .groupby(t_with_keys["_GAME_KEY"])
            .sum()
        )
        return int((per_game_minutes > 0).sum())
    return int(t_with_keys["_GAME_KEY"].nunique())

def _player_slice(team: str, player: str) -> pd.DataFrame:
    return df()[(df()["Team"] == team) & (df()["Player"] == player)].copy()

# --------- team age ----------
def _team_avg_age_xi(team: str) -> Optional[float]:
    tdf = df()[df()["Team"] == team].copy()
    if tdf.empty or "Age" not in tdf.columns:
        return None
    t_with_keys, _ = _with_game_keys(tdf)
    if "_GAME_KEY" not in t_with_keys.columns or "Minutes" not in t_with_keys.columns:
        return None
    t_with_keys["Minutes"] = pd.to_numeric(t_with_keys["Minutes"], errors="coerce").fillna(0)
    t_with_keys["Age"] = pd.to_numeric(t_with_keys["Age"], errors="coerce")
    xi = t_with_keys[t_with_keys["Minutes"] > 0]
    if xi.empty:
        return None
    per_game_avg = xi.groupby("_GAME_KEY")["Age"].mean(numeric_only=True)
    if per_game_avg.empty:
        return None
    return float(per_game_avg.mean())

def _team_avg_age_squad(team: str) -> Optional[float]:
    tdf = df()[df()["Team"] == team].copy()
    if tdf.empty or "Age" not in tdf.columns:
        return None
    tdf["Age"] = pd.to_numeric(tdf["Age"], errors="coerce")
    player_age = (
        tdf.dropna(subset=["Age"])
           .groupby("Player", as_index=False)["Age"]
           .first()
    )
    if player_age.empty:
        return None
    return float(player_age["Age"].mean())

# --------- core actions (pure python over CSV) ----------
def act_list_teams(**_) -> List[str]:
    return get_teams(df())

def act_list_players(team: str, **_) -> List[str]:
    return get_players_for_team(df(), team)

def act_player_summary(team: str, player: str, **_) -> Dict[str, Any]:
    pdf = _player_slice(team, player)
    if pdf.empty:
        return {"error": "No data for this player/team.", "team": team, "player": player}

    totals = pdf.select_dtypes(include="number").sum(numeric_only=True)
    apps = _appearances(pdf)
    minutes = float(totals.get("Minutes", 0.0))
    avg_minutes = (minutes / apps) if apps > 0 else None
    pos = pdf["Position"].dropna().iloc[0] if "Position" in pdf.columns and not pdf["Position"].dropna().empty else "—"
    age = int(pdf["Age"].dropna().iloc[0]) if "Age" in pdf.columns and not pdf["Age"].dropna().empty else None

    out = {
        "team": team,
        "player": player,
        "position": pos,
        "age": age,
        "appearances": apps,
        "team_total_games": _team_total_games(team),
        "minutes_sum": minutes,
        "avg_minutes": avg_minutes,
    }
    for m in ["Goals", "Assists", "Shots", "xG", "xA", "GCA", "SCA"]:
        if m in totals.index:
            out[m] = float(totals[m])
    return out

def act_compare_players(team_a: str, player_a: str, team_b: str, player_b: str, metrics: Optional[List[str]] = None, **_) -> Dict[str, Any]:
    left = act_player_summary(team_a, player_a)
    right = act_player_summary(team_b, player_b)
    if metrics is None:
        metrics = ["Goals", "Assists", "Minutes", "avg_minutes"]
    rows = []
    for m in metrics:
        key = m
        ml = m.lower().strip()
        if ml in ["avg minutes", "avg_minutes", "minutes/appearance"]:
            key = "avg_minutes"
        elif ml in ["minutes", "total minutes", "minutes_sum"]:
            key = "minutes_sum"
        rows.append({
            "metric": m,
            player_a: left.get(key),
            player_b: right.get(key),
        })
    return {"left": left, "right": right, "table": rows}

def act_top_players(metric: str, team: Optional[str] = None, top_n: int = 5, **_) -> List[Dict[str, Any]]:
    data = df().copy()
    if team:
        data = data[data["Team"] == team]
    if metric not in data.columns:
        return []
    agg = data.groupby(["Team","Player"], dropna=True)[metric].sum(numeric_only=True).reset_index()
    top = agg.sort_values(metric, ascending=False).head(max(1, min(50, int(top_n))))
    return [{"team": r["Team"], "player": r["Player"], metric: float(r[metric])} for _, r in top.iterrows()]

def act_best_player_by_metric(metric: str = "Goals", team: Optional[str] = None, **_) -> Dict[str, Any]:
    res = act_top_players(metric=metric, team=team, top_n=1)
    if not res:
        return {"error": f"No data for metric '{metric}'", "team": team}
    r = res[0]
    return {"metric": metric, "team": team or "ALL", "player": r["player"], "player_team": r["team"], "value": float(r[metric])}

def act_best_player_by_avg_minutes(team: Optional[str] = None, min_apps: int = 3, **_) -> Dict[str, Any]:
    data = df().copy()
    if "Minutes" not in data.columns:
        return {"scope_team": team or "ALL", "min_apps": int(min_apps), "top_average_minutes": None, "players": [], "error": "Minutes column not found."}
    if team:
        data = data[data["Team"] == team]

    rows: List[Dict[str, Any]] = []
    for (t, p), g in data.groupby(["Team", "Player"], dropna=True):
        mins = pd.to_numeric(g["Minutes"], errors="coerce").fillna(0).sum()
        apps = _appearances(g)
        if apps >= max(1, int(min_apps)) and apps > 0:
            rows.append({
                "team": t, "player": p,
                "average_minutes": float(mins / apps),
                "minutes_sum": float(mins),
                "appearances": int(apps),
            })
    if not rows:
        return {"scope_team": team or "ALL", "min_apps": int(min_apps), "top_average_minutes": None, "players": []}

    rows.sort(key=lambda r: r["average_minutes"], reverse=True)
    top_avg = rows[0]["average_minutes"]
    EPS = 1e-9
    tied = [r for r in rows if abs(r["average_minutes"] - top_avg) <= EPS]
    return {"scope_team": team or "ALL", "min_apps": int(min_apps), "top_average_minutes": float(top_avg), "players": tied}

def act_top_players_by_avg_minutes(team: Optional[str] = None, top_n: int = 5, min_apps: int = 3, **_) -> List[Dict[str, Any]]:
    data = df().copy()
    if "Minutes" not in data.columns:
        return []
    if team:
        data = data[data["Team"] == team]
    rows: List[Dict[str, Any]] = []
    for (t, p), g in data.groupby(["Team", "Player"], dropna=True):
        mins = pd.to_numeric(g["Minutes"], errors="coerce").fillna(0).sum()
        apps = _appearances(g)
        if apps >= max(1, int(min_apps)) and apps > 0:
            rows.append({
                "team": t, "player": p,
                "average_minutes": float(mins / apps),
                "minutes_sum": float(mins),
                "appearances": int(apps),
            })
    rows.sort(key=lambda r: r["average_minutes"], reverse=True)
    return rows[:max(1, min(50, int(top_n)))]

def act_team_average_age(team: str, mode: str = "xi", **_) -> Dict[str, Any]:
    mode = (mode or "xi").lower()
    if mode not in ("xi", "squad"):
        mode = "xi"
    val = _team_avg_age_xi(team) if mode == "xi" else _team_avg_age_squad(team)
    return {"team": team, "mode": mode, "average_age": val}

def act_rank_teams_by_age(mode: str = "xi", **_) -> List[Dict[str, Any]]:
    mode = (mode or "xi").lower()
    if mode not in ("xi", "squad"):
        mode = "xi"
    rows = []
    for t in get_teams(df()):
        val = _team_avg_age_xi(t) if mode == "xi" else _team_avg_age_squad(t)
        if val is not None:
            rows.append({"team": t, "average_age": float(val)})
    rows.sort(key=lambda r: r["average_age"], reverse=True)
    return rows

def act_team_games(team: str, **_) -> List[Dict[str, Any]]:
    tdf = df()[df()["Team"] == team].copy()
    if tdf.empty: return []
    _, games = _with_game_keys(tdf)
    uniq = games.drop_duplicates(subset=["_GAME_KEY"])
    return [{"game_key": r["_GAME_KEY"], "label": r["_GAME_LABEL"]} for _, r in uniq.iterrows()]

def act_team_game_summary(team: str, game_key: str, **_) -> Dict[str, Any]:
    tdf = df()[df()["Team"] == team].copy()
    if tdf.empty: return {"team": team, "game_key": game_key, "error": "No team data."}
    t_with_keys, _ = _with_game_keys(tdf)
    gdf = t_with_keys[t_with_keys["_GAME_KEY"] == game_key]
    if gdf.empty: return {"team": team, "game_key": game_key, "error": "Game not found."}
    match_minutes = int(pd.to_numeric(gdf["Minutes"], errors="coerce").fillna(0).max()) if "Minutes" in gdf.columns else None
    goals = int(gdf["Goals"].sum()) if "Goals" in gdf.columns else None
    assists = int(gdf["Assists"].sum()) if "Assists" in gdf.columns else None
    avg_age = None
    if "Age" in gdf.columns and "Minutes" in gdf.columns:
        xi = gdf[pd.to_numeric(gdf["Minutes"], errors="coerce").fillna(0) > 0]
        if not xi.empty:
            avg_age = float(pd.to_numeric(xi["Age"], errors="coerce").dropna().mean())
    label = gdf["_GAME_LABEL"].iloc[0] if "_GAME_LABEL" in gdf.columns else game_key
    return {"team": team, "game_key": game_key, "label": label, "match_minutes": match_minutes, "team_goals": goals, "team_assists": assists, "avg_age_xi": avg_age}

# --------- single dispatcher ----------
ACTIONS = {
    # discovery
    "list_teams": act_list_teams,
    "list_players": act_list_players,

    # players
    "player_summary": act_player_summary,
    "compare_players": act_compare_players,
    "top_players": act_top_players,
    "best_player_by_metric": act_best_player_by_metric,
    "best_player_by_avg_minutes": act_best_player_by_avg_minutes,
    "top_players_by_avg_minutes": act_top_players_by_avg_minutes,

    # teams / games
    "team_average_age": act_team_average_age,
    "rank_teams_by_age": act_rank_teams_by_age,
    "team_games": act_team_games,
    "team_game_summary": act_team_game_summary,
}

def perform_action(action: str, **params) -> Any:
    if action not in ACTIONS:
        return {"error": f"Unknown action '{action}'", "available_actions": list(ACTIONS.keys())}
    try:
        return ACTIONS[action](**params)
    except TypeError as e:
        return {"error": f"Bad parameters for '{action}': {e}", "params": params}
    except Exception as e:
        return {"error": str(e), "action": action, "params": params}