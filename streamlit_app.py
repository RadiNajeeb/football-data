import streamlit as st
from lib.data import inject_theme_css

st.set_page_config(page_title="Football Data", layout="wide")
inject_theme_css()

st.title("Welcome to Football Data App ⚽")
