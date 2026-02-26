#!/usr/bin/env bash
# Render build script — installs Python dependencies only.
# Chrome/Selenium are NOT supported on Render's free tier.
# JS rendering falls back gracefully to plain HTTP when selenium is absent.
set -o errexit

pip install -r requirements.txt
