# pages/live.py
import streamlit as st
from datetime import datetime, timezone
try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None

from utils.api import (
    get_game_status, get_bootstrap, get_fixtures,
    get_league_details, get_entry_event
)

LEAGUE_ID = 12260

def format_kickoff(iso_utc: str) -> str:
    if not iso_utc:
        return ""
    try:
        dt = datetime.fromisoformat(iso_utc.replace("Z", "+00:00"))
        if ZoneInfo:
            return dt.astimezone(ZoneInfo("Europe/London")).strftime("%a %d %b, %H:%M %Z")
        return dt.astimezone(timezone.utc).strftime("%a %d %b, %H:%M UTC")
    except Exception:
        return iso_utc

# ---- Load core data
status    = get_game_status() or {}
gw        = status.get("current_event", 1)
bootstrap = get_bootstrap() or {}
fixtures  = get_fixtures(gw) or []
league    = get_league_details(LEAGUE_ID) or {}

# Lookups
teams = {t["id"]: t["name"] for t in (bootstrap.get("teams") or [])}
players_by_id = {p["id"]: p for p in (bootstrap.get("elements") or [])}

# Build CURRENT ownership (element_id -> owner team name) from every entry's GW picks
ownership = {}
entries = league.get("league_entries", [])
for e in entries:
    entry_id = e.get("entry_id")
    entry_name = e.get("entry_name")
    if not entry_id or not entry_name:
        continue
    ev = get_entry_event(entry_id, gw) or {}
    for pick in ev.get("picks", []):   # each pick has "element" (player id)
        element_id = pick.get("element")
        if element_id:
            ownership[element_id] = entry_name

# ---- Render
st.title(f"Fixtures for Gameweek {gw}")

if not fixtures:
    st.info("No fixtures found.")
else:
    for f in fixtures:
        home = teams.get(f.get("team_h"), f"Team {f.get('team_h')}")
        away = teams.get(f.get("team_a"), f"Team {f.get('team_a')}")
        kickoff = format_kickoff(f.get("kickoff_time"))

        with st.expander(f"{home} vs {away} — {kickoff}", expanded=False):
            # players in the two clubs for this fixture
            fixture_team_ids = {f.get("team_h"), f.get("team_a")}
            fixture_players = [p for p in players_by_id.values() if p.get("team") in fixture_team_ids]

            # owned among them (current ownership for this GW)
            owned_players = [p for p in fixture_players if p["id"] in ownership]

            # prepare any live contributions from the fixture’s stats
            stat_map = {}
            for stat in f.get("stats", []):
                ident = stat.get("identifier")
                for side in ("h", "a"):
                    for entry in stat.get(side, []):
                        pid = entry.get("element")
                        val = entry.get("value")
                        if pid is not None:
                            stat_map.setdefault(pid, []).append(f"{ident}+{val}")

            if not owned_players:
                st.write("No owned players in this fixture.")
            else:
                table = []
                for p in owned_players:
                    pid = p["id"]
                    row = {
                        "Name": p.get("web_name", f"Player {pid}"),
                        "Club": teams.get(p.get("team"), f"Team {p.get('team')}"),
                        "Owned By": ownership.get(pid, "—"),
                        "Contrib": ", ".join(stat_map.get(pid, [])) if pid in stat_map else "—",
                    }
                    table.append(row)

                st.table(table)

# Optional dev diagnostics
with st.expander("Dev: diagnostics", expanded=False):
    st.write(f"entries: {len(entries)} | ownership items: {len(ownership)}")
    if st.checkbox("Show raw ownership map"):
        st.json(ownership)
