# pages/04_Chat.py
import os
import json
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI
from openai import APIConnectionError, RateLimitError, OpenAIError

from lib.agent_tools import perform_action  # single executor

st.set_page_config(page_title="Football Assistant — Chat", page_icon="⚽", layout="wide")
st.title("Football Assistant — Chat")

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    st.error("❌ No OpenAI API key found. Set OPENAI_API_KEY in your .env.")
    st.stop()

client = OpenAI(api_key=OPENAI_API_KEY, timeout=30.0, max_retries=3)

def safe_chat_completion(**kwargs):
    try:
        return client.chat.completions.create(**kwargs)
    except (APIConnectionError, RateLimitError, OpenAIError) as e:
        st.error(f"OpenAI error: {e}")
        return None

# ---------------- Intent Router ----------------
ROUTER_SYSTEM = (
    "You are an intent parser for a LaLiga analytics app. "
    "Given a user message, output a STRICT JSON object describing the action to run "
    "and the parameters. Do not include commentary.\n\n"
    "Supported actions and expected params:\n"
    "- list_teams: {}\n"
    "- list_players: {team}\n"
    "- player_summary: {team, player}\n"
    "- compare_players: {team_a, player_a, team_b, player_b, metrics?}\n"
    "- top_players: {metric, team?, top_n?}\n"
    "- best_player_by_metric: {metric?, team?}  # default metric 'Goals'\n"
    "- best_player_by_avg_minutes: {team?, min_apps?}\n"
    "- top_players_by_avg_minutes: {team?, top_n?, min_apps?}\n"
    "- team_average_age: {team, mode?}  # mode in ['xi','squad']\n"
    "- rank_teams_by_age: {mode?}  # mode in ['xi','squad']\n"
    "- team_games: {team}\n"
    "- team_game_summary: {team, game_key}\n\n"
    "Return JSON with keys: action (string), params (object). "
    "If the request is unclear, pick the closest action and leave missing params out."
)

def route_intent(user_text: str) -> dict:
    resp = safe_chat_completion(
        model="gpt-4o-mini",
        temperature=0.0,
        messages=[
            {"role":"system","content":ROUTER_SYSTEM},
            {"role":"user","content":user_text}
        ],
        response_format={"type":"json_object"},
        max_tokens=300
    )
    if not resp:
        return {"action":"unknown", "params":{"reason":"router-failed"}}
    try:
        data = json.loads(resp.choices[0].message.content)
        if not isinstance(data, dict):
            raise ValueError("non-dict router output")
        return {"action": data.get("action","unknown"), "params": data.get("params",{})}
    except Exception as e:
        return {"action":"unknown", "params":{"reason":f"router-parse-error: {e}"}}

# --------------- Grounded Answer Composer ---------------
ANSWER_SYSTEM = (
    "You are a football assistant. Use ONLY the JSON result provided to you. "
    "Do not invent facts. If you see a 'players' array that represents ties, list them all. "
    "If there is an 'error' field, explain briefly and suggest a supported query. "
    "Be concise; include units like minutes when relevant."
)

def compose_answer(user_text: str, result: dict | list | str) -> str:
    resp = safe_chat_completion(
        model="gpt-4o",
        temperature=0.1,
        messages=[
            {"role":"system","content":ANSWER_SYSTEM},
            {"role":"user","content":f"User question: {user_text}"},
            {"role":"user","content":"Here is the JSON result from the dataset:"},
            {"role":"user","content":json.dumps(result, ensure_ascii=False)}
        ],
        max_tokens=500
    )
    if not resp:
        return "Sorry, I couldn't compose a response."
    return resp.choices[0].message.content or "Sorry, I couldn't compose a response."

# ---------------- Chat state & UI ----------------
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []

col1, col2 = st.columns([1,1])
with col1:
    if st.button("🧹 Clear chat"):
        st.session_state["chat_messages"] = []
        st.rerun()
with col2:
    if st.button("🔌 Self-test"):
        ping = safe_chat_completion(model="gpt-4o-mini", messages=[{"role":"user","content":"ping"}], max_tokens=5)
        st.success("OpenAI reachable ✅" if ping else "OpenAI not reachable")

# display history
for m in st.session_state.chat_messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

user_text = st.chat_input("Ask about teams, players, matches, or comparisons…")
if user_text:
    st.session_state.chat_messages.append({"role":"user", "content": user_text})

    # 1) route
    intent = route_intent(user_text)
    # 2) execute
    result = perform_action(intent.get("action","unknown"), **intent.get("params",{}))
    # 3) answer
    reply = compose_answer(user_text, result)

    st.session_state.chat_messages.append({"role":"assistant","content": reply})
    with st.chat_message("assistant"):
        st.markdown(reply)