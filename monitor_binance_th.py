import asyncio
import hashlib
import json
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

import httpx
from bs4 import BeautifulSoup
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

# Try to load .env file if it exists
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, use system env vars

URL = "https://www.binance.th/th/campaign/list?utm_source=footer&utm_medium=web&utm_campaign=list"
SEARCH_TEXT = "เร็วๆ นี้"

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
CAMPAIGN_STATE_PATH = os.getenv("CAMPAIGN_STATE_PATH", "campaign_state.json")
REMINDER_THRESHOLDS: Tuple[Tuple[str, timedelta], ...] = (
    ("1m", timedelta(minutes=1)),
    ("5m", timedelta(minutes=5)),
    ("15m", timedelta(minutes=15)),
    ("1h", timedelta(hours=1)),
)


def has_thai_comingsoon(html: str) -> bool:
    if SEARCH_TEXT in html:
        return True
    return bool(re.search(r"<button[^>]*>\s*เร็วๆ\s*นี้\s*</button>", html))


def parse_campaigns(html: str, fetched_at: datetime) -> List[Dict[str, Optional[str]]]:
    """Parse HTML and extract campaign details with countdown information."""
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.find_all("div", class_="css-13h3uyu")

    campaigns: List[Dict[str, Optional[str]]] = []
    for card in cards:
        title_elem = card.find("div", class_="css-enjgea")
        title = title_elem.text.strip() if title_elem else "Unknown Campaign"

        desc_elem = card.find("div", class_="css-nudebg")
        description = desc_elem.text.strip() if desc_elem else ""

        countdown_label_elem = card.find("div", class_="css-1pnvk1z")
        countdown_label = countdown_label_elem.text.strip() if countdown_label_elem else ""

        countdown_container = card.find("div", class_="css-17u9nn0")
        countdown_value = ""
        if countdown_container:
            time_parts: List[str] = []
            time_elements = countdown_container.find_all(
                "div", class_=lambda x: x and ("css-vurnku" in x or "css-1jb05j4" in x)
            )
            for element in time_elements:
                value = element.text.strip()
                if value:
                    time_parts.append(value)
            countdown_value = " ".join(time_parts) if time_parts else "Unknown"

        button = card.find("button", class_="css-10c8e6k")
        status = button.text.strip() if button else "Unknown"

        if status == SEARCH_TEXT or SEARCH_TEXT in status:
            countdown_delta = parse_countdown_to_delta(countdown_value)
            start_timestamp_utc = None
            seconds_until_start: Optional[int] = None

            if countdown_label and "เริ่ม" in countdown_label and countdown_delta:
                start_dt = fetched_at + countdown_delta
                start_timestamp_utc = start_dt.astimezone(timezone.utc).isoformat()
                seconds_until_start = int(countdown_delta.total_seconds())

            campaigns.append(
                {
                    "id": generate_campaign_id(title, description),
                    "title": title,
                    "description": (description[:200] + "...") if len(description) > 200 else description,
                    "countdown_label": countdown_label,
                    "countdown": countdown_value,
                    "status": status,
                    "start_timestamp_utc": start_timestamp_utc,
                    "seconds_until_start": seconds_until_start,
                }
            )

    return campaigns


def generate_campaign_id(title: str, description: str) -> str:
    digest = hashlib.sha256(f"{title}|{description}".encode("utf-8")).hexdigest()
    return digest


def parse_countdown_to_delta(text: str) -> Optional[timedelta]:
    if not text:
        return None

    stripped = text.strip()
    if not stripped:
        return None

    units = {
        "วัน": "days",
        "ชั่วโมง": "hours",
        "นาที": "minutes",
        "วินาที": "seconds",
    }

    values: Dict[str, int] = {key: 0 for key in units.values()}

    for thai_unit, delta_key in units.items():
        match = re.search(rf"(\d+)\s*{thai_unit}", stripped)
        if match:
            values[delta_key] = int(match.group(1))

    if any(values.values()):
        return timedelta(**values)

    colon_parts = stripped.split(":")
    if len(colon_parts) in (3, 4) and all(part.isdigit() for part in colon_parts):
        numbers = [int(part) for part in colon_parts]
        if len(numbers) == 3:
            hours, minutes, seconds = numbers
            return timedelta(hours=hours, minutes=minutes, seconds=seconds)
        days, hours, minutes, seconds = numbers
        return timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)

    fallback_numbers = re.findall(r"\d+", stripped)
    if len(fallback_numbers) == 4:
        days, hours, minutes, seconds = map(int, fallback_numbers)
        return timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)

    return None


