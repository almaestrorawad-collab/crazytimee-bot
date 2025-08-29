import asyncio
import time
import requests
from playwright.async_api import async_playwright
import os
# === Telegram Config ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# === Alert Threshold (spins) ===
ALERT_THRESHOLD = 250   # change this number as you like

GAME_MAP = {
    "tooltip-CrazyBonus": "Crazy Time",
    "tooltip-CashHunt": "Cash Hunt",
    "tooltip-Pachinko": "Pachinko",
    "tooltip-CoinFlip": "Coin Flip",
}

async def fetch_and_send():
    """Scrape site and send message to Telegram."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("https://casinoscores.com/crazy-time/", timeout=60000)
        await page.wait_for_timeout(5000)

        results = {}

        # Find all tooltip divs
        items = await page.query_selector_all("div#CustomToolTip")
        for el in items:
            parent = await el.evaluate_handle("e => e.closest('g')")
            gid = await parent.get_attribute("id")
            text = await el.inner_text()
            parts = [line.strip() for line in text.split("\n") if line.strip()]

            if gid in GAME_MAP and len(parts) >= 3:
                spins_line = parts[-1]  # "X spins since" or "Latest Spin"
                results[GAME_MAP[gid]] = spins_line

        await browser.close()

        # Build message
        lines = ["=== Spins Since Last Hit ==="]
        alerts = []

        for game in GAME_MAP.values():
            spins_text = results.get(game, "Unknown")
            lines.append(f"{game}: {spins_text}")

            # Check alert condition
            if "spins since" in spins_text:
                try:
                    spins = int(spins_text.split()[0])
                    if spins >= ALERT_THRESHOLD:
                        alerts.append(f"⚠️ {game} has not appeared for {spins} spins!")
                except ValueError:
                    pass  # ignore if parsing fails

        # Combine message
        msg = "\n".join(lines)
        if alerts:
            msg += "\n\n" + "\n".join(alerts)

        print(msg)

        # Send to Telegram
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        try:
            r = requests.post(url, data={"chat_id": CHAT_ID, "text": msg}, timeout=10)
            print("Telegram response:", r.status_code, r.text)
        except Exception as e:
            print("❌ Telegram error:", e)

async def main_loop():
    """Run forever: fetch → send → wait 15 min."""
    while True:
        print("⏳ Running bot at", time.ctime())
        try:
            await fetch_and_send()
        except Exception as e:
            print("❌ Error in fetch_and_send:", e)
        print("💤 Sleeping for 1 minute...")
        await asyncio.sleep(60)  # 900 seconds = 15 minutes

if __name__ == "__main__":
    asyncio.run(main_loop())
