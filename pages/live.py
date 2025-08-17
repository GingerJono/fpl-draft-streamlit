# pages/live.py
import streamlit as st
from datetime import datetime, timezone
try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None

# Optional autorefresh component (best UX)
try:
    from streamlit_autorefresh import st_autorefresh  # pip install streamlit-autorefresh
except Exception:
    st_autorefresh = None

from utils.api import (
    get_game_status, get_bootstrap, get_fixtures,
    get_league_details, get_entry_event
)

LEAGUE_ID = 12260
LOCAL_TZ = ZoneInfo("Europe/London") if ZoneInfo else timezone.utc

def now_str():
    return datetime.now(LOCAL_TZ).strftime("%a %d %b %Y, %H:%M:%S %Z")

def format_kickoff(iso_utc: str) -> str:
    if not iso_utc:
        return ""
    try:
        dt = datetime.fromisoformat(iso_utc.replace("Z", "+00:00"))
        return dt.astimezone(LOCAL_TZ).strftime("%a %d %b, %H:%M %Z")
    except Exception:
        return iso_utc

# ---- Auto-refresh (60s), with pause toggle
colA, colB = st.columns([1, 3])
with colA:
    auto = st.toggle("Auto-refresh", value=True, key="live_auto")
with colB:
    st.caption("Refresh interval: 60 seconds")

if auto and st_autorefresh:
    # returns an incrementing counter we can ignore; keeps session_state intact
    st_autorefresh(interval=60_000, key="live_autorefresh")
elif auto and not st_autorefresh:
    # Fallback hint if dependency missing
    st.info("Install `streamlit-autorefresh` for smooth auto-refresh. Using manual refresh instead.")
    if st.button("Refresh now"):
        st.rerun()

# ---- Load core data
status    = get_game_status() or {}
gw        = status.get("current_event", 1)
bootstrap = get_bootstrap() or {}
fixtures  = sorted(get_fixtures(gw) or [], key=lambda x: x.get("kickoff_time") or "")
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
        pid = pick.get("element")
        if pid:
            ownership[pid] = entry_name

# ---- CSS

# Hide all checkboxes inside our fixture blocks
st.markdown(
    """
    <style>
    div[data-testid="stCheckbox"] {
        display: none !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ---- Header
st.title(f"Fixtures for Gameweek {gw}")
st.caption(f"Last refresh: {now_str()}")

if not fixtures:
    st.info("No fixtures found.")
else:
    for f in fixtures:
        fid = f.get("id")
        home = teams.get(f.get("team_h"), f"Team {f.get('team_h')}")
        away = teams.get(f.get("team_a"), f"Team {f.get('team_a')}")
        kickoff = format_kickoff(f.get("kickoff_time"))

        # Stable per-fixture expand/collapse toggle stored in session_state
        key_toggle = f"fx_open_{fid}"
        if key_toggle not in st.session_state:
            st.session_state[key_toggle] = False  # default collapsed

        tcol1, tcol2 = st.columns([9, 1])
        with tcol1:
            st.subheader(f"{home} vs {away} — {kickoff}")
        with tcol2:
            open_now = st.checkbox("", value=st.session_state[key_toggle], key=key_toggle)

        with st.expander("Show owned players", expanded=open_now):
            # players in the two clubs for this fixture
            fixture_team_ids = {f.get("team_h"), f.get("team_a")}
            fixture_players = [p for p in players_by_id.values() if p.get("team") in fixture_team_ids]

            # owned among them (current ownership for this GW)
            owned_players = [p for p in fixture_players if p["id"] in ownership]

            # live contribs rolled up from fixture stats
            stat_map = {}
            for stat in f.get("stats", []) or []:
                ident = stat.get("identifier")
                for side in ("h", "a"):
                    for entry in stat.get(side, []) or []:
                        pid = entry.get("element")
                        val = entry.get("value")
                        if pid is not None:
                            stat_map.setdefault(pid, []).append(f"{ident}+{val}")

            if not owned_players:
                st.write("No owned players in this fixture.")
            else:
                rows = []
                for p in owned_players:
                    pid = p["id"]
                    rows.append({
                        "Name": p.get("web_name", f"Player {pid}"),
                        "Club": teams.get(p.get("team"), f"Team {p.get('team')}"),
                        "Owned By": ownership.get(pid, "—"),
                        "Contrib": ", ".join(stat_map.get(pid, [])) if pid in stat_map else "—",
                    })
                st.table(rows)

# ---- Footer
st.markdown(
    f"<div style='position:sticky; bottom:0; background:#0e1117; padding:6px 10px; "
    f"opacity:0.85; font-size:0.85rem;'>Last refresh: {now_str()} "
    f"{'• Auto-refresh ON (60s)' if auto and st_autorefresh else '• Auto-refresh OFF'}</div>",
    unsafe_allow_html=True,
)

# Optional dev diagnostics
with st.expander("Dev: diagnostics", expanded=False):
    st.write(f"entries: {len(entries)} | ownership items: {len(ownership)} | fixtures: {len(fixtures)}")
    if st.checkbox("Show raw ownership map"):
        st.json(ownership)
