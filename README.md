# TsnobisFurceli

A zero-cost, self-hosted news aggregator that watches Georgian news feeds and pushes new stories to Telegram.

## How it works

Every 6 hours, a GitHub Actions workflow runs `main.py`, which:

1. Fetches each feed listed in the `SOURCES` dict (stdlib `urllib`, custom `User-Agent` header).
2. Parses items with `xml.etree.ElementTree`.
3. Diffs links against `sent_stories.json` to find new stories.
4. Posts new stories to a Telegram chat via the Bot API.
5. Persists the updated link state, which the workflow commits back to the repo.

A source seen for the first time is seeded into `sent_stories.json` without sending notifications, so adding a new feed doesn't dump its entire history into your chat.

## Adding a source

Add an entry to the `SOURCES` dict in `main.py`:

- **Standard website**: use its RSS/Atom feed URL directly.
- **Facebook page**: run it through a bridge like [FetchRSS](https://fetchrss.com) or [RSS.app](https://rss.app) and paste the resulting `.xml` URL.

No other code changes are required.

## Getting the Telegram credentials

The bot gets its own dedicated chat - it does not post into any of your existing chats. Messaging a bot directly opens a private one-on-one conversation with it.

1. **`TELEGRAM_TOKEN`** - open Telegram and message [@BotFather](https://t.me/BotFather). Send `/newbot`, pick a display name (e.g. *TsnobisFurceli*) and a unique username ending in `bot` (e.g. `TsnobisFurceliBot`). BotFather replies with a token like `6849204910:AAFlS...` - that's your `TELEGRAM_TOKEN`.
2. **`CHAT_ID`** - message [@userinfobot](https://t.me/userinfobot); it replies with your numeric account ID (e.g. `4829104`). For a private conversation with a bot, the chat ID is simply your own user ID.
3. **Open the chat** - find your new bot by its username and press **Start**. This step is required: Telegram bots cannot message a user who has never started a conversation with them. All notifications will arrive in this dedicated chat.

### Keeping the credentials secret

The token and chat ID are never written into any file in this repository. They live only as **GitHub Actions secrets** (step 2 below): encrypted values stored by GitHub, injected into the workflow at runtime as environment variables, and automatically masked (`***`) if they ever appear in workflow logs. The script reads them with `os.environ` and fails fast if they are missing. Just never hardcode them in `main.py` or commit an `.env` file.

## Deployment

1. Under **Settings -> Secrets and variables -> Actions**, add `TELEGRAM_TOKEN` and `CHAT_ID` as repository secrets.
2. Trigger a manual run from the **Actions** tab (**News Aggregator Engine** -> **Run workflow**), or wait for the 6-hour schedule.

Nothing needs to run locally. To test a change before pushing, run `TELEGRAM_TOKEN=... CHAT_ID=... uv run main.py` (and discard the resulting `sent_stories.json` edit if you don't want it committed).

## Architecture

The system is a scheduled, episodic batch job rather than an always-on service. A GitHub Actions workflow fires every 6 hours (or on manual trigger) and runs `main.py` on a fresh runner. The script pulls each configured feed - Radio Liberty's native RSS endpoints directly, and social media pages indirectly through an external RSS bridge, since scraping Facebook itself would require fragile headless browsers prone to UI breakage and IP bans. Fetched XML is parsed with the standard library's `ElementTree`, and each item's link is diff-checked against `sent_stories.json`; anything unseen is pushed to the private Telegram chat via the Bot API's `/sendMessage`.

Because Actions runners are ephemeral and stateless, the workflow commits the updated `sent_stories.json` back to the repository after each run - Git itself serves as the version-controlled database. The script uses no third-party Python packages, only the standard library, so there are no dependencies to update or rot over time. Configuration is isolated from logic: adding or removing a feed is a one-line change to the `SOURCES` dict.
