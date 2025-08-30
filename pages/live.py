# pages/live.py
import streamlit as st
from utils.helpers import highlight_teams, TEAM_COLOURS
from datetime import datetime, timezone
import pandas as pd

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

st.set_page_config(layout="wide")

LOCAL_TZ = ZoneInfo("Europe/London") if ZoneInfo else timezone.utc

def now_str():
    return datetime.now(LOCAL_TZ).strftime("%a %d %b %Y, %H:%M:%S %Z")

def fixture_label(f):
    home = _team_abbr(f.get("team_h"))
    away = _team_abbr(f.get("team_a"))
    # compact date/time (local tz, no year)
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
LEAGUE_ID = 12260
status    = get_game_status() or {}
gw        = status.get("current_event", 1)
bootstrap = get_bootstrap() or {}
fixtures  = sorted(get_fixtures(gw) or [], key=lambda x: x.get("kickoff_time") or "")
league    = get_league_details(LEAGUE_ID) or {}
live      = get_event_live(gw) or {}
# Build CURRENT ownership (element_id -> owner team name) from each entry's GW picks
# Build ownership (element -> entry_id) and entry_id -> name map
from utils.api import build_current_ownership_ids, league_entries_map

ownership_ids = build_current_ownership_ids(LEAGUE_ID, gw, starters_only=False)
entries_map = league_entries_map(LEAGUE_ID)                                # entry_id -> entry obj

# Team + player lookups
teams = {
    t["id"]: {"name": t["name"], "abbr": t["short_name"]}
    for t in (bootstrap.get("teams") or [])
}

players_by_id = {int(p["id"]): p for p in (bootstrap.get("elements") or [])}

def _team_name(team_id: int) -> str:
    t = teams.get(team_id, {})
    return (t.get("name") if isinstance(t, dict) else str(t)) or f"Team {team_id}"

def _team_abbr(team_id: int) -> str:
    t = teams.get(team_id, {})
    return t.get("abbr", "") if isinstance(t, dict) else ""

LEAGUE_ID = 12260
gw = status.get("current_event", 1)

# element -> entry_name
ownership = {pid: entries_map.get(eid, {}).get("entry_name", "—")
             for pid, eid in ownership_ids.items()}

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
                owner_eid = ownership_ids.get(pid)
                owner = entries_map.get(owner_eid, {}).get("entry_name", "—")

                stats   = live_stats_map.get(pid, {})
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

                rows.append({
                    "Player [Team]": f"{name} [{team_abbr}]",
                    "Owned by": owner,
                    "Minutes": minutes,
                    "Points": points,
                    "Contrib": " ".join(contribs) if contribs else "—",
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
    st.write(f"{len(bootstrap)}")
    st.write(
        f"entries: {len(league.get('league_entries') or [])} | "
        f"ownership_ids: {len(ownership_ids)} | fixtures: {len(fixtures)} | "
        f"live players: {len(live_stats_map)}"
    )

    pid_probe = st.text_input("Probe element_id (e.g. 661)", value="")
    if pid_probe.strip().isdigit():
        from utils.api import who_owns_element
        eid, name = who_owns_element(LEAGUE_ID, gw, int(pid_probe))
        st.write("Actual GW owner →", {"entry_id": eid, "entry_name": name})

    # --- show fixtures for this gameweek
    if fixtures:
        st.subheader(f"Fixtures GW{gw}")
        fix_table = []
        for f in fixtures:
            home_id = f.get("team_h")
            away_id = f.get("team_a")
            home = teams.get(home_id, {}).get("name", home_id)
            away = teams.get(away_id, {}).get("name", away_id)
            ko   = format_kickoff(f.get("kickoff_time"))
            fix_table.append({
                "HomeID": home_id, "Home": home,
                "AwayID": away_id, "Away": away,
                "Kickoff": ko,
                "FixtureLabel": fixture_label(f),
            })
        st.dataframe(pd.DataFrame(fix_table))
    else:
        st.info("No fixtures returned for this GW")

    # --- show teams mapping (bootstrap)
    if teams:
        st.subheader("Teams (bootstrap)")
        team_table = [{"ID": tid, "Name": t["name"], "Abbr": t["abbr"]}
                      for tid, t in teams.items()]
        st.dataframe(pd.DataFrame(team_table).sort_values("ID"))
