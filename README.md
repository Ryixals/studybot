# Study Bot

A Discord bot that tracks study time across different subjects, maintains progress dashboards, displays leaderboards, and supports offline command queuing.

## Features

- Track study time per subject (English, Math, Science, GP)
- Remove incorrect or over-reported study time
- View personal progress dashboard with visual progress bars (filter by Today/Week/Month/Year/All)
- Global leaderboard with time‑period filters
- Paginated timeline of recent study sessions (adds/removes)
- Offline command support with recap feature (rich embeds)
- Persistent database storage for all user data

## Commands

### Slash Commands

| Command | Description | Example |
| ------- | ----------- | ------- |
| `/add <subject> <minutes>` | Add study time (1‑720 min) | `/add Math 30` |
| `/remove <subject> <minutes>` | Remove study time | `/remove English 15` |
| `/check [period]` | Progress dashboard (today/week/month/year/all) | `/check week` |
| `/leaderboard [period]` | Global leaderboard | `/leaderboard month` |
| `/timeline` | Paginated history of your entries | `/timeline` |
| `/help` | Show all commands | `/help` |

### Offline Commands

When the bot is offline, use `r;` prefix, they will be processed when the bot returns online.

| Command | Description | Example |
| ------- | ----------- | ------- |
| `r;add subject minutes` | Add study time | `r;add Science 45` |
| `r;remove subject minutes` | Remove study time | `r;remove GP 10` |
| `r;check` | View progress (all‑time) | `r;check` |
| `r;leaderboard` | View global leaderboard | `r;leaderboard` |
| `r;timeline` | Show recent sessions | `r;timeline` |
| `r;help` | Show offline help | `r;help` |

## Setup

### Installation

1. Clone the repo
2. `pip install -r requirements.txt`
3. Create `.env` with `DISCORD_TOKEN=your_token_here`
4. `python bot.py`

### Configuration (config.py)

- `SUBJECTS` – subjects and embed colors
- `COMMAND_MAX_MINUTES` – max per add/remove (default 720)
- `RECAP_WINDOW_HOURS` – how far back to scan for offline commands (168h = 7 days)
- `RECAP_MESSAGES_PER_CHANNEL` – max messages to scan per channel (500)

## Database

SQLite with tables:

- `study_sessions` – every add/remove (used for period filters and timeline)
- `total_study_time` – aggregated all‑time totals
- `bot_state` – last processed message ID for recap

## License

MIT License
