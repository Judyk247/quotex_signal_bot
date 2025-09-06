import json
import time
import threading
import logging
import socketio
from datetime import datetime, timezone
import pandas as pd
from credentials import QUOTEX_SESSION_TOKEN
from strategy import analyze_candles
from telegram_utils import send_telegram_message
from config import get_dynamic_symbols, get_timeframes, add_candle

# -----------------------------
# Debug logger setup
def setup_debug_logger():
    """Enable full debug logging for Socket.IO and our app."""
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    logging.getLogger("socketio").setLevel(logging.DEBUG)
    logging.getLogger("engineio").setLevel(logging.DEBUG)
    logging.debug("[DEBUG] Debug logger initialized")

# -----------------------------
# Quotex Socket.IO URL
QUOTEX_WS_URL = "wss://ws2.qxbroker.com/socket.io/?EIO=3&transport=websocket"

# SocketIO instance injected from app.py
socketio_instance = None

# Python Socket.IO client
sio = socketio.Client(
    logger=logging.getLogger("socketio"),
    engineio_logger=logging.getLogger("engineio"),
    reconnection=True,
    reconnection_attempts=0,
    reconnection_delay=5
)

# Store market data locally
market_data = {}

# Track currently subscribed symbols/timeframes
subscribed = {}  # {symbol: set(periods)}

# -----------------------------
@sio.event
def connect():
    logging.info("[CONNECT] Connecting to Quotex Socket.IO...")

    if not QUOTEX_SESSION_TOKEN:
        logging.error("[AUTH ERROR] No QUOTEX_SESSION_TOKEN found in .env")
        return

    try:
        # Establish WebSocket connection
        sio.connect(
            "wss://ws2.qxbroker.com/socket.io/?EIO=3&transport=websocket",
            transports=["websocket"],
            headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                              "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Origin": "https://qxbroker.com",
                "Cookie": f"session={QUOTEX_SESSION_TOKEN}; activeAccount=live"
            }
        )

        # Send authorization payload
        auth_payload = [
            "authorization",
            {
                "session": QUOTEX_SESSION_TOKEN,
                "isDemo": 0,        # 0 = live, 1 = demo
                "tournamentId": 0
            }
        ]
        sio.emit("message", auth_payload)
        logging.info("[AUTH] Sent authorization payload ✅")

    except Exception as e:
        logging.error(f"[FATAL ERROR] {e}")
        logging.info("⏳ Reconnecting in 5 seconds...")
        time.sleep(5)
        connect()  # Retry

# -----------------------------
@sio.on("candle")
def handle_candle(data):
    try:
        asset = data["asset"]
        period = data["period"]

        selected_symbols = get_dynamic_symbols()
        selected_timeframes = get_timeframes()

        if asset not in selected_symbols or period not in selected_timeframes:
            return

        # Store candle
        add_candle(asset, period, data)
        candle_list = market_data.setdefault(asset, {}).setdefault("candles", {}).setdefault(period, [])
        candle_list.append(data)

        # --- Analyze candle ---
        df = pd.DataFrame(candle_list)[["open", "high", "low", "close"]]
        result = analyze_candles(df)

        if result and result.get("signal"):
            signal_obj = {
                "symbol": asset,
                "signal": result["signal"],
                "confidence": result["confidence"],
                "time": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                "timeframe": period
            }

            # Emit to dashboard
            if socketio_instance:
                socketio_instance.emit("new_signal", signal_obj)

            # Store latest signals (max 50)
            latest_signals = getattr(socketio_instance, "latest_signals", [])
            latest_signals.append(signal_obj)
            if len(latest_signals) > 50:
                latest_signals.pop(0)
            socketio_instance.latest_signals = latest_signals

            # Send Telegram alert
            send_telegram_message(signal_obj)

    except Exception as e:
        logging.error(f"[CANDLE ERROR] {e}")

# -----------------------------
@sio.on("*")
def catch_all(event, data=None):
    try:
        logging.debug(f"[CATCH-ALL] Event: {event} | Data: {str(data)[:500]}")
    except Exception as e:
        logging.error(f"[CATCH-ALL ERROR] {e}")

