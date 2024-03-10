# Wealthsimpleton

A Python script that scrapes your Wealthsimple activity history and saves the data in a JSON file.

The data scraped includes:
- Transaction description
- Transaction type
- Transaction amount
- Transaction date

## Usage

1. Ensure Python dependencies are installed: `pip install -r requirements.txt`
2. Ensure you have Chromium or Google Chrome installed.
3. Ensure you have Chrome Webdriver installed and that it is compatible with the version of Chromium/Chrome you have.
   - On Linux, you can run `installChromeDriver.sh` to automatically install/update ChromeDriver in `/usr/local/bin`,
4. Optionally, create a [`.env`](https://www.dotenv.org/docs/security/env.html) file with your Wealthsimple credentials defined as `WS_EMAIL` and `WS_PASSWORD` (or ensure those environment variables are present in some other way).
   - If you skip this, you will need to login manually when the script starts.
   - Note that even with these variables defined, you may still need to manually perform some login steps like 2FA or CAPTCHA.
5. Run the script: `python main.py`
   - You can use the `--after` argument to only include orders after a certain date/time (format is `%Y-%m-%d %H:%M`).
   - The output is printed to the terminal; if you would like to also save it to a file, use the `--file` argument with a valid file path.