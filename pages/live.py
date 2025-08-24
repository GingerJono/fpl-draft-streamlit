# pages/live.py
import streamlit as st
from utils.helpers import highlight_teams, TEAM_COLOURS
from datetime import datetime, timezone
try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None

# Build CURRENT ownership (element_id -> owner team name) from each entry's GW picks
from utils.api import build_current_ownership

# Optional autorefresh (pip install streamlit-autorefresh)
try:
    from streamlit_autorefresh import st_autorefresh
except Exception:
    st_autorefresh = None

from utils.api import (
    get_game_status, get_bootstrap, get_fixtures,
    get_league_details, get_entry_event, get_event_live,
)

st.set_page_config(layout="wide")

LEAGUE_ID = 12260
LOCAL_TZ = ZoneInfo("Europe/London") if ZoneInfo else timezone.utc

def now_str():
    return datetime.now(LOCAL_TZ).strftime("%a %d %b %Y, %H:%M:%S %Z")

def fixture_label(f):
    home = _team_abbr(f.get("team_h"))
    away = _team_abbr(f.get("team_a"))
    # compact date/time (local tz, no year)
    dt_str = ""
    if f.get("kickoff_time"):
        try:
            dt = datetime.fromisoformat(f["kickoff_time"].replace("Z", "+00:00"))
            dt_local = dt.astimezone(LOCAL_TZ)
            dt_str = dt_local.strftime("%a%H%M")  # e.g. Sat1500
        except Exception:
            pass
    return f"{home}-{away}"


def format_kickoff(iso_utc: str) -> str:
    if not iso_utc:
        return ""
    try:
        dt = datetime.fromisoformat(iso_utc.replace("Z", "+00:00"))
        return dt.astimezone(LOCAL_TZ).strftime("%a %d %b, %H:%M %Z")
    except Exception:
        return iso_utc

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

LEAGUE_ID = 12260
gw = status.get("current_event", 1)

# starters_only=True -> only XI (multiplier > 0); False -> XI + bench
ownership = build_current_ownership(LEAGUE_ID, gw, starters_only=False)

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
    # Create tab labels like "Arsenal vs Chelsea"
    tab_labels = [fixture_label(f) for f in fixtures]
    tabs = st.tabs(tab_labels)

    for f, tab in zip(fixtures, tabs):
        home_name = _team_name(f.get("team_h"))
        away_name = _team_name(f.get("team_a"))
        kickoff   = format_kickoff(f.get("kickoff_time"))

        with tab:
            st.subheader(f"{home_name} vs {away_name}\n{kickoff}")

            # Players involved in this fixture (by team)
            fixture_team_ids = {f.get("team_h"), f.get("team_a")}
            fixture_players = [p for p in players_by_id.values() if p.get("team") in fixture_team_ids]

            # Only those owned right now
            owned_players = [p for p in fixture_players if p["id"] in ownership]

            if not owned_players:
                st.write("No owned players in this fixture.")
                continue

            # Build rows with stats
            rows = []
            for p in owned_players:
                pid = int(p["id"])
                name = p.get("web_name", f"Player {pid}")
                team_abbr = teams.get(p["team"], {}).get("abbr", "")
                owner = ownership.get(pid, "—")

                stats = live_stats_map.get(pid, {})
                minutes = stats.get("minutes", 0)
                points  = stats.get("total_points", 0)

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

                contrib_str = " ".join(contribs) if contribs else "—"

                rows.append({
                    "Player [Team]": f"{name} [{team_abbr}]",
                    "Owned by": owner,
                    "Minutes": minutes,
                    "Points": points,
                    "Contrib": contrib_str,
                })

            # Render table
            html = ['<table class="fixture-table">']
            html.append("<thead><tr><th>Player [Team]</th><th>Owned by</th><th>Minutes</th><th>Points</th><th>Contrib</th></tr></thead><tbody>")
            for r in rows:
                owner = r['Owned by']
                colour = TEAM_COLOURS.get(owner, "")
                style = f" style='background-color:{colour};'" if colour else ""
                html.append(
                    f"<tr>"
                    f"<td class='player-team'>{r['Player [Team]']}</td>"
                    f"<td{style}>{owner}</td>"
                    f"<td>{r['Minutes']}</td>"
                    f"<td>{r['Points']}</td>"
                    f"<td class='contrib'>{r['Contrib']}</td>"
                    f"</tr>"
                )
            html.append("</tbody></table>")
            st.markdown("\n".join(html), unsafe_allow_html=True)

# Dev diagnostics (optional)
with st.expander("Dev: diagnostics", expanded=False):
    st.write(f"entries: {len(league.get('league_entries') or [])} | "
             f"ownership: {len(ownership)} | fixtures: {len(fixtures)} | live players: {len(live_stats_map)}")
    if st.checkbox("Show raw ownership map"):
        st.json(ownership)
