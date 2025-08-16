import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="FPL Draft API", layout="centered")

st.title("FPL Draft – Game Status")

url = "https://draft.premierleague.com/api/game"

try:
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    data = response.json()
    
    # Show raw JSON
    st.subheader("Raw API Response")
    st.json(data)

    # Convert to table for readability
    st.subheader("Game Status (Table)")
    df = pd.DataFrame([data])  # one row
    st.table(df)

except requests.RequestException as e:
    st.error(f"Failed to fetch API: {e}")
