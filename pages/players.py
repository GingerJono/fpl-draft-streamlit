# pages/players.py
import streamlit as st
import pandas as pd
from datetime import datetime, timezone
from utils.helpers import compute_score, TEAM_COLOURS
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

def style_owner(df, col="Owner"):
    if col not in df.columns:
        return df
    def _cell(v):
        c = TEAM_COLOURS.get(str(v), "")
        return f"background-color: {c}" if c else ""
    return df.style.applymap(_cell, subset=[col])

# pages/players.py  (continuing from your current version)
from utils.api import get_fixtures

# ---- Data
status = get_game_status() or {}
gw = status.get("current_event", 1)

bootstrap = get_bootstrap() or {}
players_by_id = {int(p["id"]): p for p in (bootstrap.get("elements") or [])}
teams = {t["id"]: t["short_name"] for t in (bootstrap.get("teams") or [])}
pos_map = {et["id"]: et["singular_name_short"] for et in (bootstrap.get("element_types") or [])}

fixtures = get_fixtures(gw) or []
# Map team_id -> fixture info
fixture_map = {}
for f in fixtures:
    for side in ("team_h", "team_a"):
        tid = f.get(side)
        if tid:
            fixture_map[tid] = f

# inside players.py (after you’ve built fixture_map from get_fixtures)

def get_fixture_label(team_id: int) -> str:
    f = fixture_map.get(team_id)
    if not f:
        return "—"
    # if this team is home, opponent is away; else vice versa
    if f.get("team_h") == team_id:
        opp_id = f.get("team_a")
    else:
        opp_id = f.get("team_h")
    return f"vs. {teams.get(opp_id, '—')}"

live = get_event_live(gw) or {}
live_elements = live.get("elements", {})

# Normalise live stats
live_stats = {}
if isinstance(live_elements, dict):
    for k, v in live_elements.items():
        try: pid = int(k)
        except: continue
        live_stats[pid] = v.get("stats", {}) or {}
elif isinstance(live_elements, list):
    for v in live_elements:
        pid = v.get("id")
        if pid is not None:
            live_stats[int(pid)] = v.get("stats", {}) or {}

ownership_ids = build_current_ownership_ids(LEAGUE_ID, gw, starters_only=False)
entries_map = league_entries_map(LEAGUE_ID)

def fixture_status(team_id: int) -> str:
    f = fixture_map.get(team_id)
    if not f:
        return "—"
    if f.get("finished"):
        return "Finished"
    kickoff = f.get("kickoff_time")
    if kickoff:
        try:
            dt = datetime.fromisoformat(kickoff.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            if now < dt:
                return "Not started"
            else:
                return "In play"
        except Exception:
            pass
    return "—"

# ---- Build dataframe
rows = []
for pid, pl in players_by_id.items():
    stats = live_stats.get(pid, {})
    eid = ownership_ids.get(pid)
    owner = entries_map.get(eid, {}).get("entry_name", "—")
    pos = pos_map.get(pl.get("element_type"), "")
    team_id = pl.get("team")
    status_str = fixture_status(team_id)

    row = {
        "Player": pl.get("web_name", f"#{pid}"),
        "Pos": pos,
        "Club": teams.get(team_id, ""),
        "Owner": owner,
        "Fixture": get_fixture_label(team_id),
        "Fixture Status": status_str,
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
        "Comp": compute_score(stats, pos),  # eventually pass bonus_override here
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
            "Fixture Status": st.column_config.TextColumn("Status", help="Fixture status (Not started / In play / Finished)"),
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
