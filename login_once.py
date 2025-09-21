import os
import asyncio
from dotenv import load_dotenv
from playwright.async_api import async_playwright

load_dotenv()

START_URL = os.getenv("START_URL", "").strip()
if not START_URL:
    raise SystemExit("Set START_URL in .env")

STORAGE_STATE = "storage_state.json"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # visible so you can solve CAPTCHA/2FA
        context = await browser.new_context()
        page = await context.new_page()
        print(f"[INFO] Opening {START_URL}")
        await page.goto(START_URL, wait_until="load")

        print("[ACTION] Please complete login (CAPTCHA/OTP/etc).")
        print("[ACTION] Navigate to the scheduling dashboard so the session is fully established.")
        input("[ENTER] Press Enter here once you are logged in and can see your dashboard/schedule... ")

        # Save cookies/localStorage so the headless script can reuse your session
        await context.storage_state(path=STORAGE_STATE)
        print(f"[OK] Saved session to {STORAGE_STATE}")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
