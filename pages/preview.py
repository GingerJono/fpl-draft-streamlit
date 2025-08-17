import streamlit as st

st.title("📋 Gameweek Preview")
st.write("Preview shows pre-GW info: transactions, waivers, PL schedule, and selected teams.")

# quick navigation for 1–38
cols = st.columns(38)
for i in range(38):
    with cols[i]:
        st.link_button(str(i+1), f"?gameweek={i+1}")
