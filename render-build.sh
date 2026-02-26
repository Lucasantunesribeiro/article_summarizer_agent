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
wget -q -O chrome.zip https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/114.0.5735.90/linux64/chrome-linux64.zip
unzip -q chrome.zip
rm chrome.zip

echo "Chrome installed in $HOME/opt/chrome/chrome-linux64/chrome"
