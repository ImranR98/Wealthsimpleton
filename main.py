import os
import json
from dotenv import load_dotenv
import tkinter as tk
from datetime import datetime
import argparse
import random
import time
import getpass

from selenium import webdriver
from selenium_stealth import stealth

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC\

# Function to get the screen width and height
def get_screen_dimensions():
    root = tk.Tk()
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    root.destroy()
    return screen_width, screen_height

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
    args = parser.parse_args()
    if args.file:
        output_path = args.file
    if args.after:
        after_str = args.after

    # Setup Webdriver and load env. vars.
    load_dotenv()
    screen_width, screen_height = get_screen_dimensions()
    window_width = screen_width // 2
    window_height = screen_height
    options = webdriver.ChromeOptions()
    options.add_argument(f"window-size={window_width},{window_height}")
    options.add_argument(f"window-position={screen_width},0")
    dataDir = f"/home/{getpass.getuser()}/.config/chromium"
    if not os.path.isdir(dataDir):
        dataDir = f"/home/{getpass.getuser()}/.config/google-chrome"
    if os.path.isdir(dataDir):
        options.add_argument(f"--user-data-dir={dataDir}")
        options.add_argument(f"--profile-directory=Default")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    driver = webdriver.Chrome(options=options)
    stealth(driver,
        languages=["en-US", "en"],
        vendor="Google Inc.",
        platform="Win32",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True,
        )

    driver.get("https://my.wealthsimple.com/login")
    WebDriverWait(driver, 3600).until(EC.url_changes(driver.current_url)) # Long timeout needed for manual login or 2FA
    driver.get("https://my.wealthsimple.com/app/activity")
    WebDriverWait(driver, 300).until(EC.presence_of_element_located((By.XPATH, "//button/div/div/div[2]/p[1]")))
    time.sleep(2) # If you need to scroll down to 'Load More', increase this timeout to have enough time to scroll manually (scrolling is not automated)
    tickers = driver.find_elements(By.XPATH, "//button/div/div/div[2]/p[1]")
    transactions = []
    for x in range(len(tickers)):
        ticker = driver.find_elements(By.XPATH, "//button/div/div/div[2]/p[1]")[x]
        transactionType = ticker.find_element(By.XPATH, "../div/p[1]")
        try:
            amount = ticker.find_element(By.XPATH, "../../../div[2]/p[1]")
        except:
            continue
        amount.click()
        time.sleep(1)
        details_div = amount.find_element(By.XPATH, "../../../../../div")
        try:
            date = convert_datetime(details_div.find_element(By.XPATH, "//p[text() = 'Date']/../../div[2]/div/p").text).isoformat()
        except:
            try:
                date = convert_datetime(details_div.find_element(By.XPATH, "//p[text() = 'Filled']/../div/div/p").text).isoformat()
            except:
                date = convert_datetime(details_div.find_element(By.XPATH, "//p[text() = 'Submitted']/../div/div/p").text).isoformat()

        if after_str is not None:
            after_date = datetime.strptime(after_str, '%Y-%m-%d %H:%M')
            curr_date = datetime.fromisoformat(date)
            if after_date > curr_date:
                break   
        
        transactions.append({
            "description": ticker.text,
            "type": transactionType.text,
            "amount": amount.text,
            "date": date
        })
        amount.click()

    # Output
    report = json.dumps(transactions, indent=4)
    print(report)
    if output_path:
        with open(output_path, 'w') as f:
            f.write(report)