"""
PydanticAI + Gemini Starter Project
Entry point — runs the portfolio analysis demo.
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()


def check_api_key():
    key = os.getenv("GOOGLE_API_KEY", "").strip()
    if not key or key == "your-gemini-api-key-here":
        print("\nError: GOOGLE_API_KEY not set or invalid.")
        print("Setup steps:")
        print("  1. Copy .env.example to .env")
        print("  2. Paste your Gemini API key into .env")
        print("  3. Get a free key at https://aistudio.google.com/app/apikey")
        sys.exit(1)


if __name__ == "__main__":
    check_api_key()
    from demo_stocks import run
    run()
