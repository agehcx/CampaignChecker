import os, asyncio, re, time, json
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import httpx

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


def has_thai_comingsoon(html: str) -> bool:
    if SEARCH_TEXT in html:
        return True
    if re.search(r"<button[^>]*>\s*เร็วๆ\s*นี้\s*</button>", html):
            return True
    return False

def parse_campaigns(html: str):
    """Parse HTML and extract campaign details with countdown information"""
    soup = BeautifulSoup(html, 'html.parser')
    
    # Find all campaign cards
    campaigns = soup.find_all('div', class_='css-13h3uyu')
    
    campaign_list = []
    for campaign in campaigns:
        # Extract campaign title
        title_elem = campaign.find('div', class_='css-enjgea')
        title = title_elem.text.strip() if title_elem else "Unknown Campaign"
        
        # Extract campaign description
        desc_elem = campaign.find('div', class_='css-nudebg')
        description = desc_elem.text.strip() if desc_elem else ""
        
        # Extract countdown label (e.g., "เริ่มใน" or "สิ้นสุดใน")
        countdown_label_elem = campaign.find('div', class_='css-1pnvk1z')
        countdown_label = countdown_label_elem.text.strip() if countdown_label_elem else ""
        
        # Extract countdown timer values
        countdown_container = campaign.find('div', class_='css-17u9nn0')
        countdown_value = ""
        if countdown_container:
            time_parts = []
            # Get all time elements
            time_elements = countdown_container.find_all('div', class_=lambda x: x and ('css-vurnku' in x or 'css-1jb05j4' in x))
            for elem in time_elements:
                time_parts.append(elem.text.strip())
            countdown_value = " ".join(time_parts) if time_parts else "Unknown"
        
        # Extract button status (e.g., "เร็วๆ นี้", "เข้าร่วม", etc.)
        button = campaign.find('button', class_='css-10c8e6k')
        status = button.text.strip() if button else "Unknown"
        
        # Only add campaigns with "เร็วๆ นี้" status
        if status == SEARCH_TEXT or SEARCH_TEXT in status:
            campaign_list.append({
                'title': title,
                'description': description[:200] + "..." if len(description) > 200 else description,  # Truncate long descriptions
                'countdown_label': countdown_label,
                'countdown': countdown_value,
                'status': status
            })
    
    return campaign_list

async def fetch_html_with_playwright():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context(user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
        page = await context.new_page()
        await page.route("**/*", lambda route: route.continue_())
        await page.goto(URL, wait_until="networkidle", timeout=90000)
        await asyncio.sleep(2)
        try:
            await page.wait_for_selector(f'button:has-text("{SEARCH_TEXT}")', timeout=3000)
        except:
            pass
        html = await page.content()
        await context.close()
        await browser.close()
        return html

async def notify_telegram(text: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️  Telegram credentials not set. Skipping Telegram notification.")
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "disable_web_page_preview": True}
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=20)
            if response.status_code == 200:
                print("✅ Telegram notification sent successfully!")
                return True
            else:
                print(f"❌ Telegram notification failed: {response.status_code} - {response.text}")
                return False
    except Exception as e:
        print(f"❌ Telegram notification error: {e}")
        return False

async def main():
    try:
        html = await fetch_html_with_playwright()
        found = has_thai_comingsoon(html)
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        status = "FOUND" if found else "NOT_FOUND"
        
        if found:
            # Parse campaign details
            campaigns = parse_campaigns(html)
            
            # Build detailed message
            msg = f"🚨 **Binance TH Campaign Monitor**\n\n"
            msg += f"✅ Status: {status}\n"
            msg += f"⏰ Time: {ts}\n"
            msg += f"📊 Found {len(campaigns)} campaign(s)\n\n"
            
            for idx, camp in enumerate(campaigns, 1):
                msg += f"━━━━━━━━━━━━━━━━━━━\n"
                msg += f"🎯 **Campaign {idx}**\n\n"
                msg += f"� **{camp['title']}**\n\n"
                
                if camp['countdown_label'] and camp['countdown']:
                    msg += f"⏳ {camp['countdown_label']}: {camp['countdown']}\n\n"
                
                msg += f"💬 {camp['description']}\n\n"
                msg += f"🔘 Status: {camp['status']}\n"
            
            msg += f"\n━━━━━━━━━━━━━━━━━━━\n"
            msg += f"🔗 {URL}"
            
            print(f"\n🎯 CAMPAIGN FOUND! Sending notifications...\n")
            print(f"📋 Campaign Details:")
            for idx, camp in enumerate(campaigns, 1):
                print(f"\n  {idx}. {camp['title']}")
                if camp['countdown_label'] and camp['countdown']:
                    print(f"     ⏳ {camp['countdown_label']}: {camp['countdown']}")
                print(f"     🔘 {camp['status']}")
            print()
            
            await notify_telegram(msg)
            
        else:
            print(f"ℹ️  No campaign found with '{SEARCH_TEXT}'")
            msg = f"ℹ️ [Binance TH Monitor]\n\nNo campaigns with '{SEARCH_TEXT}' found.\nTime: {ts}"
            
        print(json.dumps({"status": status, "timestamp": ts, "length": len(html)}))
    except Exception as e:
        error_msg = f"❌ [Binance TH Monitor ERROR]\n\nError: {str(e)}\nTime: {time.strftime('%Y-%m-%d %H:%M:%S')}"
        print(json.dumps({"status": "ERROR", "error": str(e)}))
        # Try to send error notification too
        await notify_telegram(error_msg)
        raise

if __name__ == "__main__":
    asyncio.run(main())