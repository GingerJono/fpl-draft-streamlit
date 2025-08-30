# pages/players.py
import streamlit as st
import pandas as pd
from datetime import datetime, timezone
try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None

from utils.api import (
    get_game_status,
    get_bootstrap,
    get_event_live,
    build_current_ownership_ids,
    league_entries_map,
)

st.set_page_config(layout="wide")

LEAGUE_ID = 12260
LOCAL_TZ = ZoneInfo("Europe/London") if ZoneInfo else timezone.utc

def now_str():
    return datetime.now(LOCAL_TZ).strftime("%a %d %b %Y, %H:%M:%S %Z")

TEAM_COLOURS = {
    "Ekitikekitike": "#ffadad",
    "ØdegaardiansOfTheGal": "#ffd6a5",
    "Ranger Things": "#fdffb6",
    "Potter&The½FitWilson": "#caffbf",
    "Bowen Arrow": "#9bf6ff",
    "DioufFeelLuckyPunk?": "#a0c4ff",
    "No Juan Eyed Bernabe": "#bdb2ff",
}

def style_owner(df, col="Owner"):
    if col not in df.columns:
        return df
    def _cell(v):
        c = TEAM_COLOURS.get(str(v), "")
        return f"background-color: {c}" if c else ""
    return df.style.applymap(_cell, subset=[col])

# --- scoring rules
SCORING = {
    'long_play_limit': 60, 'short_play': 1, 'long_play': 2,
    'concede_limit': 2,
    'goals_conceded_GKP': -1, 'goals_conceded_DEF': -1, 'goals_conceded_MID': 0, 'goals_conceded_FWD': 0,
    'saves_limit': 3, 'saves': 1,
    'goals_scored_GKP': 10, 'goals_scored_DEF': 6, 'goals_scored_MID': 5, 'goals_scored_FWD': 4,
    'assists': 3,
    'clean_sheets_GKP': 4, 'clean_sheets_DEF': 4, 'clean_sheets_MID': 1, 'clean_sheets_FWD': 0,
    'defensive_contribution_limit_GKP': 0, 'defensive_contribution_limit_DEF': 10,
    'defensive_contribution_limit_MID': 12, 'defensive_contribution_limit_FWD': 12,
    'defensive_contribution_GKP': 0, 'defensive_contribution_DEF': 2,
    'defensive_contribution_MID': 2, 'defensive_contribution_FWD': 2,
    'penalties_saved': 5, 'penalties_missed': -2,
    'yellow_cards': -1, 'red_cards': -3, 'own_goals': -2,
    'bonus': 1,
}

