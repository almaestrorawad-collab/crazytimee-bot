import asyncio
import time
import requests
from playwright.async_api import async_playwright
import os

# === Telegram Config ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# === Alert Threshold (spins) ===
ALERT_THRESHOLD = 200   # spins threshold for alert

# Track the highest multiplier globally
highest_multiplier = 0
highest_game = None
highest_time = None

# Map tooltip IDs to game names
GAME_MAP = {
    "tooltip-CrazyBonus": "Crazy Time",
    "tooltip-CashHunt": "Cash Hunt",
    "tooltip-Pachinko": "Pachinko",
    "tooltip-CoinFlip": "Coin Flip",
}


async def fetch_and_send():
    global highest_multiplier, highest_game, highest_time

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("https://casinoscores.com/crazy-time/", timeout=60000)
        await page.wait_for_timeout(5000)

        # --- PART 1: Spins since last hit (tooltip section) ---
        results = {}
        tooltips = await page.query_selector_all("div#CustomToolTip")
        for el in tooltips:
            parent = await el.evaluate_handle("e => e.closest('g')")
            gid = await parent.get_attribute("id")
            text = await el.inner_text()
            parts = [line.strip() for line in text.split("\n") if line.strip()]
            if gid in GAME_MAP and len(parts) >= 3:
                spins_line = parts[-1]  # "X spins since"
                results[GAME_MAP[gid]] = spins_line

        # --- PART 2: History table multipliers ---
        rows = await page.query_selector_all("tr[data-slot='table-row']")

        for row in rows[:10]:  # last 10 spins
            # time
            date_elems = await row.query_selector_all("p.dateTime_DateTime__date__bXWTP")
            time_elem = await row.query_selector("p.dateTime_DateTime__time__f0_Bn")
            date_parts = [await d.inner_text() for d in date_elems]
            time_text = await time_elem.inner_text() if time_elem else ""
            full_time = " ".join(date_parts + [time_text])

            # game
            game_img = await row.query_selector("td img[alt='Spin Result']")
            game_src = await game_img.get_attribute("src") if game_img else ""
            if "pachiko" in game_src:
                game = "Pachinko"
            elif "crazy-time" in game_src:
                game = "Crazy Time"
            elif "cash-hunt" in game_src:
                game = "Cash Hunt"
            elif "coin-flip" in game_src:
                game = "Coin Flip"
            else:
                game = None  # ignore numbers

            # multiplier(s)
            multiplier_val = 0
            mult_elems = await row.query_selector_all("span[data-slot='badge']")
            mult_texts = [await el.inner_text() for el in mult_elems]

            if game == "Crazy Time":
                # take maximum of all multipliers
                vals = []
                for text in mult_texts:
                    if "x" in text.lower():
                        try:
                            vals.append(int(text.lower().replace("x", "").strip()))
                        except:
                            pass
                multiplier_val = max(vals) if vals else 0

            elif game == "Cash Hunt":
                # average if it's a range like "5X -- 100X"
                for text in mult_texts:
                    if "--" in text:
                        try:
                            parts = text.lower().replace("x", "").split("--")
                            low, high = int(parts[0].strip()), int(parts[1].strip())
                            multiplier_val = (low + high) / 2
                        except:
                            pass
                    elif "x" in text.lower():
                        try:
                            multiplier_val = int(text.lower().replace("x", "").strip())
                        except:
                            pass

            else:
                # single value for Pachinko / Coin Flip
                for text in mult_texts:
                    if "x" in text.lower():
                        try:
                            multiplier_val = int(text.lower().replace("x", "").strip())
                            break
                        except:
                            pass

            # Check if it's a new record
            if game and multiplier_val > highest_multiplier:
                highest_multiplier = multiplier_val
                highest_game = game
                highest_time = full_time

        await browser.close()

        # --- Build Telegram message ---
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

        # Always include the record (even if no new one found)
        if highest_multiplier > 0:
            alerts.append(
                f"🏆 HIGHEST MULTIPLIER so far: {highest_game} x{highest_multiplier} at {highest_time}"
            )

        msg = "\n".join(lines)
        if alerts:
            msg += "\n\n" + "\n".join(alerts)

        print(msg)

        # Send to Telegram
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        try:
            r = requests.post(url, data={"chat_id": CHAT_ID, "text": msg}, timeout=10)
            print("Telegram response:", r.status_code)
        except Exception as e:
            print("❌ Telegram error:", e)


async def main_loop():
    while True:
        print("⏳ Running bot at", time.ctime())
        try:
            await fetch_and_send()
        except Exception as e:
            print("❌ Error in fetch_and_send:", e)
        print("💤 Sleeping for 15 minutes...")
        await asyncio.sleep(10)  # 900 seconds = 15 minutes


if __name__ == "__main__":
    asyncio.run(main_loop())
