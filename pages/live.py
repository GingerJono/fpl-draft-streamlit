# pages/live.py
import streamlit as st
from datetime import datetime, timezone
try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None

# Optional autorefresh (pip install streamlit-autorefresh)
try:
    from streamlit_autorefresh import st_autorefresh
except Exception:
    st_autorefresh = None

from utils.api import (
    get_game_status, get_bootstrap, get_fixtures,
    get_league_details, get_entry_event, get_event_live,
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

# ---- Auto-refresh (60s)
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
    st.info("Tip: pip install streamlit-autorefresh for smoother updates.")

# ---- Load core data
status    = get_game_status() or {}
gw        = status.get("current_event", 1)
bootstrap = get_bootstrap() or {}
fixtures  = sorted(get_fixtures(gw) or [], key=lambda x: x.get("kickoff_time") or "")
league    = get_league_details(LEAGUE_ID) or {}
live      = get_event_live(gw) or {}

# Team + player lookups
teams = {
    t["id"]: {"name": t["name"], "abbr": t["short_name"]}
    for t in (bootstrap.get("teams") or [])
}
players_by_id = {p["id"]: p for p in (bootstrap.get("elements") or [])}

def _team_name(team_id: int) -> str:
    t = teams.get(team_id, {})
    return (t.get("name") if isinstance(t, dict) else str(t)) or f"Team {team_id}"

def _team_abbr(team_id: int) -> str:
    t = teams.get(team_id, {})
    return t.get("abbr", "") if isinstance(t, dict) else ""

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

# ---- Live stats map from /event/{gw}/live
# Endpoint shape can be dict { "82": {...} } or list [{id, stats, ...}]
live_elements = live.get("elements", {})
live_stats_map = {}

if isinstance(live_elements, dict):
    for k, v in live_elements.items():
        try:
            pid = int(k)
        except Exception:
            continue
        live_stats_map[pid] = v.get("stats", {}) or {}
elif isinstance(live_elements, list):
    for v in live_elements:
        pid = v.get("id")
        if pid is not None:
            live_stats_map[pid] = v.get("stats", {}) or {}

# ---- CSS (hide checkboxes, tidy table, no-wrap player/team, line-broken contrib)
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
    .player-team { white-space: nowrap !important; }
    .contrib { font-size: 0.85rem; line-height: 1.15; opacity: 0.9; }
    .contrib .item { display:block; }  /* each stat on its own line */
    </style>
    """,
    unsafe_allow_html=True
)

# Short labels for stats
STAT_LABELS = {
    "minutes": "min",
    "goals_scored": "g",
    "assists": "a",
    "clean_sheets": "cs",
    "goals_conceded": "gc",
    "yellow_cards": "yc",
    "red_cards": "rc",
    "saves": "saves",
    "bonus": "b",
    "bps": "bps",
    "defensive_contribution": "def",
    "penalties_saved": "ps",
    "penalties_missed": "pm",
    "own_goals": "og",
}

# Useful display order (minutes first)
STAT_ORDER = [
    "minutes", "goals_scored", "assists", "clean_sheets", "goals_conceded",
    "yellow_cards", "red_cards", "saves", "bonus", "bps",
    "defensive_contribution", "penalties_saved", "penalties_missed", "own_goals",
]

# ---- Header
st.title(f"Fixtures for Gameweek {gw}")
st.caption(f"Last refresh: {now_str()}")

if not fixtures:
    st.info("No fixtures found.")
else:
    for f in fixtures:
        fid = f.get("id")
        home_name = _team_name(f.get("team_h"))
        away_name = _team_name(f.get("team_a"))
        kickoff = format_kickoff(f.get("kickoff_time"))

        key_toggle = f"fx_open_{fid}"
        if key_toggle not in st.session_state:
            st.session_state[key_toggle] = False

        tcol1, tcol2 = st.columns([9, 1])
        with tcol1:
            st.subheader(f"{home_name} vs {away_name} — {kickoff}")
        with tcol2:
            open_now = st.checkbox("", value=st.session_state[key_toggle], key=key_toggle)

        with st.expander("Show owned players", expanded=open_now):
            # Players involved in this fixture (by team)
            fixture_team_ids = {f.get("team_h"), f.get("team_a")}
            fixture_players = [p for p in players_by_id.values() if p.get("team") in fixture_team_ids]

            # Only those owned right now
            owned_players = [p for p in fixture_players if p["id"] in ownership]

            if not owned_players:
                st.write("No owned players in this fixture.")
                continue

            # Build rows with minutes + contrib (from live stats)
            owned_rows = []
            for p in owned_players:
                pid = p["id"]
                name = p.get("web_name", f"Player {pid}")
                abbr = _team_abbr(p.get("team"))
                owner = ownership.get(pid, "—")

                pstats = live_stats_map.get(pid, {})  # dict of live stats
                minutes_val = pstats.get("minutes") if isinstance(pstats, dict) else None
                points_val = pstats.get("total_points") if isinstance(pstats, dict) else None


                # Build contrib list in a stable order; include only non-zero (except minutes)
                contrib_list = []
                for key in STAT_ORDER:
                    if key == "minutes":
                        continue
                    val = pstats.get(key) if isinstance(pstats, dict) else None
                    if isinstance(val, (int, float)) and val != 0:
                        label = STAT_LABELS.get(key, key)
                        contrib_list.append(f"{label}+{int(val) if isinstance(val, (int, float)) else val}")

                # Ensure minutes also appears in Contrib at the top
                if minutes_val is not None:
                    contrib_list = [f"min+{minutes_val}"] + contrib_list

                owned_rows.append({
                    "player_team": f"{name} [{abbr}]",
                    "owner": owner,
                    "minutes": minutes_val if minutes_val is not None else "—",
                    "points": points_val if points_val is not None else "—",
                    "contrib_list": contrib_list,
                })

            # Render HTML table so we can keep formatting control
            html = ['<table class="fixture-table">']
            html.append("<thead><tr><th>Player [Team]</th><th>Owned by</th><th>Minutes</th><th>Points</th><th>Contrib</th></tr></thead><tbody>")
            for r in owned_rows:
                contrib_html = "".join(f'{c} ' for c in r["contrib_list"]) or '<span class="item">—</span>'
                html.append(
                    f"<tr>"
                    f"<td class='player-team'>{r['player_team']}</td>"
                    f"<td>{r['owner']}</td>"
                    f"<td>{r['minutes']}</td>"
                    f"<td>{r['points']}</td>"
                    f"<td class='contrib'>{contrib_html}</td>"
                    f"</tr>"
                )
            html.append("</tbody></table>")
            st.markdown("\n".join(html), unsafe_allow_html=True)

# ---- Sticky footer
st.markdown(
    f"<div style='position:sticky; bottom:0; background:#0e1117; padding:6px 10px; "
    f"opacity:0.85; font-size:0.85rem;'>Last refresh: {now_str()} "
    f"{'• Auto-refresh ON (60s)' if auto and st_autorefresh else '• Auto-refresh OFF'}</div>",
    unsafe_allow_html=True,
)

# Dev diagnostics (optional)
with st.expander("Dev: diagnostics", expanded=False):
    st.write(f"entries: {len(league.get('league_entries') or [])} | "
             f"ownership: {len(ownership)} | fixtures: {len(fixtures)} | live players: {len(live_stats_map)}")
    if st.checkbox("Show raw ownership map"):
        st.json(ownership)
