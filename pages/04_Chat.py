# pages/04_Chat.py

# 1) Path shim
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# 2) Third-party
import streamlit as st

# 3) Your local helpers (adjust these to what you really use)
from lib.data import load_df
# If you have chat helpers in lib/agent_tools.py:
#   from lib.agent_tools import chat, ask_model, build_prompt  # <-- adjust names
# Or if 04_Chat works purely with Streamlit’s chat_input, keep it simple.

# 4) Load data if this chat references it
DATA_PATH = ROOT / "database.csv"
try:
    DF = load_df(str(DATA_PATH))
except Exception:
    DF = None  # chat may not need DF; avoid hard crash

# ------------------- YOUR PAGE LOGIC -------------------
st.title("Chat")

# Basic chat loop (use your own functions instead if you have them)
if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

prompt = st.chat_input("Ask anything about La Liga data…")
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Replace this with your actual model call if you have one in lib/agent_tools
    # For now, echo with a friendly note:
    answer = "I received your question, but the chat model isn’t wired yet."
    if DF is None:
        answer += " (Data not loaded.)"

    with st.chat_message("assistant"):
        st.markdown(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})
