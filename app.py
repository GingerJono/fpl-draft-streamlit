import requests
import streamlit as st
import pandas as pd

st.set_page_config(page_title="FPL Draft – League Snapshot", layout="wide")
st.title("FPL Draft – League Snapshot")

LEAGUE_ID = 12260
URL = f"https://draft.premierleague.com/api/league/{LEAGUE_ID}/details"

@st.cache_data(ttl=30)
def fetch_league() -> dict:
    r = requests.get(URL, timeout=10)
    r.raise_for_status()
    return r.json()

def status_str(p1: int, p2: int, finished: bool) -> str:
    if finished:
        if p1 > p2: return "won"
        if p1 < p2: return "lost"
        return "draw"
    if p1 > p2: return "leading"
    if p1 < p2: return "trailing"
    return "level"

try:
    data = fetch_league()
    league = data["league"]
    entries = pd.DataFrame(data["league_entries"])
    matches = pd.DataFrame(data["matches"])
    standings = pd.DataFrame(data.get("standings", []))

    id_to_name = dict(zip(entries["id"], entries["entry_name"].fillna("(TBD)")))

    st.subheader(league["name"])
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Draft status", league.get("draft_status", ""))
    c2.metric("Max entries", league.get("max_entries", ""))
    c3.metric("Scoring", league.get("scoring", ""))
    c4.metric("Waivers", "Yes" if league.get("trades") == "y" else "No")

    # ---- Current/active GW snapshot ----
    if not matches.empty:
        current_evts = sorted(set(matches.loc[matches["started"] == True, "event"]))
        current_event = current_evts[0] if current_evts else None
    else:
        current_event = None

    if current_event is not None:
        st.markdown(f"### Gameweek {current_event} – Live/Latest Fixtures")
        m_now = matches[matches["event"] == current_event].copy()
        m_now["Team 1"] = m_now["league_entry_1"].map(id_to_name)
        m_now["Team 2"] = m_now["league_entry_2"].map(id_to_name)
        m_now["T1 pts"] = m_now["league_entry_1_points"]
        m_now["T2 pts"] = m_now["league_entry_2_points"]
        m_now["Status"] = [
            status_str(p1, p2, fin)
            for p1, p2, fin in zip(m_now["T1 pts"], m_now["T2 pts"], m_now["finished"])
        ]
        m_now["Δ"] = (m_now["T1 pts"] - m_now["T2 pts"]).abs()
        st.dataframe(
            m_now[["Team 1", "T1 pts", "Team 2", "T2 pts", "Status", "Δ"]]
            .sort_values("Δ", ascending=False)
            .drop(columns=["Δ"]),
            use_container_width=True
        )

        # Per-team snapshot (who’s leading/trailing)
        rows = []
        for _, r in m_now.iterrows():
            rows.append({"Team": r["Team 1"], "Opponent": r["Team 2"], "Points": r["T1 pts"],
                         "Status": status_str(r["T1 pts"], r["T2 pts"], r["finished"])})
            rows.append({"Team": r["Team 2"], "Opponent": r["Team 1"], "Points": r["T2 pts"],
                         "Status": status_str(r["T2 pts"], r["T1 pts"], r["finished"])})
        team_now = pd.DataFrame(rows)
        st.markdown("#### Team snapshot (this gameweek)")
        st.dataframe(team_now.sort_values(["Status", "Points"], ascending=[True, False]),
                     use_container_width=True)

        a, b, c = st.columns(3)
        a.metric("Leading teams", int((team_now["Status"] == "leading").sum()))
        b.metric("Trailing teams", int((team_now["Status"] == "trailing").sum()))
        c.metric("Level ties", int((team_now["Status"] == "level").sum() // 2))
    else:
        st.info("No started fixtures yet.")

    # ---- Standings (may be zero until GW completes) ----
    st.markdown("### Standings (from API)")
    if standings.empty:
        st.write("No standings available yet.")
    else:
        standings = standings.merge(entries[["id", "entry_name"]],
                                    left_on="league_entry", right_on="id", how="left")
        standings = standings.rename(columns={"entry_name": "Team"})[
            ["Team", "matches_won", "matches_drawn", "matches_lost",
             "points_for", "points_against", "total", "rank"]
        ].sort_values(["total", "points_for"], ascending=[False, False])
        st.dataframe(standings, use_container_width=True)

    # ---- Waiver order ----
    if "waiver_pick" in entries:
        st.markdown("### Waiver order")
        waiver = entries[["waiver_pick", "entry_name"]].dropna().sort_values("waiver_pick")
        waiver.columns = ["Waiver #", "Team"]
        st.table(waiver)

    with st.expander("Raw API JSON"):
        st.json(data)

except requests.RequestException as e:
    st.error(f"API error: {e}")
except Exception as e:
    st.exception(e)
