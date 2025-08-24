TEAM_COLOURS = {
    "Ekitikekitike": "#ffadad",
    "ØdegaardiansOfTheGal": "#ffd6a5",
    "Ranger Things": "#fdffb6",
    "Potter&The½FitWilson": "#caffbf",
    "Bowen Arrow": "#9bf6ff",
    "DioufFeelLuckyPunk?": "#a0c4ff",
    "No Juan Eyed Bernabe": "#bdb2ff",
}

import pandas as pd

def highlight_teams(df: pd.DataFrame):
    def _style(val):
        colour = TEAM_COLOURS.get(str(val), "")
        return f"background-color: {colour}" if colour else ""
    return df.style.applymap(_style)
