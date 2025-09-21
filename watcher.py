import os, asyncio, random, re
from datetime import datetime
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from notify import push_alert
from playwright.async_api import async_playwright, TimeoutError as PwTimeout

load_dotenv()

START_URL  = os.getenv("START_URL", "").strip()
SCHEDULE_URL = os.getenv("SCHEDULE_URL", "").strip()
AVAIL_SELECTOR = os.getenv("AVAIL_SELECTOR", ".next-available-date").strip()
CONS_KEYS = [k.strip() for k in os.getenv("CONSULATE_KEYS", "").split(",") if k.strip()]

CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL_SECONDS", "0") or "0")
JITTER = int(os.getenv("RANDOM_SLEEP_JITTER", "0") or "0")

EARLIEST_TARGET_DATE = os.getenv("EARLIEST_TARGET_DATE", "").strip()
TARGET_DATE = None
if EARLIEST_TARGET_DATE:
    try:
        TARGET_DATE = datetime.strptime(EARLIEST_TARGET_DATE, "%Y-%m-%d").date()
    except ValueError:
        TARGET_DATE = None

STORAGE_STATE = "storage_state.json"

DATE_RX = re.compile(r"(20\d{2}-\d{2}-\d{2})|(\d{1,2}/\d{1,2}/20\d{2})")  # ISO or M/D/YYYY

def parse_date(text: str):
    m = DATE_RX.search(text)
    if not m: return None
    s = m.group(0)
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None

async def check_once():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await p.chromium.launch_persistent_context(
            user_data_dir=".playwright_profile",
            headless=True,
        ) if not os.path.exists(STORAGE_STATE) else await p.chromium.launch(headless=True)

        # Prefer loading saved storage_state if present
        if os.path.exists(STORAGE_STATE):
            context = await p.chromium.new_context(storage_state=STORAGE_STATE, headless=True)

        page = await context.new_page()

        try:
            await page.goto(SCHEDULE_URL or START_URL, wait_until="load", timeout=45000)
        except PwTimeout:
            await context.close()
            return {"ok": False, "error": "Timeout opening page"}

        # If you must click tabs or select consulate from a dropdown, do it here.
        # Example (pseudo):
        # await page.click("text=Reschedule Appointment")
        # await page.select_option("#location", value="Mumbai")

        html = await page.content()
        soup = BeautifulSoup(html, "html.parser")
        candidates = soup.select(AVAIL_SELECTOR)
        texts = [c.get_text(strip=True) for c in candidates if c.get_text(strip=True)]

        await context.close()

        found = []
        for t in texts:
            d = parse_date(t)
            if d:
                found.append((t, d))

        return {"ok": True, "raw": texts, "dates": found}

async def main_loop():
    while True:
        res = await check_once()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if not res.get("ok"):
            print(f"[{now}] ERROR: {res.get('error')}")
        else:
            dates = res.get("dates", [])
            if dates:
                # Pick the earliest date spotted
                earliest = sorted(d for _, d in dates)[0]
                should_alert = True
                if TARGET_DATE:
                    should_alert = earliest <= TARGET_DATE
                if should_alert:
                    body = "Found possible availability lines:\n\n" + "\n".join([f"- {t} → {d}" for t,d in dates])
                    if push_alert("J-1 Visa Appointment Availability Found", body):
                        print(f"[{now}] ALERT sent. Earliest: {earliest}")
                    else:
                        print(f"[{now}] ALERT FAILED to send. Earliest: {earliest}")
                else:
                    print(f"[{now}] Dates found, but later than target: {earliest}")
            else:
                print(f"[{now}] No dates parsed. Raw lines: {res.get('raw')[:3]}")
        if CHECK_INTERVAL <= 0:
            break
        sleep_s = CHECK_INTERVAL + random.randint(0, JITTER)
        await asyncio.sleep(sleep_s)

if __name__ == "__main__":
    if CHECK_INTERVAL > 0:
        asyncio.run(main_loop())
    else:
        asyncio.run(check_once())
