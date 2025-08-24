import streamlit as st
from utils.api import get_game_status, get_league_details
from utils.helpers import highlight_teams
import pandas as pd

LEAGUE_ID = 12260   # hardcoded for now

st.title("🏆 FPL Draft – League Snapshot")

# --- Game status ---
status = get_game_status()
st.subheader("Game Status")
st.write(f"Current Gameweek: **{status['current_event']}**")
st.write(f"Next Gameweek: **{status['next_event']}**")
st.write(f"Processing Status: **{status['processing_status']}**")

# --- League table ---
league = get_league_details(LEAGUE_ID)

# map league_entry id -> league_entry object (for names)
entry_map = {e["id"]: e for e in league["league_entries"] if e["entry_id"]}

st.subheader("League Table")
table = [
    {
        "Team": entry_map[s["league_entry"]]["entry_name"],
        "Manager": (
            entry_map[s["league_entry"]]["player_first_name"] + " " +
            entry_map[s["league_entry"]]["player_last_name"]
        ),
        "Wins": s["matches_won"],
        "Losses": s["matches_lost"],
        "Draws": s["matches_drawn"],
        "Points": s["total"],
    }
    for s in league["standings"]
    if s["league_entry"] in entry_map
]

df_table = pd.DataFrame(table)
st.dataframe(highlight_teams(df_table), use_container_width=True)

# --- Current Matches as Table ---
st.subheader("Current Gameweek Matches")
gw = status["current_event"]
matches = [m for m in league["matches"] if m["event"] == gw]

match_table = []
for m in matches:
    home = entry_map.get(m["league_entry_1"], {}).get("entry_name", "TBD")
    away = entry_map.get(m["league_entry_2"], {}).get("entry_name", "TBD")
    match_table.append({
        "Home": home,
        "Score A": m["league_entry_1_points"],
        "Score B": m["league_entry_2_points"],
        "Away": away
    })

df_match = pd.DataFrame(match_table)
st.dataframe(highlight_teams(df_match), use_container_width=True)

