# pages/live.py
import streamlit as st
from datetime import datetime, timezone
try:
    from zoneinfo import ZoneInfo  # Python 3.9+
except Exception:
    ZoneInfo = None

from utils.api import get_game_status, get_fixtures, get_bootstrap, get_draft_choices

LEAGUE_ID = 12260  # your league

def format_kickoff(iso_utc: str) -> str:
    if not iso_utc:
        return ""
    # iso_utc like "2025-08-16T14:00:00Z"
    try:
        dt = datetime.fromisoformat(iso_utc.replace("Z", "+00:00"))
        if ZoneInfo:
            dt = dt.astimezone(ZoneInfo("Europe/London"))
            return dt.strftime("%a %d %b, %H:%M %Z")
        else:
            # fallback: show UTC nicely
            return dt.astimezone(timezone.utc).strftime("%a %d %b, %H:%M UTC")
    except Exception:
        return iso_utc

# --- Data loads ---
status = get_game_status() or {}
gw = status.get("current_event", 1)  # default to GW1 if missing

fixtures = get_fixtures(gw) or []
bootstrap = get_bootstrap() or {}
choices = get_draft_choices(LEAGUE_ID) or {"choices": []}

# --- Lookups ---
teams = {t["id"]: t["name"] for t in bootstrap.get("teams", [])}
players_by_id = {p["id"]: p for p in bootstrap.get("elements", [])}
ownership = {c["element"]: c["entry_name"] for c in choices.get("choices", [])}

st.title(f"Fixtures for Gameweek {gw}")

if not fixtures:
    st.info("No fixtures found for this gameweek.")
else:
    for f in fixtures:
        home = teams.get(f.get("team_h"), f"Team {f.get('team_h')}")
        away = teams.get(f.get("team_a"), f"Team {f.get('team_a')}")
        kickoff = format_kickoff(f.get("kickoff_time", ""))

        st.subheader(f"{home} vs {away} — {kickoff}")

        # Gather all players from these two teams
        fixture_team_ids = {f.get("team_h"), f.get("team_a")}
        fixture_players = [p for p in players_by_id.values() if p.get("team") in fixture_team_ids]

        # Only show players owned in our draft league
        owned_players = [p for p in fixture_players if p["id"] in ownership]

        if not owned_players:
            st.write("No owned players in this fixture.")
            continue

        # Optional: show any contributions (goals/assists/cards) if present
        stat_map = {}
        for stat in f.get("stats", []):
            ident = stat.get("identifier")
            for side in ("h", "a"):
                for entry in stat.get(side, []):
                    pid = entry.get("element")
                    val = entry.get("value")
                    if pid is None:
                        continue
                    stat_map.setdefault(pid, []).append(f"{ident} +{val}")

        for p in owned_players:
            pid = p["id"]
            name = p.get("web_name") or f"Player {pid}"
            owner = ownership.get(pid, "—")
            contrib = ", ".join(stat_map.get(pid, [])) if pid in stat_map else "No contributions"
            st.write(f"- {name} ({owner}) → {contrib}")
