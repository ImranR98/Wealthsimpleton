import os
import json
import logging
import sys
from dotenv import load_dotenv
from datetime import datetime
import argparse
import random
import time

from selenium import webdriver
from selenium_stealth import stealth

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException

# Convert a date/time string from 'January 30' or 'January 30, 2024' format to a date
def convert_datetime(input_string):
    current_year = datetime.now().year
    if ',' in input_string:
        date_format = '%B %d, %Y'
    else:
        date_format = '%B %d'
        input_string += f", {current_year}"  # Add the current year
    return datetime.strptime(input_string, date_format)

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
    WebDriverWait(driver, 300).until(EC.presence_of_element_located((By.XPATH, "//button/div/div/div[2]/p[1]")))
    time.sleep(2) # If you need to scroll down to 'Load More', increase this timeout to have enough time to scroll manually (scrolling is not automated)
    tickers = driver.find_elements(By.XPATH, "//button/div/div/div[2]/p[1]")
    log.info("Found %d transactions, scraping...", len(tickers))
    transactions = []
    for x in range(len(tickers)):
        ticker = driver.find_elements(By.XPATH, "//button/div/div/div[2]/p[1]")[x]
        transactionType = ticker.find_element(By.XPATH, "../div/p[1]")
        try:
            amount = ticker.find_element(By.XPATH, "../../../div[2]/div[1]/p[1]")
        except:
            log.debug("  skip %d: %s (no amount)", x, ticker.text)
            continue
        amount.click()
        time.sleep(1)
        details_div = amount.find_element(By.XPATH, "../../../../../../div[2]")
        date_field = None
        for field in ['Date', 'Filled', 'Submitted', 'Paid', 'Next order date', 'Holdings on record date']:
            try:
                date = convert_datetime(details_div.find_element(By.XPATH, f"//p[text() = '{field}']/../../div[2]/div/p").text).isoformat()
                date_field = field
                break
            except:
                continue
        log.debug("  %d/%d: %s | %s | %s | %s (%s)", x + 1, len(tickers), ticker.text, transactionType.text, amount.text, date, date_field)

        if after_str is not None:
            after_date = datetime.strptime(after_str, '%Y-%m-%d %H:%M')
            curr_date = datetime.fromisoformat(date)
            if after_date > curr_date:
                log.info("Cutoff date %s reached, stopping", after_str)
                break

        transactions.append({
            "description": ticker.text,
            "type": transactionType.text,
            "amount": amount.text,
            "date": date
        })
        amount.click()

    log.info("Scraped %d transactions", len(transactions))
    report = json.dumps(transactions, indent=4)
    print(report)
    if output_path:
        log.info("Writing %s", output_path)
        with open(output_path, 'w') as f:
            f.write(report)