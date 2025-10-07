# 🤖 Telegram Notification Setup Guide

## Step 1: Create a Telegram Bot

1. Open Telegram and search for `@BotFather`
2. Send `/newbot` command
3. Follow the prompts to:
   - Choose a name for your bot (e.g., "Binance Campaign Monitor")
   - Choose a username (must end in 'bot', e.g., "binance_campaign_monitor_bot")
4. You'll receive a token that looks like: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`
5. **Save this token** - you'll need it for `TELEGRAM_BOT_TOKEN`

## Step 2: Get Your Chat ID

### Option A: Personal Chat (Direct Messages)
1. Open Telegram and search for `@userinfobot`
2. Send any message to it
3. It will reply with your chat ID (a number like `123456789`)
4. **Save this ID** - you'll need it for `TELEGRAM_CHAT_ID`

### Option B: Channel or Group
1. Add your bot to the channel/group as an admin
2. Send a test message in the channel/group
3. Visit this URL in your browser (replace YOUR_BOT_TOKEN):
   ```
   https://api.telegram.org/botYOUR_BOT_TOKEN/getUpdates
   ```
4. Look for `"chat":{"id":` in the response - that's your chat ID
5. For channels/groups, the ID usually starts with a minus sign (e.g., `-1001234567890`)

## Step 3: Configure Environment Variables

### Option A: Using .env file (Recommended)
1. Copy the example file:
   ```bash
   cp .env.example .env
   ```
2. Edit `.env` and replace the placeholders:
   ```
   TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
   TELEGRAM_CHAT_ID=123456789
   ```
3. Install python-dotenv if not already installed:
   ```bash
   pip install python-dotenv
   ```
4. Update the script to load .env file (add at the top):
   ```python
   from dotenv import load_dotenv
   load_dotenv()
   ```

### Option B: Using Shell Environment Variables
```bash
export TELEGRAM_BOT_TOKEN="123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
export TELEGRAM_CHAT_ID="123456789"
```

Or add to your `~/.zshrc` file for persistence.

## Step 4: Test the Bot

1. Start a chat with your bot (search for its username in Telegram)
2. Send `/start` command
3. Run the monitor script:
   ```bash
   python3 monitor_binance_th.py
   ```
4. If a campaign is found, you should receive a notification!

## Troubleshooting

### Bot not sending messages?
- Check if the bot token is correct
- Make sure you've started a conversation with the bot (send `/start`)
- For groups/channels, ensure the bot is added as an admin

### "Chat not found" error?
- Verify your chat ID is correct
- Make sure you've sent at least one message to the bot first

### Test manually:
```bash
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/sendMessage" \
  -H "Content-Type: application/json" \
  -d '{"chat_id": "<YOUR_CHAT_ID>", "text": "Test message"}'
```

## Optional: LINE Notify Setup

1. Visit https://notify-bot.line.me/
2. Login with your LINE account
3. Click "Generate token"
4. Select a chat room to receive notifications
5. Copy the token and add to your `.env`:
   ```
   LINE_NOTIFY_TOKEN=your_line_notify_token_here
   ```
