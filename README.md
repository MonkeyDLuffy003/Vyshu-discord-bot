# Vyshu Discord Bot (V4 MVP)

## What's new vs the old translation-only bot
- **`/vyshu-mode`** (admin only) — set per-server mode: `translate`, `personal`, or `off`
- **`/vyshu-status`** — check the current mode for the server you're in
- **`/vyshuai`** — anyone can chat directly with Vyshu AI in-channel
- **`/setpfp` / `/setname` / `/setstatus`** — change the bot's picture, nickname, and status (admin only)
- **Personal mode** — in servers set to `personal`, Vyshu silently reads *only Teja's own messages*
  (everyone else is ignored, nothing is posted publicly). Every few hours it DMs Teja a short,
  warm read on tone/patterns in his own messages — never a diagnosis, just a nudge to check in
  with himself if things read heavier than usual.

## Setup
1. Copy `.env.example` to `.env` and fill in:
   - `DISCORD_TOKEN` — from the Discord Developer Portal
   - `ADMIN_ID` — your Discord user ID (enable Developer Mode → right-click your name → Copy ID)
   - `GROQ_API_KEY` — from console.groq.com
2. `pip install -r requirements.txt`
3. `python main.py`

## Important: needs to run 24/7
GitHub Actions runs on triggers/schedules, not a persistent process — it can't host a live bot.
Deploy this on a host that stays online, like **Railway**, **Render**, or a small VPS. All of them
can deploy straight from your GitHub repo, so your push-and-deploy workflow still works.

## Bot permissions needed
When inviting the bot to a server, enable:
- `applications.commands` scope (for slash commands)
- **Message Content Intent** (in the Developer Portal, under Bot settings)
- Send Messages, Read Message History, Embed Links

## Notes
- `personal` mode only ever stores messages from `ADMIN_ID`. No one else's messages are read or saved.
- The mood-analysis prompt is written to avoid diagnostic language on purpose — it flags patterns,
  it doesn't label conditions.
