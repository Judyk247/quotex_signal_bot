import os
import threading
import time
from collections import defaultdict
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- Telegram ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_IDS = os.getenv("TELEGRAM_CHAT_IDS", "").split(",")

# --- Timeframes ---
TIMEFRAMES = ["1m", "3m", "5m"]
CANDLE_PERIODS = {"1m": 60, "3m": 180, "5m": 300}

# --- Debug ---
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# --- Market data ---
market_data = defaultdict(lambda: {"candles": defaultdict(list)})

# --- Symbols loaded dynamically by admin dashboard ---
SYMBOLS = []

# --- Heartbeat interval (for SocketIO connection) ---
HEARTBEAT_INTERVAL = 5  # seconds

# -----------------------------
# Functions for dynamic symbols
def update_symbols(new_symbols):
    """
    Update the list of symbols dynamically (from admin/dashboard)
    and initialize their market_data storage.
    """
    global SYMBOLS
    SYMBOLS = new_symbols
    for symbol in SYMBOLS:
        if "candles" not in market_data[symbol]:
            market_data[symbol]["candles"] = defaultdict(list)
    if DEBUG:
        print(f"[CONFIG] Symbols updated dynamically: {SYMBOLS}")

def get_dynamic_symbols():
    """Return the current list of symbols selected for scanning."""
    return SYMBOLS

# -----------------------------
# Functions for dynamic timeframes
selected_timeframes = TIMEFRAMES.copy()

def update_timeframes(new_timeframes):
    """
    Update selected timeframes dynamically.
    new_timeframes should be a list of strings like ["1m", "3m"].
    """
    global selected_timeframes
    selected_timeframes = [tf for tf in new_timeframes if tf in CANDLE_PERIODS]
    if DEBUG:
        print(f"[CONFIG] Timeframes updated dynamically: {selected_timeframes}")

def get_timeframes():
    """Return the current list of selected timeframes."""
    return selected_timeframes

# -----------------------------
# Candle storage helper
def add_candle(symbol, timeframe, candle):
    """
    Add a new candle to market_data for a given symbol and timeframe.
    Keeps only last 50 candles.
    """
    if symbol not in SYMBOLS or timeframe not in selected_timeframes:
        # Symbol or timeframe not selected by admin, ignore
        return
    market_data[symbol]["candles"][timeframe].append(candle)
    if len(market_data[symbol]["candles"][timeframe]) > 50:
        market_data[symbol]["candles"][timeframe].pop(0)

# -----------------------------
# SocketIO heartbeat for keeping connection alive
def socketio_heartbeat(sio):
    """Send a periodic heartbeat to keep SocketIO connection alive."""
    while True:
        try:
            sio.emit("ping", {"time": int(time.time())})
        except Exception as e:
            if DEBUG:
                print("[HEARTBEAT ERROR]", e)
        time.sleep(HEARTBEAT_INTERVAL)

# -----------------------------
# Auto-start for testing if run standalone
if __name__ == "__main__":
    print("⚠️ config.py is meant to be imported by the app, not run standalone")
