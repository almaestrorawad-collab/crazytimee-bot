import asyncio
import time
import requests
from playwright.async_api import async_playwright
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
ALERT_THRESHOLD = 200

GAME_MAP = {
    "tooltip-CrazyBonus": "Crazy Time",
    "tooltip-CashHunt": "Cash Hunt",
    "tooltip-Pachinko": "Pachinko",
    "tooltip-CoinFlip": "Coin Flip",
}

BASE_PROBS = {
    "Crazy Time": 1/54,
    "Pachinko": 2/54,
    "Cash Hunt": 2/54,
    "Coin Flip": 4/54
}

async def fetch_and_send():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("https://casinoscores.com/crazy-time/", timeout=60000)
        await page.wait_for_timeout(5000)

        # spins since last hit
        results = {}
        tooltips = await page.query_selector_all("div#CustomToolTip")
        for el in tooltips:
            parent = await el.evaluate_handle("e => e.closest('g')")
            gid = await parent.get_attribute("id")
            text = await el.inner_text()
            parts = [line.strip() for line in text.split("\n") if line.strip()]
            if gid in GAME_MAP and len(parts) >= 3:
                results[GAME_MAP[gid]] = parts[-1]

        await browser.close()

        # build message
        lines = ["=== Spins Since Last Hit ==="]
        alerts = []

        for game in GAME_MAP.values():
            spins_text = results.get(game, "Unknown")
            lines.append(f"{game}: {spins_text}")
            if "spins since" in spins_text:
                try:
                    spins = int(spins_text.split()[0])
                    if spins >= ALERT_THRESHOLD:
                        alerts.append(f"⚠️ {game} not appeared for {spins} spins!")
                except:
                    pass

        prob_lines = ["=== Next Spin Probabilities (adjusted) ==="]
        for game in GAME_MAP.values():
            spins_text = results.get(game, "Unknown")
            prob = BASE_PROBS.get(game, 0)
            if "spins since" in spins_text:
                try:
                    spins = int(spins_text.split()[0])
                    adj_prob = prob * (1 + spins / 100)
                    prob_lines.append(f"{game}: {adj_prob*100:.2f}% (last seen {spins} spins ago)")
                except:
                    prob_lines.append(f"{game}: {prob*100:.2f}% (last seen Unknown)")
            else:
                prob_lines.append(f"{game}: {prob*100:.2f}% (last seen Unknown)")

        msg = "\n".join(lines)
        if alerts:
            msg += "\n\n" + "\n".join(alerts)
        msg += "\n\n" + "\n".join(prob_lines)

        print(msg)

        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

asyncio.run(fetch_and_send())
