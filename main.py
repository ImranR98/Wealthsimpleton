import os
import json
import logging
import sys
import re
from dotenv import load_dotenv
from datetime import datetime, timedelta
import argparse
import random
import time

from selenium import webdriver
from selenium_stealth import stealth

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException

# Convert a date string from the activity page ('Today', 'Yesterday',
# 'January 30, 2024', or 'August 30, 2026 4:00 pm') to a datetime.
def convert_datetime(input_string):
    text = re.sub(r'\s+', ' ', input_string).strip()
    today = datetime.now()
    if text.lower() == 'today':
        return today.replace(hour=0, minute=0, second=0, microsecond=0)
    if text.lower() == 'yesterday':
        return (today - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    for fmt in ('%B %d, %Y %I:%M %p', '%B %d, %Y'):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ValueError(f"unparseable date: {input_string!r}")

# Click an element after centering it in the viewport: the activity page has a
# sticky header that would otherwise intercept clicks on rows scrolled to the top.
def click_visible(driver, element):
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'}); arguments[0].click();", element)

# Main function
if __name__ == "__main__":
    # Validate arguments
    output_path=""
    after_str=None
    parser = argparse.ArgumentParser()
    parser.add_argument('--file', help='Where to save the output (can be an existing file for incremental scraping)')
    parser.add_argument('--after', help='A \'Y-m-d H:M\' string to filter out orders older than a certain date/time')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose/debug logging to stderr')
    args = parser.parse_args()
    if args.file:
        output_path = args.file
    if args.after:
        after_str = args.after

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='%(asctime)s %(message)s',
        datefmt='%H:%M:%S',
        stream=sys.stderr,
    )
    log = logging.getLogger('wealthsimpleton')

    log.info("Wealthsimpleton starting")
    load_dotenv()
    options = webdriver.ChromeOptions()
    dataDir = os.path.expanduser("~/.config/wealthsimpleton-selenium")
    os.makedirs(dataDir, exist_ok=True)
    options.add_argument(f"--user-data-dir={dataDir}")
    options.add_argument("--profile-directory=Default")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    os.environ["TMPDIR"] = "/tmp"
    driver = None
    for attempt in range(3):
        try:
            import glob
            for f in glob.glob(os.path.join(dataDir, "Singleton*")):
                os.remove(f)
            driver = webdriver.Chrome(options=options)
            break
        except Exception as e:
            log.warning("Chrome launch failed (attempt %d/3): %s", attempt + 1, e)
            time.sleep(5)
    if driver is None:
        raise RuntimeError("Chrome failed to launch after 3 attempts")
    stealth(driver,
        languages=["en-US", "en"],
        vendor="Google Inc.",
        platform="Win32",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True,
        )

    driver.get("https://my.wealthsimple.com/login")
    log.info("Waiting for login/2FA (timeout: 3600s)...")
    WebDriverWait(driver, 3600).until(EC.url_changes(driver.current_url)) # Long timeout needed for manual login or 2FA
    log.info("Logged in, loading activity page")
    driver.get("https://my.wealthsimple.com/app/activity")
    WebDriverWait(driver, 300).until(EC.presence_of_element_located((By.XPATH, "//main//button[span[1]/span[3]]")))
    time.sleep(2)
    if after_str is not None:
        cutoff = datetime.strptime(after_str, '%Y-%m-%d %H:%M')
    else:
        cutoff = datetime.now() - timedelta(days=45)  # ~1.5 months
    for _ in range(60):
        try:
            load_more = driver.find_element(By.XPATH, "//button[.//span[text()='Load more']]")
        except NoSuchElementException:
            break
        headers = driver.find_elements(By.XPATH, "//main//h3")
        if headers:
            oldest = convert_datetime(headers[-1].text)
            if oldest < cutoff.replace(hour=0, minute=0, second=0, microsecond=0):
                log.info("Reached cutoff %s, stopping 'Load more'", cutoff.date().isoformat())
                break
        click_visible(driver, load_more)
        time.sleep(2)
    tickers = driver.find_elements(By.XPATH, "//main//button[span[1]/span[3]]")
    log.info("Found %d transactions, scraping...", len(tickers))
    transactions = []
    for x in range(len(tickers)):
        ticker = driver.find_elements(By.XPATH, "//main//button[span[1]/span[3]]")[x]
        try:
            description = ticker.find_element(By.XPATH, "./span[1]/span[2]/span[1]").text
            transactionType = ticker.find_element(By.XPATH, "./span[1]/span[2]/span[2]/span[1]/span[1]/span[1]").text
            click_visible(driver, ticker)
            panel = WebDriverWait(driver, 10).until(EC.presence_of_element_located((
                By.XPATH, f"(//main//button[span[1]/span[3]])[{x + 1}]/following-sibling::div[1]")))
            details = {}
            for dt, dd in zip(panel.find_elements(By.TAG_NAME, 'dt'), panel.find_elements(By.TAG_NAME, 'dd')):
                details[dt.text] = dd.text
            click_visible(driver, ticker)  # collapse
            amount = (details.get('Total') or details.get('Amount') or details.get('Total cost')
                      or ticker.find_element(By.XPATH, "./span[1]/span[3]/span[last()]/span[1]/span[1]").text)
            date_str = details.get('Date')
            if not date_str:
                date_str = ticker.find_element(By.XPATH, "ancestor::div[.//h3][1]//h3").text
            date = convert_datetime(date_str).isoformat()
        except Exception as e:
            log.warning("  skip %d: %s (%s: %s)", x, ticker.text, type(e).__name__, e)
            continue
        log.debug("  %d/%d: %s | %s | %s | %s", x + 1, len(tickers), description, transactionType, amount, date)

        if datetime.fromisoformat(date) < cutoff:
            log.info("Cutoff %s reached, stopping", cutoff.date().isoformat())
            break

        transactions.append({
            "description": description,
            "type": transactionType,
            "amount": amount,
            "date": date,
            "details": details,
        })

    log.info("Scraped %d transactions", len(transactions))
    report = json.dumps(transactions, indent=4)
    print(report)
    if output_path:
        log.info("Writing %s", output_path)
        with open(output_path, 'w') as f:
            f.write(report)