import json
import time
import threading
import logging
import socketio
from datetime import datetime, timezone
import pandas as pd

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
    logging.info("[CONNECT] Connected to Quotex Socket.IO")
    logging.info("[AUTH] Quotex connection established ✅")

@sio.event
def disconnect():
    logging.warning("[DISCONNECT] Connection closed, attempting reconnect...")

# -----------------------------
@sio.on("tick")
def handle_tick(data):
    """
    data = [symbol, timestamp, price, direction_flag]
    Store ticks locally for reference (optional)
    """
    try:
        symbol = data[0]
        ts = data[1]
        price = data[2]

        # Only process admin-selected symbols
        if symbol not in get_dynamic_symbols():
            return

        market_data.setdefault(symbol, {}).setdefault("ticks", []).append({
            "time": ts,
            "price": price
        })

    except Exception as e:
        logging.error(f"[TICK ERROR] {e}")

@sio.on("candle")
def handle_candle(data):
    """
    data = {
        "asset": "USDINR_otc",
        "period": 60,
        "open": ...,
        "high": ...,
        "low": ...,
        "close": ...,
        "time": ...
    }
    """
    try:
        asset = data["asset"]
        period = data["period"]

        # Only process admin-selected symbols and timeframes
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
    """Catch-all debug logger for every incoming event."""
    try:
        logging.debug(f"[CATCH-ALL] Event: {event} | Data: {str(data)[:500]}")
    except Exception as e:
        logging.error(f"[CATCH-ALL ERROR] {e}")

# -----------------------------
def sync_subscriptions():
    """
    Dynamically subscribe/unsubscribe symbols and timeframes
    based on admin dashboard selections.
    """
    global subscribed

    selected_symbols = set(get_dynamic_symbols())
    selected_timeframes = set(get_timeframes())

    # Subscribe new symbols/timeframes
    for symbol in selected_symbols:
        periods = subscribed.get(symbol, set())
        for period in selected_timeframes:
            if period not in periods:
                try:
                    sio.emit("subscribe", {"type": "candles", "asset": symbol, "period": period})
                    logging.info(f"[SUBSCRIBE] Subscribed {symbol} to {period}s candles")
                    periods.add(period)
                except Exception as e:
                    logging.error(f"[SUBSCRIBE ERROR] {symbol} {period}: {e}")
        subscribed[symbol] = periods

    # Unsubscribe removed symbols or periods
    for symbol in list(subscribed.keys()):
        periods = subscribed[symbol]
        for period in list(periods):
            if symbol not in selected_symbols or period not in selected_timeframes:
                try:
                    sio.emit("unsubscribe", {"type": "candles", "asset": symbol, "period": period})
                    logging.info(f"[UNSUBSCRIBE] Unsubscribed {symbol} from {period}s candles")
                    periods.remove(period)
                except Exception as e:
                    logging.error(f"[UNSUBSCRIBE ERROR] {symbol} {period}: {e}")
        if not periods:
            del subscribed[symbol]

# -----------------------------
# Periodically sync subscriptions
def subscription_sync_worker():
    while True:
        try:
            sync_subscriptions()
        except Exception as e:
            logging.error(f"[SYNC ERROR] {e}")
        time.sleep(5)  # check every 5 seconds

# -----------------------------
def run_quotex_ws(socketio_from_app):
    """Connect to Quotex and process data for selected symbols/timeframes."""
    global socketio_instance
    socketio_instance = socketio_from_app

    try:
        logging.info(f"🔌 Connecting to Quotex Socket.IO...")
        sio.connect(
            QUOTEX_WS_URL,
            transports=["websocket"],
            headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                              "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Origin": "https://qxbroker.com",
            }
        )

        # Start subscription sync worker
        threading.Thread(target=subscription_sync_worker, daemon=True).start()

        sio.wait()
    except Exception as e:
        logging.error(f"[FATAL ERROR] {e}")
        logging.info("⏳ Reconnecting in 5 seconds...")
        time.sleep(5)
        run_quotex_ws(socketio_from_app)

def start_quotex_ws(socketio_from_app):
    """Start Quotex Socket.IO in a separate thread."""
    t = threading.Thread(
        target=run_quotex_ws,
        args=(socketio_from_app,),
        daemon=True
    )
    t.start()

# -----------------------------
def get_dynamic_symbols_list():
    """Return the latest dynamic symbols"""
    return get_dynamic_symbols()

# -----------------------------
if __name__ == "__main__":
    logging.info("⚠️ Run this only from app.py, not directly.")
