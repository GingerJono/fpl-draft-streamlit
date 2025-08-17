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

@st.cache_data(ttl=300)
def get_event_live(event_id: int):
    return requests.get(f"{DRAFT_BASE}/event/{event_id}/live").json()


# utils/api.py (append this to the bottom)

from concurrent.futures import ThreadPoolExecutor, as_completed

@st.cache_data(ttl=60)  # small cache; uses get_entry_event (120s) under the hood
def build_current_ownership(league_id: int, event_id: int, starters_only: bool = False) -> dict[int, str]:
    """
    Returns a mapping of element_id -> owner's entry_name for the specified GW,
    built from each entry's actual picks in /entry/{id}/event/{gw}.

    - starters_only=True => only players with multiplier > 0 (i.e., scoring XI)
    """
    league = get_league_details(league_id) or {}
    entries = [
        e for e in (league.get("league_entries") or [])
        if e.get("entry_id") and e.get("entry_name")
    ]

    ownership: dict[int, str] = {}

    def fetch_one(entry: dict):
        entry_id = int(entry["entry_id"])
        entry_name = entry["entry_name"]
        data = get_entry_event(entry_id, event_id) or {}
        for p in (data.get("picks") or []):
            try:
                pid  = int(p.get("element"))
                mult = int(p.get("multiplier", 0))
            except Exception:
                continue
            if starters_only and mult <= 0:
                continue
            ownership[pid] = entry_name

    # parallelize to keep UI snappy for 8-team leagues
    with ThreadPoolExecutor(max_workers=min(8, max(1, len(entries)))) as ex:
        futures = [ex.submit(fetch_one, e) for e in entries]
        for _ in as_completed(futures):
            pass

    return ownership
