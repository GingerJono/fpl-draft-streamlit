import streamlit as st
from datetime import datetime
from zoneinfo import ZoneInfo

from utils.api import (
    get_current_event,
    get_fixtures_for_event,
    get_teams_map,
)

st.title("⚽ Gameweek Live – Fixtures")

gw = get_current_event()
st.subheader(f"Fixtures for Gameweek {gw}")

fixtures = get_fixtures_for_event(gw)
team_map = get_teams_map()

# sort by kickoff time
fixtures.sort(key=lambda f: f["kickoff_time"] or "")

for f in fixtures:
    home = team_map[f["team_h"]]
    away = team_map[f["team_a"]]

    # status / score
    if f["finished"]:
        status = "FT"
    elif f["started"]:
        status = "Live"
    else:
        status = "Scheduled"

    if f["team_h_score"] is not None and f["team_a_score"] is not None:
        score = f"{f['team_h_score']}–{f['team_a_score']}"
    else:
        score = "vs"

    # kickoff (UK time)
    ko_uk = (
        datetime.fromisoformat(f["kickoff_time"].replace("Z", "+00:00"))
        .astimezone(ZoneInfo("Europe/London"))
        .strftime("%a %d %b, %H:%M")
        if f["kickoff_time"] else "TBC"
    )

    st.markdown(f"**{home} {score} {away}**  ·  {status}")
    st.caption(f"Kickoff: {ko_uk} (UK)")

st.divider()
st.caption("Fixtures supplied by classic FPL API; team names via Draft bootstrap-static.")
