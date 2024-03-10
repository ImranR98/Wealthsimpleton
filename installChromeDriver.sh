#!/bin/bash

CHROME_PATH="$(which chromium-browser)"
if [ -z "$CHROME_PATH" ]; then
    CHROME_PATH="$(which google-chrome)"
fi
if [ -z "$CHROME_PATH" ]; then
    echo "Neither chromium-browser nor google-chrome were found in your PATH!" >&2
    exit 1
fi

CHROME_VERSION="$("$CHROME_PATH" --version | grep -Eo '([0-9]+\.)+[0-9]+' | sed -r 's/(.*)\..*/\1/')"

if [ -n "$(which chromedriver)" ]; then
    CHROMEDRIVER_VERSION="$(chromedriver --version | grep -Eo '([0-9]+\.)+[0-9]+' | sed -r 's/(.*)\..*/\1/')"
else
    CHROMEDRIVER_VERSION="N/A"
fi

if [ "$CHROME_VERSION" != "$CHROMEDRIVER_VERSION" ]; then
    echo "Chrome version is $CHROME_VERSION but ChromeDriver version is $CHROMEDRIVER_VERSION - downloading new ChromeDriver..."
    NEW_CHROMEDRIVER_URL="$(curl -s https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json | sed 's/"url"/\n"url"/g' | grep -o 'url"[^"]*"[^"]*"' | grep "$CHROME_VERSION" | grep 'chromedriver-linux64.zip' | tail -1 | head -c -2 | tail -c +7 | cat)"
    curl "$NEW_CHROMEDRIVER_URL" -o /tmp/chromedriver-"$CHROME_VERSION".zip
    unzip /tmp/chromedriver-"$CHROME_VERSION".zip -d /tmp
    rm /tmp/chromedriver-"$CHROME_VERSION".zip
    echo "Installing..."
    sudo mv /tmp/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver
    rm -r /tmp/chromedriver-linux64
else
    echo "ChromeDriver is up to date ($CHROMEDRIVER_VERSION)."
fi
