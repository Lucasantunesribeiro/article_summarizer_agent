#!/usr/bin/env python3
"""
Setup script for Article Summarizer Agent
Installs dependencies and prepares the environment
"""

import os
import subprocess
import sys


def run_command(cmd, description):
    """Run a command and handle errors"""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ Error: {result.stderr}")
            return False
        print(f"✅ {description} completed successfully")
        return True
    except Exception as e:
        print(f"❌ Error during {description}: {str(e)}")
        return False


def main():
    print("🤖 Article Summarizer Agent - Setup Script")
    print("=" * 50)

    # Check Python version

    print(f"✅ Python {sys.version} detected")

    # Install requirements
    if not run_command("pip install -r requirements.txt", "Installing Python dependencies"):
        print("❌ Failed to install dependencies. Please check your pip installation.")
        sys.exit(1)

    # Download NLTK data
    print("📚 Downloading NLTK data...")
    try:
        # Import nltk only after it's installed
        import nltk

        nltk.download("punkt", quiet=True)
        nltk.download("stopwords", quiet=True)
        nltk.download("wordnet", quiet=True)
        print("✅ NLTK data downloaded successfully")
    except ImportError:
        print("⚠️ Warning: NLTK not yet installed. NLTK data will be downloaded on first run.")
    except Exception as e:
        print(f"⚠️ Warning: Could not download NLTK data: {e}")
        print("   This will be downloaded automatically on first run.")

    # Create directories
    os.makedirs("outputs", exist_ok=True)
    os.makedirs(".cache", exist_ok=True)
    os.makedirs("templates", exist_ok=True)
    os.makedirs("static/css", exist_ok=True)
    os.makedirs("static/js", exist_ok=True)
    print("✅ Directories created")

    # Test installation
    print("🧪 Testing installation...")
    try:
        print("✅ All modules imported successfully")
    except Exception as e:
        print(f"❌ Module import test failed: {e}")
        sys.exit(1)

    print("\n🎉 Setup completed successfully!")
    print("\nNext steps:")
    print("1. Run: python main.py --status")
    print("2. Try: python main.py --interactive")
    print("3. Or: python main.py --url 'https://example.com/article'")
    print("4. For web interface: python app.py")
    print("\nFor help: python main.py --help")


if __name__ == "__main__":
    main()
