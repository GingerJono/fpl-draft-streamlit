# pages/teams.py
import streamlit as st
import pandas as pd
from datetime import datetime, timezone
try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None

from utils.api import get_game_status, build_gw_player_table, get_league_details

st.set_page_config(layout="wide")

LEAGUE_ID = 12260
LOCAL_TZ = ZoneInfo("Europe/London") if ZoneInfo else timezone.utc

def now_str():
    return datetime.now(LOCAL_TZ).strftime("%a %d %b %Y, %H:%M:%S %Z")

TEAM_COLOURS = {
    "Ekitikekitike": "#ffadad",
    "ØdegaardiansOfTheGal": "#ffd6a5",
    "Ranger Things": "#fdffb6",
    "Potter&The½FitWilson": "#caffbf",
    "Bowen Arrow": "#9bf6ff",
    "DioufFeelLuckyPunk?": "#a0c4ff",
    "No Juan Eyed Bernabe": "#bdb2ff",
}

POS_ORDER = {"GKP": 1, "DEF": 2, "MID": 3, "FWD": 4}
def lineup_rank(slot: str) -> int:
    if slot == "XI":
        return 0
    if slot.startswith("Bench"):
        try:
            return int(slot.split()[-1])
        except Exception:
            return 9
    return 9

def style_owner(df, col="Owner"):
    if col not in df.columns:
        return df
    def _cell(v):
        c = TEAM_COLOURS.get(str(v), "")
        return f"background-color: {c}" if c else ""
    return df.style.applymap(_cell, subset=[col])

# ------ Data
status = get_game_status() or {}
gw = status.get("current_event", 1)
rows = build_gw_player_table(LEAGUE_ID, gw)
league = get_league_details(LEAGUE_ID) or {}

# Build GW points map + match info
gw_points_map = {}
match_map = {}  # entry_id -> match dict
for m in (league.get("matches") or []):
    if m.get("event") == gw:
        gw_points_map[m["league_entry_1"]] = m.get("league_entry_1_points", 0)
        gw_points_map[m["league_entry_2"]] = m.get("league_entry_2_points", 0)
        match_map[m["league_entry_1"]] = m
        match_map[m["league_entry_2"]] = m

entry_map = {e["id"]: e for e in (league.get("league_entries") or []) if e.get("entry_id")}

st.title(f"Teams — GW{gw}")
st.caption(f"Last refresh: {now_str()}")

if not rows:
    st.info("No data.")
    st.stop()

df = pd.DataFrame(rows)
cols = ["Name","Position","Team","DraftRank","DraftedTo","GWPoints","Minutes","Contribs","LineupSlot"]
df = df[cols].copy()

team_names = sorted(df["DraftedTo"].dropna().unique().tolist())
tabs = st.tabs(team_names)

for name, tab in zip(team_names, tabs):
    with tab:
        d = df[df["DraftedTo"] == name].copy()
        d["pos_order"] = d["Position"].map(POS_ORDER).fillna(99).astype(int)
        d["lineup_order"] = d["LineupSlot"].map(lineup_rank).astype(int)
        d = d.sort_values(["lineup_order", "pos_order", "Name"], kind="mergesort")

        # find entry_id
        entry_id = None
        for e in league.get("league_entries") or []:
            if e["entry_name"] == name:
                entry_id = e["id"]
                break

        team_points = gw_points_map.get(entry_id, "—")
        st.markdown(f"**GW Points: {team_points}**")

        # --- show score table with this team always on the left
        match = match_map.get(entry_id)
        if match:
            if entry_id == match["league_entry_1"]:
                opp_id = match["league_entry_2"]
                left_score = match.get("league_entry_1_points", 0)
                right_score = match.get("league_entry_2_points", 0)
            else:
                opp_id = match["league_entry_1"]
                left_score = match.get("league_entry_2_points", 0)
                right_score = match.get("league_entry_1_points", 0)

            opp_name = entry_map.get(opp_id, {}).get("entry_name", "—")

            score_data = pd.DataFrame([{
                "Team": name,
                "Score": left_score,
                "Opponent Score": right_score,
                "Opponent": opp_name
            }])
            st.table(score_data)

        # Pretty columns
        d_display = d.rename(columns={
            "Name": "Player",
            "Position": "Pos",
            "Team": "Club",
            "DraftRank": "Draft Rank",
            "DraftedTo": "Owner",
            "GWPoints": "GW Pts",
            "LineupSlot": "Slot"
        })[["Player","Pos","Club","Draft Rank","Owner","Slot","Minutes","GW Pts","Contribs"]]

        st.table(style_owner(d_display, col="Owner"))
