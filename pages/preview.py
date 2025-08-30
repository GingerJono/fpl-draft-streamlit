# pages/preview.py
import streamlit as st
import pandas as pd
from datetime import datetime, timezone
try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None

from utils.api import get_game_status, get_fixtures, get_bootstrap, get_league_details

st.set_page_config(layout="wide")

LEAGUE_ID = 12260
LOCAL_TZ = ZoneInfo("Europe/London") if ZoneInfo else timezone.utc

def format_kickoff(iso_utc: str) -> str:
    if not iso_utc:
        return ""
    try:
        dt = datetime.fromisoformat(iso_utc.replace("Z", "+00:00"))
        return dt.astimezone(LOCAL_TZ).strftime("%a %d %b, %H:%M %Z")
    except Exception:
        return iso_utc

status = get_game_status() or {}
current_gw = status.get("current_event", 1)

st.title("📋 Gameweek Preview")
st.caption(f"Current GW: {current_gw}")

tab_labels = [f"GW{i}" for i in range(1, 39)]
tabs = st.tabs(tab_labels)

league = get_league_details(LEAGUE_ID) or {}
entry_map = {e["id"]: e for e in (league.get("league_entries") or []) if e.get("entry_id")}

for gw, tab in enumerate(tabs, start=1):
    with tab:
        st.subheader(f"Gameweek {gw}")

        # ---- Premier League fixtures
        fixtures = get_fixtures(gw) or []
        bootstrap = get_bootstrap() or {}
        teams = {t["id"]: t for t in (bootstrap.get("teams") or [])}

        if fixtures:
            fix_table = []
            for f in fixtures:
                home = teams.get(f.get("team_h"), {}).get("name", f.get("team_h"))
                away = teams.get(f.get("team_a"), {}).get("name", f.get("team_a"))
                ko   = format_kickoff(f.get("kickoff_time"))
                fix_table.append({"Home": home, "Away": away, "Kickoff": ko})
            st.markdown("**Premier League fixtures**")
            st.table(pd.DataFrame(fix_table))
        else:
            st.info("No PL fixtures available.")

        # ---- Draft league matches (H2H)
        matches = [m for m in (league.get("matches") or []) if m.get("event") == gw]
        if matches:
            match_table = []
            for m in matches:
                home = entry_map.get(m["league_entry_1"], {}).get("entry_name", "—")
                away = entry_map.get(m["league_entry_2"], {}).get("entry_name", "—")
                match_table.append({
                    "Team A": home,
                    "Pts A": m.get("league_entry_1_points", 0),
                    "Pts B": m.get("league_entry_2_points", 0),
                    "Team B": away,
                })
            st.markdown("**Draft League H2H**")
            st.table(pd.DataFrame(match_table))
        else:
            st.info("No Draft matches available for this GW.")