def load_campaign_state() -> Dict[str, Dict]:
    try:
        with open(CAMPAIGN_STATE_PATH, "r", encoding="utf-8") as state_file:
            return json.load(state_file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_campaign_state(state: Dict[str, Dict]) -> None:
    directory = os.path.dirname(CAMPAIGN_STATE_PATH)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(CAMPAIGN_STATE_PATH, "w", encoding="utf-8") as state_file:
        json.dump(state, state_file, ensure_ascii=False, indent=2)


def prune_campaign_state(state: Dict[str, Dict], now_utc: datetime) -> None:
    stale_cutoff = now_utc - timedelta(days=14)
    to_remove: List[str] = []

    for campaign_id, info in list(state.items()):
        last_seen = info.get("last_seen_at")
        if not last_seen:
            continue
        try:
            last_seen_dt = datetime.fromisoformat(last_seen)
        except ValueError:
            continue
        if last_seen_dt.tzinfo is None:
            last_seen_dt = last_seen_dt.replace(tzinfo=timezone.utc)
        if last_seen_dt < stale_cutoff:
            to_remove.append(campaign_id)

    for campaign_id in to_remove:
        state.pop(campaign_id, None)


def humanize_timedelta(delta: timedelta) -> str:
    total_seconds = max(int(delta.total_seconds()), 0)
    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)

    parts: List[str] = []
    if days:
        parts.append(f"{days}d")
    if days or hours:
        parts.append(f"{hours}h")
    if not parts or minutes:
        parts.append(f"{minutes}m")
    if not days and seconds:
        parts.append(f"{seconds}s")
    return " ".join(parts)


def format_campaign_section(campaign: Dict[str, Optional[str]]) -> str:
    lines = ["━━━━━━━━━━━━━━━━━━━", f"🎯 **{campaign['title']}**"]

    if campaign.get("countdown_label") and campaign.get("countdown"):
        lines.append(f"⏳ {campaign['countdown_label']}: {campaign['countdown']}")

    if campaign.get("start_timestamp_utc"):
        try:
            start_dt = datetime.fromisoformat(campaign["start_timestamp_utc"]).astimezone()
            lines.append(f"🗓️ Start: {start_dt.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        except ValueError:
            pass

    description = campaign.get("description")
    if description:
        lines.append(f"💬 {description}")

    lines.append(f"🔘 Status: {campaign['status']}")
    return "\n".join(lines)


async def process_campaign_notifications(
    campaigns: List[Dict[str, Optional[str]]], fetched_at: datetime
) -> Dict[str, bool]:
    """Send notifications for newly detected campaigns and upcoming reminders."""
    now_utc = fetched_at.astimezone(timezone.utc)
    state = load_campaign_state()

    new_campaigns: List[Dict[str, Optional[str]]] = []
    reminders_to_send: List[Tuple[Dict[str, Optional[str]], timedelta, str]] = []

    for campaign in campaigns:
        campaign_id = campaign["id"]
        state_entry = state.get(
            campaign_id,
            {
                "title": campaign["title"],
                "first_detected_at": now_utc.isoformat(),
                "initial_notified": False,
                "reminders_sent": [],
            },
        )

        state_entry["title"] = campaign["title"]
        state_entry["last_seen_at"] = now_utc.isoformat()
        state_entry["start_timestamp_utc"] = campaign.get("start_timestamp_utc")
        if not isinstance(state_entry.get("reminders_sent"), list):
            state_entry["reminders_sent"] = []
        state[campaign_id] = state_entry

        if not state_entry.get("initial_notified", False):
            new_campaigns.append(campaign)

        start_timestamp_utc = campaign.get("start_timestamp_utc")
        if start_timestamp_utc:
            try:
                start_dt = datetime.fromisoformat(start_timestamp_utc)
            except ValueError:
                start_dt = None
            if start_dt:
                time_left = start_dt - now_utc
                if time_left > timedelta(0):
                    for reminder_key, threshold in sorted(REMINDER_THRESHOLDS, key=lambda item: item[1]):
                        if reminder_key in state_entry["reminders_sent"]:
                            continue
                        if time_left <= threshold:
                            reminders_to_send.append((campaign, time_left, reminder_key))
                            break

    notifications_sent = {"initial": False, "reminder": False}

    if new_campaigns:
        ts_local = fetched_at.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
        header = [
            # "🚨 Binance TH - Campaign Monitor",
            # "",
            "✅ Status: FOUND",
            f"⏰ Time: {ts_local}",
            f"📊 Found {len(new_campaigns)} new campaign(s)",
            "",
        ]
        sections = [format_campaign_section(c) for c in new_campaigns]
        message = "\n".join(header + sections + ["━━━━━━━━━━━━━━━━━━━", f"🔗 {URL}"])

        if await notify_telegram(message):
            notifications_sent["initial"] = True
            for campaign in new_campaigns:
                entry = state.get(campaign["id"], {})
                entry["initial_notified"] = True
                entry["initial_notified_at"] = now_utc.isoformat()
                state[campaign["id"]] = entry
            print("✅ New campaign notification sent to Telegram.")

    for campaign, time_left, reminder_key in reminders_to_send:
        reminder_lines = [
            f"⏰ Campaign Reminder ({reminder_key})",
            "",
            f"🎯 {campaign['title']}",
            f"⏳ Starts in about {humanize_timedelta(time_left)}",
        ]

        if campaign.get("start_timestamp_utc"):
            try:
                start_dt = datetime.fromisoformat(campaign["start_timestamp_utc"]).astimezone()
                reminder_lines.append(f"🗓️ Starts at {start_dt.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            except ValueError:
                pass

        description = campaign.get("description")
        if description:
            reminder_lines.extend(["", description])

        reminder_lines.extend(["", f"🔗 {URL}"])

        if await notify_telegram("\n".join(reminder_lines)):
            notifications_sent["reminder"] = True
            entry = state.get(campaign["id"], {})
            reminders = entry.setdefault("reminders_sent", [])
            reminders.append(reminder_key)
            entry.setdefault("reminder_history", []).append(
                {"type": reminder_key, "sent_at": now_utc.isoformat()}
            )
            state[campaign["id"]] = entry
            print(f"🔔 Sent {reminder_key} reminder for '{campaign['title']}'.")

    prune_campaign_state(state, now_utc)
    save_campaign_state(state)
    return notifications_sent


async def fetch_html_with_playwright() -> str:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            )
        )
        page = await context.new_page()
        await page.route("**/*", lambda route: route.continue_())
        await page.goto(URL, wait_until="networkidle", timeout=90_000)
        await asyncio.sleep(2)
        async with suppress_timeout():
            await page.wait_for_selector(f"button:has-text(\"{SEARCH_TEXT}\")", timeout=3_000)
        html = await page.content()
        await context.close()
        await browser.close()
        return html


