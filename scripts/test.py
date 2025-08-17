import requests
import json

endpoints = [
    "https://draft.premierleague.com/api/bootstrap-dynamic",
    "https://draft.premierleague.com/api/game",
    "https://draft.premierleague.com/api/bootstrap-static",
    "https://draft.premierleague.com/api/league/12260/details",
    "https://draft.premierleague.com/api/league/12260/element-status",
    "https://draft.premierleague.com/api/draft/league/12260/trades",
    "https://draft.premierleague.com/api/pl/event-status",
    "https://draft.premierleague.com/api/event/1/live",
    "https://draft.premierleague.com/api/entry/177491/public",
    "https://draft.premierleague.com/api/draft/12260/choices",
    "https://draft.premierleague.com/api/entry/177491/event/1"
]

with open("fpl_api_dump.txt", "w", encoding="utf-8") as f:
    for url in endpoints:
        f.write(f"\n=== {url} ===\n")
        try:
            r = requests.get(url, timeout=10)
            f.write(f"Status: {r.status_code}\n")
            data = r.json()

            # Dump top-level structure only
            if isinstance(data, dict):
                for key, value in data.items():
                    f.write(f"- {key}: {type(value).__name__}\n")
            elif isinstance(data, list):
                f.write(f"Response is a list with {len(data)} items\n")
                if data and isinstance(data[0], dict):
                    f.write(f"First element keys: {list(data[0].keys())}\n")
                elif data:
                    f.write(f"First element type: {type(data[0]).__name__}\n")

            # Optionally write first 500 chars of the JSON to inspect
            snippet = json.dumps(data, indent=2)[:500]
            f.write(f"Snippet:\n{snippet}\n")

        except Exception as e:
            f.write(f"Error: {e}\n")
