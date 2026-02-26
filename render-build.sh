#!/usr/bin/env bash
# exit on error
set -o errexit

# Define Chrome and ChromeDriver versions
CHROME_VERSION="114.0.5735.90"

# Install Python requirements
pip install -r requirements.txt

# Create a place to store Chrome
mkdir -p $HOME/opt/chrome
cd $HOME/opt/chrome

# Download and extract Chrome
echo "Downloading Google Chrome..."
wget -q -O chrome.zip https://storage.googleapis.com/chrome-for-testing-public/133.0.6943.141/linux64/chrome-linux64.zip
unzip -q chrome.zip
rm chrome.zip

echo "Downloading ChromeDriver..."
wget -q -O chromedriver.zip https://storage.googleapis.com/chrome-for-testing-public/133.0.6943.141/linux64/chromedriver-linux64.zip
unzip -q chromedriver.zip
rm chromedriver.zip

echo "Chrome and ChromeDriver installed in $HOME/opt/chrome"
