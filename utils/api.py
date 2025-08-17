# utils/api.py
import requests
import streamlit as st

DRAFT_BASE = "https://draft.premierleague.com/api"
FPL_BASE   = "https://fantasy.premierleague.com/api"

def _get_json(url: str, default):
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception:
        return default

@st.cache_data(ttl=300)
def get_game_status():
    """
    Draft endpoint that includes current_event / next_event, etc.
    Example keys: current_event, next_event, processing_status, waivers_processed...
    """
    return _get_json(f"{DRAFT_BASE}/game", default={})

@st.cache_data(ttl=300)
def get_league_details(league_id: int):
    return requests.get(f"{DRAFT_BASE}/league/{league_id}/details", timeout=10).json()

@st.cache_data(ttl=300)
def get_bootstrap():
    """Fantasy endpoint with teams/elements."""
    return _get_json(f"{FPL_BASE}/bootstrap-static/", default={})

@st.cache_data(ttl=300)
def get_fixtures(event: int):
    """Fantasy endpoint for fixtures by event (gameweek). Returns a list."""
    return _get_json(f"{FPL_BASE}/fixtures?event={event}", default=[])

@st.cache_data(ttl=300)
def get_draft_choices(league_id: int):
    """
    Draft endpoint for who owns which players.
    Shape: {"choices": [ { "element": <player_id>, "entry_name": <team name>, ... }, ... ]}
    """
    return _get_json(f"{DRAFT_BASE}/draft/league/{league_id}/choices", default={"choices":[]})

@st.cache_data(ttl=120)  # shorter cache; squads can change with waivers
def get_entry_event(entry_id: int, event: int):
    # Current squad (picks) for a given entry + GW
    return _get_json(f"{DRAFT_BASE}/entry/{entry_id}/event/{event}", default={})
