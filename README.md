# Study Bot

A Discord bot that tracks study time across different subjects, maintains progress dashboards, displays leaderboards, and supports offline command queuing.

## Features

- Track study time per subject (English, Math, Science, GP)
- Remove incorrect or over-reported study time
- View personal progress dashboard with visual progress bars
- Global leaderboard showing top students
- Offline command support with recap feature
- Persistent database storage for all user data

## Commands

### Slash Commands

| Command | Description | Example |
| ------- | ----------- | ------- |
| `/add <subject> <minutes>` | Add study time to a subject (1-720 minutes) | `/add Math 30` |
| `/remove <subject> <minutes>` | Remove study time from a subject | `/remove English 15` |
| `/check` | Display your study progress dashboard | `/check` |
| `/leaderboard` | Show global leaderboard of top students | `/leaderboard` |

### Offline Commands (Recap)

When the bot is offline, you can type commands in any channel using the `r;` prefix. The bot will process them automatically when it comes back online.

| Command | Description | Example |
| ------- | ----------- | ------- |
| `r;add <subject> <minutes>` | Add study time | `r;add Science 45` |
| `r;remove <subject> <minutes>` | Remove study time | `r;remove GP 10` |
| `r;check` | View your progress | `r;check` |
| `r;leaderboard` | View global leaderboard | `r;leaderboard` |

**Note:** Subjects are case‑insensitive for offline commands (`r;add math 30` works).

## Setup

### Prerequisites

- Python 3.8 or higher
- A Discord bot token from the [Discord Developer Portal](https://discord.com/developers/applications)

### Installation

1. **Clone the repository**

   ```bash
   git clone <repository-url>
   cd study-bot
   ```

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Create a `.env` file**

   ```env
   DISCORD_TOKEN=your_bot_token_here
   DATABASE_PATH=tracker.db
   ```

4. **Run the bot**

   ```bash
   python bot.py
   ```

## Configuration

Edit `config.py` to customize:

| Variable | Description | Default |
| -------- | ----------- | ------- |
| `SUBJECTS` | Subjects to track with embed colors | English, Math, Science, GP |
| `COMMAND_MAX_MINUTES` | Maximum minutes per add/remove | 720 (12 hours) |
| `RECAP_WINDOW_HOURS` | How far back to scan for offline commands | 168 (7 days) |
| `RECAP_MESSAGES_PER_CHANNEL` | Max messages to scan per channel | 500 |

## Database Schema

The bot uses SQLite with two main tables:

- `study_sessions` - Individual study entries (add/remove logs)
- `total_study_time` - Aggregated totals per user per subject
- `bot_state` - Tracks last processed message ID for recap feature

## Error Handling

- Input validation prevents negative or excessive time entries
- Database rollback on errors
- Graceful error messages for invalid commands
- Cooldown system prevents spam (configurable via `COMMAND_COOLDOWN`)

## License

MIT

## Support

For issues or feature requests, please open an issue on GitHub.
