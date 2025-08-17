import requests
import streamlit as st

# Draft API (league/game state, players/teams)
BASE_DRAFT = "https://draft.premierleague.com/api"
# Classic FPL API (fixtures with kickoff times & scores)
BASE_MAIN  = "https://fantasy.premierleague.com/api"

@st.cache_data(ttl=300)
def get_game_status():
    return requests.get(f"{BASE_DRAFT}/game", timeout=10).json()

@st.cache_data(ttl=300)
def get_league_details(league_id: int):
    return requests.get(f"{BASE_DRAFT}/league/{league_id}/details", timeout=10).json()

@st.cache_data(ttl=300)
def get_event_live(event_id: int):
    return requests.get(f"{BASE_DRAFT}/event/{event_id}/live", timeout=10).json()

# --- new: shared dictionaries ---
@st.cache_data(ttl=1800)  # load once per 30 min
def get_bootstrap_static():
    return requests.get(f"{BASE_DRAFT}/bootstrap-static", timeout=10).json()

@st.cache_data(ttl=1800)
def get_teams_map():
    teams = get_bootstrap_static()["teams"]
    # id -> "Arsenal", etc.
    return {t["id"]: t["name"] for t in teams}

# --- new: fixtures (from classic FPL API) ---
@st.cache_data(ttl=120)   # fixtures can update during live GWs
def get_fixtures_for_event(event_id: int):
    return requests.get(f"{BASE_MAIN}/fixtures/?event={event_id}", timeout=10).json()

# convenience
@st.cache_data(ttl=120)
def get_current_event():
    return get_game_status()["current_event"]

@st.cache_data(ttl=300)
def get_draft_choices(league_id: int):
    return requests.get(f"{BASE_DRAFT}/draft/{league_id}/choices", timeout=10).json()
