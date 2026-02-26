#!/usr/bin/env python3
"""
Simplified startup script for Article Summarizer Agent
"""

import os
import sys
import subprocess
import webbrowser
import time
from pathlib import Path

def main():
    print("🚀 Article Summarizer Agent - Web Application Startup")
    print("=" * 60)
    
    # Check if we're in the right directory
    if not Path("app.py").exists():
        print("❌ Error: app.py not found. Please run this script from the project root directory.")
        return
    
    # Create necessary directories
    print("📁 Creating necessary directories...")
    os.makedirs('outputs', exist_ok=True)
    os.makedirs('static/css', exist_ok=True)
    os.makedirs('static/js', exist_ok=True)
    os.makedirs('.cache', exist_ok=True)
    
    # Check if dependencies are installed
    try:
        import flask
        import requests
        import transformers
        print("✅ Dependencies verified")
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("Please run: python -m pip install -r requirements.txt")
        return
    
    # Start the application
    print("🌐 Starting the web application...")
    print("📡 Server will be available at: http://localhost:5000")
    print("🔄 Starting in 3 seconds...")
    time.sleep(3)
    
    # Open browser automatically
    try:
        webbrowser.open("http://localhost:5000")
    except:
        pass
    
    # Start the Flask app
    print("🚀 Launching Flask application...")
    os.system("python app.py")

if __name__ == "__main__":
    main() 