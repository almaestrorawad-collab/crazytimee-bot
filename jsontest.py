import asyncio
import time
import requests
from playwright.async_api import async_playwright
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

async def fetch_and_send():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("https://casinoscores.com/crazy-time/", timeout=60000)
        await page.wait_for_timeout(5000)

        items = await page.query_selector_all("div#CustomToolTip")
        results = []
        for el in items:
            text = await el.inner_text()
            parts = [line.strip() for line in text.split("\n") if line.strip()]
            if len(parts) >= 3:
                results.append(parts[-1])  # last line = "X spins since"

        await browser.close()

        msg = "=== Spins Since Last Hit ===\n" + "\n".join(results)
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg}, timeout=10)

async def loop():
    while True:
        try:
            print("⏳ Running bot at", time.ctime())
            await fetch_and_send()
        except Exception as e:
            print("❌ Error:", e)

        # wait 2 minutes (120 seconds)
        await asyncio.sleep(120)

if __name__ == "__main__":
    asyncio.run(loop())
