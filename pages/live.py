# pages/live.py
import streamlit as st
from datetime import datetime, timezone
try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None

# Optional autorefresh component (pip install streamlit-autorefresh)
try:
    from streamlit_autorefresh import st_autorefresh
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
    st_autorefresh(interval=60_000, key="live_autorefresh")
elif auto and not st_autorefresh:
    if st.button("Refresh now"):
        st.rerun()
    st.info("Tip: install `streamlit-autorefresh` for smooth auto-refresh.")

# ---- Load core data
status    = get_game_status() or {}
gw        = status.get("current_event", 1)
bootstrap = get_bootstrap() or {}
fixtures  = sorted(get_fixtures(gw) or [], key=lambda x: x.get("kickoff_time") or "")
league    = get_league_details(LEAGUE_ID) or {}

# Lookups
teams = {
    t["id"]: {"name": t["name"], "abbr": t["short_name"]}
    for t in (bootstrap.get("teams") or [])
}
players_by_id = {p["id"]: p for p in (bootstrap.get("elements") or [])}

# Build CURRENT ownership (element_id -> owner team name) from each entry's GW picks
ownership = {}
for e in (league.get("league_entries") or []):
    entry_id = e.get("entry_id")
    entry_name = e.get("entry_name")
    if not entry_id or not entry_name:
        continue
    ev = get_entry_event(entry_id, gw) or {}
    for pick in (ev.get("picks") or []):
        pid = pick.get("element")
        if pid:
            ownership[pid] = entry_name

# ---- CSS (hide checkbox, tidy table, non-wrapping player/team, line-broken contrib)
st.markdown(
    """
    <style>
    div[data-testid="stCheckbox"] { display: none !important; }
    [data-testid="stExpander"] details > summary > div:first-child { display:none !important; }

    .fixture-table { width:100%; border-collapse:collapse; }
    .fixture-table th, .fixture-table td {
      border-bottom: 1px solid rgba(49,51,63,0.2);
      padding: 10px 12px;
      vertical-align: top;
      text-align: left;
    }
    .fixture-table th { font-weight: 600; }
    .player-team { white-space: nowrap !important; }   /* don’t wrap name [TEAM] */
    .contrib { font-size: 0.85rem; line-height: 1.15; opacity: 0.9; }
    .contrib .item { display:block; }                  /* each stat on new line */
    </style>
    """,
    unsafe_allow_html=True
)

# ---- Header
st.title(f"Fixtures for Gameweek {gw}")
st.caption(f"Last refresh: {now_str()}")

def _team_name(team_id: int) -> str:
    t = teams.get(team_id, {})
    return (t.get("name") if isinstance(t, dict) else str(t)) or f"Team {team_id}"

def _team_abbr(team_id: int) -> str:
    t = teams.get(team_id, {})
    return t.get("abbr", "") if isinstance(t, dict) else ""

# Short labels for fixture stat identifiers (shown in Contrib column)
STAT_LABELS = {
    "goals_scored": "g",
    "assists": "a",
    "yellow_cards": "yc",
    "red_cards": "rc",
    "saves": "saves",
    "bonus": "b",
    "bps": "bps",
    "defensive_contribution": "def",
    "penalties_saved": "ps",
    "penalties_missed": "pm",
    "own_goals": "og",
    "minutes": "min",  # appears in some live feeds; included when present
}

if not fixtures:
    st.info("No fixtures found.")
else:
    for f in fixtures:
        fid = f.get("id")
        home_name = _team_name(f.get("team_h"))
        away_name = _team_name(f.get("team_a"))
        kickoff = format_kickoff(f.get("kickoff_time"))

        # Persisted expand/collapse per fixture
        key_toggle = f"fx_open_{fid}"
        if key_toggle not in st.session_state:
            st.session_state[key_toggle] = False

        # Header row (title + hidden checkbox)
        tcol1, tcol2 = st.columns([9, 1])
        with tcol1:
            st.subheader(f"{home_name} vs {away_name} — {kickoff}")
        with tcol2:
            open_now = st.checkbox("", value=st.session_state[key_toggle], key=key_toggle)

        with st.expander("Show owned players", expanded=open_now):
            # Players in this fixture’s two clubs
            fixture_team_ids = {f.get("team_h"), f.get("team_a")}
            fixture_players = [p for p in players_by_id.values() if p.get("team") in fixture_team_ids]

            # Current ownership for this GW
            owned_players = [p for p in fixture_players if p["id"] in ownership]

            # Live contributions from the fixture stats → {player_id: [ "stat+val", ... ]}
            stat_map = {}
            for stat in (f.get("stats") or []):
                ident = STAT_LABELS.get(stat.get("identifier"), stat.get("identifier"))
                for side in ("h", "a"):
                    for entry in (stat.get(side) or []):
                        pid = entry.get("element")
                        val = entry.get("value")
                        if pid is not None:
                            stat_map.setdefault(pid, []).append(f"{ident}+{val}")

            if not owned_players:
                st.write("No owned players in this fixture.")
                continue

            # Build rows and render an HTML table
            owned_rows = []
            for p in owned_players:
                pid = p["id"]
                name = p.get("web_name", f"Player {pid}")
                abbr = _team_abbr(p.get("team"))
                owner = ownership.get(pid, "—")
                contrib_list = stat_map.get(pid, [])  # each item shown on its own line
                owned_rows.append({
                    "player_team": f"{name} [{abbr}]",
                    "owner": owner,
                    "contrib_list": contrib_list,
                })

            html = ['<table class="fixture-table">']
            html.append("<thead><tr><th>Player [Team]</th><th>Owned by</th><th>Contrib</th></tr></thead><tbody>")
            for r in owned_rows:
                contrib_html = "".join(f'<span class="item">{c}</span>' for c in r["contrib_list"]) or '<span class="item">—</span>'
                html.append(
                    f"<tr>"
                    f"<td class='player-team'>{r['player_team']}</td>"
                    f"<td>{r['owner']}</td>"
                    f"<td class='contrib'>{contrib_html}</td>"
                    f"</tr>"
                )
            html.append("</tbody></table>")
            st.markdown("\n".join(html), unsafe_allow_html=True)

# ---- Footer (sticky)
st.markdown(
    f"<div style='position:sticky; bottom:0; background:#0e1117; padding:6px 10px; "
    f"opacity:0.85; font-size:0.85rem;'>Last refresh: {now_str()} "
    f"{'• Auto-refresh ON (60s)' if auto and st_autorefresh else '• Auto-refresh OFF'}</div>",
    unsafe_allow_html=True,
)

# Dev diagnostics (optional)
with st.expander("Dev: diagnostics", expanded=False):
    st.write(f"entries: {len(league.get('league_entries') or [])} | "
             f"ownership items: {len(ownership)} | fixtures: {len(fixtures)}")
    if st.checkbox("Show raw ownership map"):
        st.json(ownership)
