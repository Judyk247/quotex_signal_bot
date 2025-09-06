# telegram_utils.py
"""
Utility module for handling Telegram bot messaging.
Works with Quotex signals.
"""

import logging
import requests

# Use actual values directly (from your config)
TELEGRAM_BOT_TOKEN = "8393216803:AAGeejYBbXRMgKrp3zv8ifAxnOgYNMVZUBw"
TELEGRAM_CHAT_ID = "6005165491"

def send_telegram_message(signal_obj: dict) -> bool:
    """
    Send a trade signal message to the configured Telegram chat.
    
    Args:
        signal_obj (dict): Signal dictionary with keys:
            - symbol
            - signal (Buy/Call, Sell/Put)
            - confidence
            - timeframe
            - time
    Returns:
        bool: True if sent successfully, False otherwise.
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logging.error("[TELEGRAM] Missing bot token or chat ID")
        return False

    message = (
        f"📈 <b>New Signal Alert</b>\n"
        f"Symbol: <b>{signal_obj.get('symbol')}</b>\n"
        f"Signal: <b>{signal_obj.get('signal')}</b>\n"
        f"Confidence: <b>{signal_obj.get('confidence')}%</b>\n"
        f"Timeframe: <b>{signal_obj.get('timeframe')}s</b>\n"
        f"Time: <b>{signal_obj.get('time')}</b>"
    )

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }

    try:
        response = requests.post(url, json=payload, timeout=5)
        if response.status_code == 200:
            logging.info(f"[TELEGRAM] Message sent: {signal_obj.get('symbol')} - {signal_obj.get('signal')}")
            return True
        else:
            logging.error(f"[TELEGRAM] Failed to send message: {response.text}")
            return False
    except Exception as e:
        logging.error(f"[TELEGRAM] Exception sending message: {str(e)}")
        return False
