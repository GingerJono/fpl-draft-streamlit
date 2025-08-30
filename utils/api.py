# utils/api.py
import requests
import pandas as pd
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
    return _get_json(f"{DRAFT_BASE}/bootstrap-static", default={})

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

# --- Ownership: rely only on actual GW picks --- #

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Tuple

@st.cache_data(ttl=300)
def league_entries_map(league_id: int) -> Dict[int, dict]:
    """entry_id -> league_entry object (has entry_name, etc)."""
    league = get_league_details(league_id) or {}
    out: Dict[int, dict] = {}
    for e in (league.get("league_entries") or []):
        if e.get("entry_id"):
            try:
                out[int(e["entry_id"])] = e
            except Exception:
                pass
    return out

@st.cache_data(ttl=60)
def build_current_ownership_ids(league_id: int, event_id: int, starters_only: bool = False) -> Dict[int, int]:
    """
    element_id -> owner's entry_id for the specified GW,
    built ONLY from /entry/{id}/event/{gw} picks (truth source).
    """
    entries = league_entries_map(league_id)
    ownership_ids: Dict[int, int] = {}

    def fetch_one(entry_id: int):
        data = get_entry_event(entry_id, event_id) or {}
        for p in (data.get("picks") or []):
            try:
                pid  = int(p.get("element"))
                mult = int(p.get("multiplier", 0))
            except Exception:
                continue
            if starters_only and mult <= 0:
                continue
            ownership_ids[pid] = entry_id

    with ThreadPoolExecutor(max_workers=min(8, max(1, len(entries)))) as ex:
        futures = [ex.submit(fetch_one, eid) for eid in entries.keys()]
        for _ in as_completed(futures):
            pass

    return ownership_ids

@st.cache_data(ttl=60)
def build_current_ownership(league_id: int, event_id: int, starters_only: bool = False) -> Dict[int, str]:
    """
    Back-compat shim: element_id -> owner's entry_name (derived from entry_id).
    """
    ids = build_current_ownership_ids(league_id, event_id, starters_only)
    entries = league_entries_map(league_id)
    return {pid: entries.get(eid, {}).get("entry_name", "—") for pid, eid in ids.items()}


def compute_slot(mult: int | None, posn: int | None) -> str:
    try:
        p = int(posn)
    except Exception:
        p = None
    try:
        m = int(mult)
    except Exception:
        m = None

    if p is not None:
        if 1 <= p <= 11: 
            return "XI"
        if 12 <= p <= 15:
            return f"Bench {p - 11}"
    # Fallbacks if position missing
    if m is not None and m > 0:
        return "XI"
    if m == 0:
        return "Bench ?"
    return "Unknown"

@st.cache_data(ttl=30)
def build_gw_player_table(league_id: int, event_id: int) -> list[dict]:
    """
    One row per player currently owned in the league for the GW.
    Includes: name, position, team, draft_rank (if available), owner team,
    GW points, minutes, contribs, lineup slot (XI or Bench 1/2/3/4).
    """
    league = get_league_details(league_id) or {}
    entries = [e for e in (league.get("league_entries") or []) if e.get("entry_id")]

    bootstrap = get_bootstrap() or {}
    elements = {p["id"]: p for p in (bootstrap.get("elements") or [])}
    teams = {t["id"]: t for t in (bootstrap.get("teams") or [])}
    etypes = {et["id"]: et for et in (bootstrap.get("element_types") or [])}
    pos_name = lambda et_id: etypes.get(et_id, {}).get("singular_name_short", "")

    # live stats (minutes, points, etc.)
    live = get_event_live(event_id) or {}
    live_elements = live.get("elements", {})
    stats_map = {}
    if isinstance(live_elements, dict):
        for k, v in live_elements.items():
            try:
                stats_map[int(k)] = v.get("stats") or {}
            except Exception:
                continue
    else:
        for v in (live_elements or []):
            pid = v.get("id")
            if pid is not None:
                stats_map[int(pid)] = v.get("stats") or {}

    # draft choices -> potential draft rank
    choices = get_draft_choices(league_id) or {}
    draft_map: dict[int, int] = {}
    if "choices" in choices:
        # Prefer explicit ordinal if present; else try round+pick math
        n_teams = max(1, len(entries))
        for c in choices["choices"]:
            pid = c.get("element")
            if pid is None:
                continue
            rank = (
                c.get("choice")
                or c.get("pick")
                or c.get("draft_number")
            )
            if not rank:
                rnd = c.get("round")
                rnd_pick = c.get("pick") or c.get("selection") or c.get("overall_pick")
                if rnd and rnd_pick:
                    try:
                        rank = int((int(rnd) - 1) * n_teams + int(rnd_pick))
                    except Exception:
                        rank = None
            if rank:
                try:
                    draft_map[int(pid)] = int(rank)
                except Exception:
                    pass

    # ownership + bench order via entry/{id}/event/{gw}
    rows: list[dict] = []
    for e in entries:
        entry_id = int(e["entry_id"])
        entry_name = e["entry_name"]
        picks = (get_entry_event(entry_id, event_id) or {}).get("picks") or []
        for p in picks:
            try:
                pid = int(p.get("element"))
                mult = int(p.get("multiplier", 0))
                posn = int(p.get("position", 0))  # 1..15 expected
            except Exception:
                continue
            pl = elements.get(pid, {})
            tm = teams.get(pl.get("team"), {})
            stats = stats_map.get(pid, {})
            minutes = int(stats.get("minutes", 0))
            points = int(stats.get("total_points", 0))

            contribs = []
            if "minutes" in stats: contribs.append(f"min+{stats['minutes']}")
            if stats.get("goals_scored"): contribs.append(f"g+{stats['goals_scored']}")
            if stats.get("assists"): contribs.append(f"a+{stats['assists']}")
            if stats.get("clean_sheets"): contribs.append(f"cs+{stats['clean_sheets']}")
            if stats.get("goals_conceded"): contribs.append(f"gc+{stats['goals_conceded']}")
            if stats.get("yellow_cards"): contribs.append(f"yc+{stats['yellow_cards']}")
            if stats.get("red_cards"): contribs.append(f"rc+{stats['red_cards']}")
            if stats.get("saves"): contribs.append(f"saves+{stats['saves']}")
            if stats.get("bonus"): contribs.append(f"b+{stats['bonus']}")
            if "bps" in stats: contribs.append(f"bps+{stats['bps']}")
            if "defensive_contribution" in stats: contribs.append(f"def+{stats['defensive_contribution']}")

            # lineup slot
            slot = compute_slot(mult, posn)

            rows.append({
                "Name": pl.get("web_name", f"Player {pid}"),
                "Position": pos_name(pl.get("element_type")),
                "Team": tm.get("short_name", ""),
                "DraftRank": draft_map.get(pid, None),
                "DraftedTo": entry_name,
                "GWPoints": points,
                "Minutes": minutes,
                "Contribs": " ".join(contribs) if contribs else "—",
                "LineupSlot": slot,
                "PlayerID": pid,  # handy for debugging/filtering
                "EntryID": entry_id,
            })

    return rows