def compute_score(stats: dict, pos: str) -> int:
    pts = 0
    minutes = stats.get("minutes", 0)

    # minutes
    if minutes >= SCORING['long_play_limit']:
        pts += SCORING['long_play']
    elif minutes > 0:
        pts += SCORING['short_play']

    # goals scored
    if stats.get("goals_scored"):
        pts += stats["goals_scored"] * SCORING[f"goals_scored_{pos}"]

    # assists
    pts += stats.get("assists", 0) * SCORING['assists']

    # clean sheet
    if minutes >= SCORING['long_play_limit'] and stats.get("clean_sheets"):
        pts += SCORING[f"clean_sheets_{pos}"]

    # goals conceded (only GKP/DEF penalised, after concede_limit)
    if pos in ("GKP","DEF"):
        conceded = stats.get("goals_conceded", 0)
        if conceded >= SCORING['concede_limit']:
            pts += (conceded // SCORING['concede_limit']) * SCORING[f"goals_conceded_{pos}"]

    # saves (for GKP)
    if pos == "GKP":
        saves = stats.get("saves", 0)
        pts += (saves // SCORING['saves_limit']) * SCORING['saves']

    # defensive contribution
    dc = stats.get("defensive_contribution", 0)
    limit = SCORING[f"defensive_contribution_limit_{pos}"]
    if limit and dc:
        pts += (dc // limit) * SCORING[f"defensive_contribution_{pos}"]

    # pens
    pts += stats.get("penalties_saved", 0) * SCORING['penalties_saved']
    pts += stats.get("penalties_missed", 0) * SCORING['penalties_missed']

    # cards
    pts += stats.get("yellow_cards", 0) * SCORING['yellow_cards']
    pts += stats.get("red_cards", 0) * SCORING['red_cards']

    # own goals
    pts += stats.get("own_goals", 0) * SCORING['own_goals']

    # bonus
    pts += stats.get("bonus", 0) * SCORING['bonus']

    return pts

# ---- Data
status = get_game_status() or {}
gw = status.get("current_event", 1)

bootstrap = get_bootstrap() or {}
players_by_id = {int(p["id"]): p for p in (bootstrap.get("elements") or [])}
teams = {t["id"]: t["short_name"] for t in (bootstrap.get("teams") or [])}
pos_map = {et["id"]: et["singular_name_short"] for et in (bootstrap.get("element_types") or [])}

live = get_event_live(gw) or {}
live_elements = live.get("elements", {})

live_stats = {}
if isinstance(live_elements, dict):
    for k, v in live_elements.items():
        try:
            pid = int(k)
        except Exception:
            continue
        live_stats[pid] = v.get("stats", {}) or {}
elif isinstance(live_elements, list):
    for v in live_elements:
        pid = v.get("id")
        if pid is not None:
            live_stats[int(pid)] = v.get("stats", {}) or {}

ownership_ids = build_current_ownership_ids(LEAGUE_ID, gw, starters_only=False)
entries_map = league_entries_map(LEAGUE_ID)

# ---- Build dataframe
rows = []
for pid, pl in players_by_id.items():
    stats = live_stats.get(pid, {})
    eid = ownership_ids.get(pid)
    owner = entries_map.get(eid, {}).get("entry_name", "—")
    pos = pos_map.get(pl.get("element_type"), "")

    row = {
        "Player": pl.get("web_name", f"#{pid}"),
        "Pos": pos,
        "Club": teams.get(pl.get("team"), ""),
        "Owner": owner,
        "Min": stats.get("minutes", 0),
        "G": stats.get("goals_scored", 0),
        "A": stats.get("assists", 0),
        "CS": stats.get("clean_sheets", 0),
        "GC": stats.get("goals_conceded", 0),
        "YC": stats.get("yellow_cards", 0),
        "RC": stats.get("red_cards", 0),
        "OG": stats.get("own_goals", 0),
        "PS": stats.get("penalties_saved", 0),
        "PM": stats.get("penalties_missed", 0),
        "SV": stats.get("saves", 0),
        "B": stats.get("bonus", 0),
        "BPS": stats.get("bps", 0),
        "DC": stats.get("defensive_contribution", 0),
        "API": stats.get("total_points", 0),
        "Comp": compute_score(stats, pos),
    }
    rows.append(row)

df = pd.DataFrame(rows)

# ---- UI
st.title(f"All Players — GW{gw}")
st.caption(f"Last refresh: {now_str()}")

if df.empty:
    st.info("No players found.")
else:
    df["Owned?"] = df["Owner"].ne("—")
    df = df.sort_values(["Owned?", "API"], ascending=[False, False])
    df = df.drop(columns=["Owned?"])

    st.dataframe(
        style_owner(df, col="Owner"),
        use_container_width=True,
        column_config={
            "Min": st.column_config.NumberColumn("Min", help="Minutes played"),
            "G": st.column_config.NumberColumn("G", help="Goals scored"),
            "A": st.column_config.NumberColumn("A", help="Assists"),
            "CS": st.column_config.NumberColumn("CS", help="Clean sheets"),
            "GC": st.column_config.NumberColumn("GC", help="Goals conceded"),
            "YC": st.column_config.NumberColumn("YC", help="Yellow cards"),
            "RC": st.column_config.NumberColumn("RC", help="Red cards"),
            "OG": st.column_config.NumberColumn("OG", help="Own goals"),
            "PS": st.column_config.NumberColumn("PS", help="Penalties saved"),
            "PM": st.column_config.NumberColumn("PM", help="Penalties missed"),
            "SV": st.column_config.NumberColumn("SV", help="Saves"),
            "B": st.column_config.NumberColumn("B", help="Bonus"),
            "BPS": st.column_config.NumberColumn("BPS", help="Bonus point system score"),
            "DC": st.column_config.NumberColumn("DC", help="Defensive contribution"),
            "API": st.column_config.NumberColumn("API", help="API total points"),
            "Comp": st.column_config.NumberColumn("Comp", help="Computed total points"),
        },
    )