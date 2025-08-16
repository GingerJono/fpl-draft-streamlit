import streamlit as st

st.set_page_config(page_title="My Streamlit App", layout="wide")

st.title("Hello Streamlit 👋")
st.write("This is my first Streamlit app running from VS Code.")

# Example input/output
name = st.text_input("What's your name?")
if name:
    st.success(f"Hello {name}, welcome to the app!")

# Example chart
import pandas as pd
import numpy as np

df = pd.DataFrame(
    np.random.randn(20, 3),
    columns=["A", "B", "C"]
)
st.line_chart(df)
