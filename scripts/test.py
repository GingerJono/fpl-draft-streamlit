import requests, json

league_id = 12260
choices = requests.get(f"https://draft.premierleague.com/api/draft/{league_id}/choices").json()

with open("choices_dump.txt", "w", encoding="utf-8") as f:
    json.dump(choices, f, indent=2)