class suppress_timeout:
    """Async context manager to ignore Playwright timeout errors."""

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, _):
        return exc_type is not None and issubclass(exc_type, PlaywrightTimeoutError)


async def notify_telegram(text: str) -> bool:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️  Telegram credentials not set. Skipping Telegram notification.")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "disable_web_page_preview": True,
    }

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(url, json=payload)
            if response.status_code == 200:
                print("✅ Telegram notification sent successfully!")
                return True
            print(f"❌ Telegram notification failed: {response.status_code} - {response.text}")
            return False
    except Exception as exc:  # pylint: disable=broad-except
        print(f"❌ Telegram notification error: {exc}")
        return False


async def main() -> None:
    try:
        html = await fetch_html_with_playwright()
        fetched_at = datetime.now(timezone.utc)
        found = has_thai_comingsoon(html)
        status = "FOUND" if found else "NOT_FOUND"
        ts = fetched_at.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")

        if found:
            campaigns = parse_campaigns(html, fetched_at)

            print("\n🎯 CAMPAIGN FOUND!\n")
            for idx, campaign in enumerate(campaigns, 1):
                print(f"  {idx}. {campaign['title']}")
                if campaign.get("countdown_label") and campaign.get("countdown"):
                    print(f"     ⏳ {campaign['countdown_label']}: {campaign['countdown']}")
                if campaign.get("start_timestamp_utc"):
                    try:
                        start_dt = datetime.fromisoformat(campaign["start_timestamp_utc"]).astimezone()
                        print(f"     🗓️ Starts: {start_dt.strftime('%Y-%m-%d %H:%M:%S %Z')}")
                    except ValueError:
                        pass
                print(f"     🔘 {campaign['status']}")

            notifications = await process_campaign_notifications(campaigns, fetched_at)
            if not any(notifications.values()):
                print("\nℹ️ Campaigns already notified. Sending status heartbeat.\n")
                sections = [format_campaign_section(c) for c in campaigns]

                if campaigns:
                    header_line = f"{len(campaigns)} Campaign{'s' if len(campaigns) != 1 else ''} found ✅"
                else:
                    header_line = "No campaigns found ‼️"

                heartbeat_msg = "\n".join(
                    [
                        # "ℹ️ Binance TH - Campaign Monitor",
                        # "",
                        header_line,
                    ]
                    + sections
                    + ["", f"🔗 {URL}"]
                )
                await notify_telegram(heartbeat_msg)
        else:
            print(f"ℹ️  No campaign found with '{SEARCH_TEXT}'")

        print(json.dumps({"status": status, "timestamp": ts, "length": len(html)}))
    except Exception as exc:  # pylint: disable=broad-except
        error_ts = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
        error_msg = f"❌ [Binance TH Monitor ERROR]\n\nError: {exc}\nTime: {error_ts}"
        print(json.dumps({"status": "ERROR", "error": str(exc)}))
        await notify_telegram(error_msg)
        raise


if __name__ == "__main__":
    asyncio.run(main())