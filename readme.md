# FPL Draft API – Core Structure

## Global / Static
- **`/api/bootstrap-static`**
  - Reference data – load once and cache.
  - Includes:
    - `elements`: all players with IDs and stats.
    - `teams`: Premier League teams.
    - `element_types`: positions (GKP/DEF/MID/FWD).
    - `events`, `fixtures`, `settings`.

- **`/api/bootstrap-dynamic`**
  - Session-level data (depends on login).
  - Mostly empty when unauthenticated.

- **`/api/game`**
  - Current season/game state.
  - Fields: `current_event`, `next_event`, `waivers_processed`, `trades_time_for_approval`.

## League Context
- **`/api/league/{id}/details`**
  - League metadata.
  - `league`: name, draft date, settings.
  - `league_entries`: managers.
  - `matches`: H2H fixtures.
  - `standings`.

- **`/api/league/{id}/element-status`**
  - Player ownership status in the league.
  - Example: `{element: 170, owner: null}` → free agent.

- **`/api/draft/league/{id}/trades`**
  - Trade proposals and completed trades.

- **`/api/draft/{league_id}/choices`**
  - Draft log – who picked which player at what time.

## Events / Gameweeks
- **`/api/pl/event-status`**
  - Timeline of FPL site processing for each event.
  - Tracks if `bonus_added`, `leagues_updated`, etc.

- **`/api/event/{id}/live`**
  - Live stats for all players in that GW.
  - `stats`: raw match stats (minutes, goals, assists).
  - `explain`: breakdown of FPL points.

- **`/api/entry/{id}/event/{gw}`**
  - A manager’s team for a specific GW.
  - `picks`: XI, bench, captaincy.
  - `entry_history`: points, transfers.
  - `subs`: auto-subs.

## Manager Info
- **`/api/entry/{id}/public`**
  - Public profile for a manager.
  - Team name, manager name, total points, favourite PL club, etc.


https://draft.premierleague.com/api/bootstrap-dynamic
https://draft.premierleague.com/api/game
https://draft.premierleague.com/api/bootstrap-static
https://draft.premierleague.com/api/league/12260/details
https://draft.premierleague.com/api/league/12260/element-status
https://draft.premierleague.com/api/draft/league/12260/trades
https://draft.premierleague.com/api/pl/event-status
https://draft.premierleague.com/api/event/1/live
https://draft.premierleague.com/api/entry/177491/public
https://draft.premierleague.com/api/draft/12260/choices
https://draft.premierleague.com/api/entry/177491/event/1

https://draft.premierleague.com/api/draft/entry/177491/transactions // requires auth
https://draft.premierleague.com/api/watchlist/177491 // requires auth
https://draft.premierleague.com/api/entry/177491/my-team // requires auth