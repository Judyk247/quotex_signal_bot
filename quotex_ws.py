import json
import time
import threading
import logging
import socketio
from datetime import datetime, timezone
import pandas as pd
import importlib
import os

# Local modules
import credentials  # will be reloaded dynamically
from strategy import analyze_candles
from telegram_utils import send_telegram_message
from config import get_dynamic_symbols, get_timeframes, add_candle

# -----------------------------
# SocketIO client
sio = socketio.Client(
    reconnection=False  # we handle reconnection manually
)

socketio_instance = None
market_data = {}
subscribed = {}

_last_creds_snapshot = None  # Track last loaded credentials

# -----------------------------
def load_creds():
    """Reload credentials.py dynamically each reconnect."""
    global _last_creds_snapshot
    importlib.reload(credentials)
    creds = {
        "SESSION": credentials.QUOTEX_SESSION_TOKEN,
        "IS_DEMO": credentials.QUOTEX_IS_DEMO,
        "TOURNAMENT_ID": credentials.QUOTEX_TOURNAMENT_ID,
        "USER_AGENT": credentials.QUOTEX_USER_AGENT,
        "ORIGIN": credentials.QUOTEX_ORIGIN,
        "COOKIE": credentials.QUOTEX_COOKIE,
        "WS_URL": credentials.QUOTEX_WS_URL,
    }
    return creds

def creds_changed(new_creds):
    """Check if credentials.py has been updated."""
    global _last_creds_snapshot
    if _last_creds_snapshot is None:
        _last_creds_snapshot = new_creds
        return False
    if _last_creds_snapshot != new_creds:
        logging.info("[CREDS] Detected credentials.py update 🔄 Forcing reconnect...")
        _last_creds_snapshot = new_creds
        return True
    return False

# -----------------------------
@sio.event
def connect():
    logging.info("[CONNECT] Connected to Quotex ✅")

    creds = load_creds()
    if not creds["SESSION"]:
        logging.error("[AUTH ERROR] No QUOTEX_SESSION_TOKEN in credentials.py")
        return

    try:
        auth_payload = [
            "authorization",
            {
                "session": creds["SESSION"],
                "isDemo": creds["IS_DEMO"],
                "tournamentId": creds["TOURNAMENT_ID"]
            }
        ]
        sio.emit("message", auth_payload)
        logging.info("[AUTH] Sent authorization payload ✅")
    except Exception as e:
        logging.error(f"[AUTH ERROR] Failed: {e}")

@sio.event
def disconnect():
    logging.warning("[DISCONNECT] Lost connection ⚠️")
    logging.info("⏳ Will retry automatically...")

# -----------------------------
@sio.on("candle")
def handle_candle(data):
    try:
        asset = data["asset"]
        period = data["period"]

        if asset not in get_dynamic_symbols() or period not in get_timeframes():
            return

        add_candle(asset, period, data)
        candles = market_data.setdefault(asset, {}).setdefault("candles", {}).setdefault(period, [])
        candles.append(data)

        df = pd.DataFrame(candles)[["open", "high", "low", "close"]]
        result = analyze_candles(df)

        if result and result.get("signal"):
            signal_obj = {
                "symbol": asset,
                "signal": result["signal"],
                "confidence": result["confidence"],
                "time": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                "timeframe": period
            }

            if socketio_instance:
                socketio_instance.emit("new_signal", signal_obj)

            latest_signals = getattr(socketio_instance, "latest_signals", [])
            latest_signals.append(signal_obj)
            if len(latest_signals) > 50:
                latest_signals.pop(0)
            socketio_instance.latest_signals = latest_signals

            send_telegram_message(signal_obj)

    except Exception as e:
        logging.error(f"[CANDLE ERROR] {e}")

# -----------------------------
def sync_subscriptions():
    global subscribed
    symbols = set(get_dynamic_symbols())
    periods = set(get_timeframes())

    for symbol in symbols:
        subs = subscribed.get(symbol, set())
        for p in periods:
            if p not in subs:
                try:
                    sio.emit("subscribe", {"type": "candles", "asset": symbol, "period": p})
                    logging.info(f"[SUBSCRIBE] {symbol} {p}s")
                    subs.add(p)
                except Exception as e:
                    logging.error(f"[SUBSCRIBE ERROR] {symbol} {p}: {e}")
        subscribed[symbol] = subs

    for symbol in list(subscribed.keys()):
        subs = subscribed[symbol]
        for p in list(subs):
            if symbol not in symbols or p not in periods:
                try:
                    sio.emit("unsubscribe", {"type": "candles", "asset": symbol, "period": p})
                    logging.info(f"[UNSUBSCRIBE] {symbol} {p}s")
                    subs.remove(p)
                except Exception as e:
                    logging.error(f"[UNSUBSCRIBE ERROR] {symbol} {p}: {e}")
        if not subs:
            del subscribed[symbol]

def subscription_sync_worker():
    while True:
        try:
            sync_subscriptions()
        except Exception as e:
            logging.error(f"[SYNC ERROR] {e}")
        time.sleep(5)

# -----------------------------
def run_quotex_ws(socketio_from_app):
    global socketio_instance
    socketio_instance = socketio_from_app

    while True:
        try:
            creds = load_creds()
            if creds_changed(creds) and sio.connected:
                # Force reconnect if creds updated
                logging.info("[CREDS] Forcing reconnect with new credentials...")
                sio.disconnect()

            if sio.connected:
                time.sleep(5)
                continue

            logging.info("🔌 Connecting to Quotex WebSocket...")

            sio.connect(
                creds["WS_URL"],
                transports=["websocket"],
                headers={
                    "User-Agent": creds["USER_AGENT"],
                    "Origin": creds["ORIGIN"],
                    "Cookie": creds["COOKIE"]
                },
                socketio_path="socket.io"
            )

            threading.Thread(target=subscription_sync_worker, daemon=True).start()
            sio.wait()

        except Exception as e:
            logging.error(f"[CONNECTION ERROR] {e}")
            logging.info("⏳ Retrying in 5 seconds...")
            time.sleep(5)

# -----------------------------
def start_quotex_ws(socketio_from_app):
    threading.Thread(
        target=run_quotex_ws,
        args=(socketio_from_app,),
        daemon=True
    ).start()
