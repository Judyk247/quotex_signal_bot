import threading
import logging
from datetime import datetime
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO
from strategy import analyze_candles
from telegram_utils import send_telegram_message
from data_fetcher import get_dynamic_symbols
from config import TIMEFRAMES, TELEGRAM_CHAT_IDS, update_symbols

# 👇 Import Quotex Socket.IO WebSocket
from quotex_ws import start_quotex_ws, setup_debug_logger

setup_debug_logger()

# Flask app setup
app = Flask(__name__)
CORS(app)
app.config["TEMPLATES_AUTO_RELOAD"] = True
socketio = SocketIO(app, async_mode="eventlet")

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

latest_signals = []  # Store latest signals for dashboard
MAX_SIGNALS = 50     # Keep only the last 50

# Admin-selected symbols/timeframes (updated from dashboard)
selected_symbols = []      # ["EURUSD_otc", ...]
selected_timeframes = []   # [60, 180, 300]


# -----------------------------
# Background worker manager
def start_background_workers():
    """Start Quotex Socket.IO worker + data fetcher."""
    logging.info("🔌 Connecting to Quotex via Python Socket.IO...")

    # Inject Flask SocketIO instance into Quotex WS
    start_quotex_ws(socketio)
# -----------------------------


# -----------------------------
# Dashboard routes
@app.route("/")
def dashboard():
    logging.info("Rendering dashboard page")
    return render_template("dashboard.html")


@app.route("/signals_data")
def signals_data():
    signals_out = latest_signals if latest_signals else [
        {
            "symbol": "-",
            "signal": "No signals yet",
            "confidence": 0,
            "time": "-",
            "timeframe": "-"
        }
    ]
    return jsonify({
        "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "signals": signals_out,
        "mode": "LIVE"
    })


@app.route("/symbols")
def symbols():
    """Return available symbols and timeframes for admin selection."""
    symbols_list = get_dynamic_symbols()  # Fetch dynamically from Quotex or cached
    return jsonify({"symbols": symbols_list, "timeframes": TIMEFRAMES})


@app.route("/update_symbols", methods=["POST"])
def update_symbols_endpoint():
    """
    Admin posts new symbols/timeframes.
    Example payload: {"symbols": ["EURUSD_otc","USDJPY_otc"], "timeframes": [60,180,300]}
    """
    global selected_symbols, selected_timeframes

    data = request.json
    new_symbols = data.get("symbols", [])
    new_timeframes = data.get("timeframes", [])

    # Update shared references
    selected_symbols = new_symbols
    selected_timeframes = new_timeframes

    # Update config (for global access)
    update_symbols(new_symbols)

    # Notify Quotex WS dynamically
    socketio.emit("symbols_update", {"symbols": new_symbols, "timeframes": new_timeframes})
    logging.info(f"✅ Symbols/timeframes updated dynamically: {new_symbols} | {new_timeframes}")

    return jsonify({"status": "success", "symbols": new_symbols, "timeframes": new_timeframes})
# -----------------------------


# -----------------------------
# Emit signals immediately to new dashboard clients
@socketio.on("connect")
def on_connect():
    logging.info("Client connected, sending current signals...")
    for sig in latest_signals:
        socketio.emit("new_signal", sig)
# -----------------------------


if __name__ == "__main__":
    logging.info("Starting Flask-SocketIO app on 0.0.0.0:5000")

    # ✅ Start background workers for Quotex
    start_background_workers()

    socketio.run(app, host="0.0.0.0", port=5000, debug=False)
