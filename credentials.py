# credentials.py

import os

# Base WebSocket URL for Quotex
QUOTEX_WS_URL = os.getenv("QUOTEX_WS_URL")

# Auth/session credentials (replace with your own or set via env vars)
QUOTEX_SESSION_TOKEN = os.getenv("QUOTEX_SESSION_TOKEN", "")
QUOTEX_USER_ID = os.getenv("QUOTEX_USER_ID", "")
QUOTEX_ACCOUNT_URL = os.getenv("QUOTEX_ACCOUNT_URL", "https://qxbroker.com/en/trade")
