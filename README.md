# cal_pool_bot

Telegram bot for UC Berkeley RecWell pool opening hours. The bot is called
`cal_pool_bot` and its source code is available on [GitHub](https://github.com/fidoriel/cal-pool-bot).

1. Create a Telegram bot with `@BotFather` and copy its token.
2. Install `uv` and the dependencies:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync
```

3. Copy `.env.example` to `.env` and insert the token from `@BotFather`.
4. Start the bot:

```bash
uv run cal-pool-bot
```

Send `/start` to `@cal_pool_bot` in Telegram. It provides buttons for `Open
now`, `Today`, `Tomorrow`, and `This week`, plus a link to this repository.
Opening-time ranges include their total duration as `HH:MM`; closed or
unavailable pools are omitted.

## Docker

Build and run the bot with:

```bash
docker build -t cal_pool_bot .
docker run --env-file .env cal_pool_bot
```

The image includes a Docker health check that verifies the `cal_pool_bot`
process is running.
