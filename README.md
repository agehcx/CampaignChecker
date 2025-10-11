# 🚨 Binance TH Campaign Monitor

> Automated monitoring tool that tracks upcoming campaigns on Binance Thailand and sends real-time notifications to Telegram when new campaigns are about to start.

Never miss out on Binance Thailand campaigns again! This bot automatically checks for new campaigns with "เร็วๆ นี้" (Coming Soon) status and alerts you instantly via Telegram.

---

## ✨ Features

- 🔍 **Automatic Campaign Detection** - Monitors Binance TH campaign page for upcoming campaigns
- ⚡ **Real-time Notifications** - Instant Telegram alerts when new campaigns are found
- 📊 **Detailed Information** - Extracts campaign title, description, and countdown timer
- 🤖 **Headless Browser** - Uses Playwright for reliable scraping of dynamic content
- ⏰ **GitHub Actions Support** - Can run automatically on a schedule (optional)
- 🔔 **Smart Reminders** - Automatic reminders at 1 hour, 15 minutes, 5 minutes, and 1 minute before start

---

## 📋 Prerequisites

- Python 3.7+
- Telegram Bot (for notifications)
- Playwright browsers installed

---

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/agehcx/CampaignChecker.git
cd CampaignChecker
```

### 2. Install Dependencies

```bash
pip3 install -r requirements.txt
```

### 3. Install Playwright Browsers

```bash
playwright install chromium
```

### 4. Configure Telegram Bot

Create a `.env` file in the project root:

```bash
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

**How to get these credentials:**
- See [SETUP_TELEGRAM.md](SETUP_TELEGRAM.md) for detailed instructions
- Bot Token: Create a bot with [@BotFather](https://t.me/botfather)
- Chat ID: Get your ID from [@userinfobot](https://t.me/userinfobot)

### 5. Run the Monitor

```bash
python3 monitor_binance_th.py
```

---

## 📱 Notification Example

When a campaign is found, you'll receive a Telegram message like:

```
🚨 Binance TH Campaign Monitor

✅ Status: FOUND
⏰ Time: 2025-10-07 18:08:16
📊 Found 1 campaign(s)

━━━━━━━━━━━━━━━━━━━
🎯 Campaign 1

📌 WLFI Learn to Earn

⏳ เริ่มใน: 0D 17H 55M 26S

💬 ทำความเข้าใจกับ WLFI ได้ง่ายๆ แล้วร่วมกิจกรรมง่าย ๆ 
ลุ้นรับรางวัลเมื่อทำครบตามเงื่อนไข...

🔘 Status: เร็วๆ นี้

━━━━━━━━━━━━━━━━━━━
🔗 https://www.binance.th/th/campaign/list
```

---

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `TELEGRAM_BOT_TOKEN` | Your Telegram bot token from BotFather | Yes |
| `TELEGRAM_CHAT_ID` | Your Telegram chat/channel ID | Yes |
| `CAMPAIGN_STATE_PATH` | Path to store campaign state JSON (optional) | No |

The state file keeps track of which campaigns have already triggered the initial alert and each reminder threshold (1h/15m/5m/1m). When running locally you can keep it for persistent reminders. When running on GitHub Actions the workspace is ephemeral, so reminders still work because the monitor evaluates the countdown on every run, but the state file is recreated each time.

### Customization

Edit `monitor_binance_th.py` to customize:

```python
# Change the search keyword (default: "เร็วๆ นี้")
SEARCH_TEXT = "เร็วๆ นี้"

# Change the target URL
URL = "https://www.binance.th/th/campaign/list"

# Adjust reminder schedule (label, time delta)
REMINDER_THRESHOLDS = (
   ("1m", timedelta(minutes=1)),
   ("5m", timedelta(minutes=5)),
   ("15m", timedelta(minutes=15)),
   ("1h", timedelta(hours=1)),
)
```

---

## 🤖 Automated Monitoring (GitHub Actions)

Want to run this automatically at 11pm, 3am, 7am, 11am, 3pm, and 7pm (UTC)? The repository includes a GitHub Actions workflow:

### Setup:

1. **Fork this repository**

2. **Add Repository Secrets:**
   - Go to: `Settings` → `Secrets and variables` → `Actions`
   - Add these secrets:
     - `TELEGRAM_BOT_TOKEN`
     - `TELEGRAM_CHAT_ID`

3. **Enable GitHub Actions:**
   - Go to `Actions` tab
   - Enable workflows

The monitor will now run automatically at the scheduled six times each day and notify you when campaigns are found!

---

## 📁 Project Structure

```
CampaignChecker/
├── monitor_binance_th.py    # Main monitoring script
├── requirements.txt          # Python dependencies
├── .env                      # Environment variables (create this)
├── .gitignore               # Git ignore rules
├── README.md                # This file
├── SETUP_TELEGRAM.md        # Telegram setup guide
└── .github/
    └── workflows/
        └── monitor.yml      # GitHub Actions workflow
```

---

## 🛠️ Troubleshooting

### "Executable doesn't exist" Error

If you see this error:
```
BrowserType.launch: Executable doesn't exist at /path/to/chromium
```

**Solution:** Install Playwright browsers:
```bash
playwright install chromium
```

### No Notifications Received

1. Check if `.env` file exists with correct credentials
2. Verify bot token is valid: Message [@BotFather](https://t.me/botfather)
3. Ensure you've started a chat with your bot
4. Check console output for error messages

### Campaign Not Detected

- The script looks for the Thai text "เร็วๆ นี้" (Coming Soon)
- Binance TH may have changed their HTML structure
- Check the console output for the HTML length to verify it's loading

---

## 🔧 Development

### Running in Debug Mode

View full HTML content:
```python
# In monitor_binance_th.py, add this after fetching HTML:
print(html[:1000])  # Print first 1000 characters
```

### Testing Without Notifications

Comment out the notification calls:
```python
# await notify_telegram(msg)
```

---

## 📝 How It Works

1. **Fetch Page** - Uses Playwright to load the Binance TH campaign page with a real browser
2. **Wait for Content** - Waits for dynamic content to load completely
3. **Parse HTML** - Extracts campaign details using BeautifulSoup
4. **Check Status** - Looks for campaigns with "เร็วๆ นี้" (Coming Soon) status
5. **Send Alerts** - Sends formatted notifications to Telegram with all campaign details

---

## 🤝 Contributing

Contributions are welcome! Feel free to:
- Report bugs
- Suggest new features
- Submit pull requests

---

## 📜 License

This project is open source and available under the MIT License.

---

## ⚠️ Disclaimer

This tool is for personal use only. Please respect Binance's terms of service and rate limits. The author is not responsible for any misuse of this tool.

---

## 💡 Tips

- Run the script manually first to test before setting up automation
- Use a dedicated Telegram channel for campaign notifications
- Consider running this on a VPS for 24/7 monitoring
- Check the script periodically as Binance may update their website structure

---

## 📞 Support

If you encounter any issues or have questions:
- Open an issue on GitHub
- Check [SETUP_TELEGRAM.md](SETUP_TELEGRAM.md) for Telegram setup help

---

**Built with ❤️ for the Binance TH community**

*Never miss a campaign again!* 🚀
