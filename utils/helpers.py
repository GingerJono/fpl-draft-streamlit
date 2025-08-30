import pandas as pd

TEAM_COLOURS = {
    "Ekitikekitike": "#ffadad",
    "ØdegaardiansOfTheGal": "#ffd6a5",
    "Ranger Things": "#fdffb6",
    "Potter&The½FitWilson": "#caffbf",
    "Bowen Arrow": "#9bf6ff",
    "DioufFeelLuckyPunk?": "#a0c4ff",
    "No Juan Eyed Bernabe": "#bdb2ff",
}

def highlight_teams(df: pd.DataFrame):
    def _style(val):
        colour = TEAM_COLOURS.get(str(val), "")
        return f"background-color: {colour}" if colour else ""
    return df.style.applymap(_style)


# --- scoring rules
SCORING = {
    'long_play_limit': 60, 'short_play': 1, 'long_play': 2,
    'concede_limit': 2,
    'goals_conceded_GKP': -1, 'goals_conceded_DEF': -1, 'goals_conceded_MID': 0, 'goals_conceded_FWD': 0,
    'saves_limit': 3, 'saves': 1,
    'goals_scored_GKP': 10, 'goals_scored_DEF': 6, 'goals_scored_MID': 5, 'goals_scored_FWD': 4,
    'assists': 3,
    'clean_sheets_GKP': 4, 'clean_sheets_DEF': 4, 'clean_sheets_MID': 1, 'clean_sheets_FWD': 0,
    'defensive_contribution_limit_GKP': 0, 'defensive_contribution_limit_DEF': 10,
    'defensive_contribution_limit_MID': 12, 'defensive_contribution_limit_FWD': 12,
    'defensive_contribution_GKP': 0, 'defensive_contribution_DEF': 2,
    'defensive_contribution_MID': 2, 'defensive_contribution_FWD': 2,
    'penalties_saved': 5, 'penalties_missed': -2,
    'yellow_cards': -1, 'red_cards': -3, 'own_goals': -2,
    # don't use raw bonus here, we’ll recalc
    'bonus': 1,
}

def compute_bonus_for_fixture(players: list[dict]) -> dict[int, int]:
    """
    Given a list of players in one fixture with {"id": int, "bps": int},
    return {player_id: bonus_points}.
    Tie handling: all tied players take the higher bonus slot,
    and lower slots are skipped.
    """
    # sort descending by BPS
    players_sorted = sorted(players, key=lambda p: p.get("bps", 0), reverse=True)

    # group by BPS value
    from itertools import groupby
    bonus_map = {}
    bonus_slots = [3, 2, 1]  # available bonus slots

    i = 0
    for bps_val, group in groupby(players_sorted, key=lambda p: p.get("bps", 0)):
        group_list = list(group)
        if i >= len(bonus_slots):
            break
        # everyone in this tie group gets the current slot value
        slot_val = bonus_slots[i]
        for g in group_list:
            bonus_map[g["id"]] = slot_val
        # if tie consumed a slot, skip as many slots as group size
        # e.g. 2 players tied for top → both get 3, next slot to assign is "1"
        i += len(group_list)

    return bonus_map


def compute_score(stats: dict, pos: str, bonus_override: int | None = None) -> int:
    pts = 0
    minutes = stats.get("minutes", 0)

    if minutes >= SCORING['long_play_limit']:
        pts += SCORING['long_play']
    elif minutes > 0:
        pts += SCORING['short_play']

    if stats.get("goals_scored"):
        pts += stats["goals_scored"] * SCORING[f"goals_scored_{pos}"]

    pts += stats.get("assists", 0) * SCORING['assists']

    if minutes >= SCORING['long_play_limit'] and stats.get("clean_sheets"):
        pts += SCORING[f"clean_sheets_{pos}"]

    if pos in ("GKP","DEF"):
        conceded = stats.get("goals_conceded", 0)
        if conceded >= SCORING['concede_limit']:
            pts += (conceded // SCORING['concede_limit']) * SCORING[f"goals_conceded_{pos}"]

    if pos == "GKP":
        saves = stats.get("saves", 0)
        pts += (saves // SCORING['saves_limit']) * SCORING['saves']

    dc = stats.get("defensive_contribution", 0)
    limit = SCORING[f"defensive_contribution_limit_{pos}"]
    if limit and dc:
        pts += (dc // limit) * SCORING[f"defensive_contribution_{pos}"]

    pts += stats.get("penalties_saved", 0) * SCORING['penalties_saved']
    pts += stats.get("penalties_missed", 0) * SCORING['penalties_missed']

    pts += stats.get("yellow_cards", 0) * SCORING['yellow_cards']
    pts += stats.get("red_cards", 0) * SCORING['red_cards']
    pts += stats.get("own_goals", 0) * SCORING['own_goals']

    # use recalculated bonus if provided
    if bonus_override is not None:
        pts += bonus_override
    else:
        pts += stats.get("bonus", 0) * SCORING['bonus']

    return pts
