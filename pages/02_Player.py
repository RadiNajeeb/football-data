import streamlit as st
import pandas as pd
from lib.data import load_df

st.title("Player Explorer")

# Load data
DF = load_df("database.csv")

# Team and player selection
teams = DF["team"].dropna().unique()
team = st.selectbox("Team", teams)
players = DF[DF["team"] == team]["player"].dropna().unique()
player = st.selectbox("Player", players)

# Filter player data
player_df = DF[(DF["team"] == team) & (DF["player"] == player)]

if not player_df.empty:
    st.subheader(f"{player}")

    # Collect stats (adjust column names as needed)
    stats = {
        "Match Minutes": int(player_df["minutes"].sum()),
        "Goals": int(player_df["goals"].sum()),
        "Assists": int(player_df["assists"].sum()),
        "Shots": int(player_df["shots"].sum()),
        "Passes Completed": int(player_df["passes_completed"].sum()),
        "Tackles": int(player_df["tackles"].sum()),
        "Yellow Cards": int(player_df["yellow_cards"].sum()),
        "Red Cards": int(player_df["red_cards"].sum()),
    }

    # Show stats in columns
    cols = st.columns(4)
    for i, (stat, value) in enumerate(stats.items()):
        with cols[i % 4]:
            st.metric(stat, value)

    with st.expander("Raw data"):
        st.dataframe(player_df)
