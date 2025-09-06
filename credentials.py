# credentials.py
import os
from dotenv import load_dotenv

# Load .env variables
load_dotenv()

# 🔑 Quotex credentials
QUOTEX_EMAIL = os.getenv("QUOTEX_EMAIL", "")
QUOTEX_PASSWORD = os.getenv("QUOTEX_PASSWORD", "")
QUOTEX_SESSION_TOKEN = os.getenv("QUOTEX_SESSION_TOKEN", "")

# Quotex WebSocket endpoint
QUOTEX_WS_URL = "wss://ws2.qxbroker.com/socket.io/?EIO=3&transport=websocket"

# Quotex API base URL
QUOTEX_API_URL = "https://qxbroker.com"

# Safety check: ensure session token is set for manual login mode
if not QUOTEX_SESSION_TOKEN:
    raise EnvironmentError("❌ QUOTEX_SESSION_TOKEN is missing in .env")
