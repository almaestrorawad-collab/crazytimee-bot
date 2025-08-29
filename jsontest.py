import asyncio
import requests
from playwright.async_api import async_playwright
import os

# === Settings ===
URL = "https://casinoscores.com/crazy-time/"
BONUSES = ["Crazy Time", "Cash Hunt", "Pachinko", "Coin Flip"]
ALERT_THRESHOLD = 300  # spins

# === Telegram Config (from GitHub Secrets) ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def send_telegram_message(text: str):
    """Send a message to Telegram chat."""
    if not BOT_TOKEN or not CHAT_ID:
        print("❌ BOT_TOKEN or CHAT_ID not set!")
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": text}, timeout=10)
    except Exception as e:
        print("Telegram send error:", e)

async def fetch_last_hits():
    """Scrape CasinoScores counters for all bonuses once."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(URL, timeout=60000)

        await page.wait_for_timeout(5000)  # wait for JS chart to render

        items = await page.query_selector_all("div#CustomToolTip")
        results = {}

        for el in items:
            text = await el.inner_text()
            parts = [line.strip() for line in text.split("\n") if line.strip()]
            if len(parts) >= 3:
                _, lands, spins_line = parts
                parent = await el.evaluate_handle("e => e.closest('g')")
                gid = await parent.get_attribute("id")
                if gid:
                    if "Crazy" in gid: name = "Crazy Time"
                    elif "Cash" in gid: name = "Cash Hunt"
                    elif "Pachinko" in gid: name = "Pachinko"
                    elif "CoinFlip" in gid: name = "Coin Flip"
                    else: continue
                    results[name] = spins_line

        await browser.close()
        return results

async def main():
    results = await fetch_last_hits()

    # Build summary message
    summary = ["=== Spins Since Last Hit ==="]
    for game in BONUSES:
        spins_text = results.get(game, "Unknown")
        summary.append(f"{game}: {spins_text}")

        # Alert if threshold passed
        if "spins since" in spins_text:
            spins = int(spins_text.split()[0])
            if spins >= ALERT_THRESHOLD:
                summary.append(f"⚠️ {game} has not appeared for {spins} spins!")

    message = "\n".join(summary)

    # Print locally + send to Telegram
    print(message)
    send_telegram_message(message)

if __name__ == "__main__":
    asyncio.run(main())

# push commit 2