import websocket
import json
import threading
import time
import logging
import base64
import os
from config.credentials import Credentials
from utils.logger import setup_logger

logger = setup_logger('websocket_client')

# Try to import cloudscraper
try:
    import cloudscraper
    CLOUDSCRAPER_AVAILABLE = True
except ImportError:
    CLOUDSCRAPER_AVAILABLE = False
    logger.warning("cloudscraper not installed. Run: pip install cloudscraper")

class QuotexWebSocketClient:
    def __init__(self):
        self.ws = None
        self.connected = False
        self.authenticated = False
        self.ping_interval = 25000
        self.ping_timeout = 5000
        self.sid = None
        self.cloudflare_cookies = ""
        self.message_count = 0
        self.on_message_callback = None  # Callback for processed messages
        
    def bypass_cloudflare(self):
        """Bypass Cloudflare protection using cloudscraper"""
        if not CLOUDSCRAPER_AVAILABLE:
            logger.error("cloudscraper not installed. Run: pip install cloudscraper")
            return False

        logger.info("Bypassing Cloudflare protection...")
        try:
            scraper = cloudscraper.create_scraper()
            scraper.headers = {
                'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }

            response = scraper.get('https://qxbroker.com', timeout=30)

            if response.status_code == 200:
                cookies_dict = scraper.cookies.get_dict()
                self.cloudflare_cookies = "; ".join([f"{k}={v}" for k, v in cookies_dict.items()])
                logger.info("Cloudflare bypass successful!")
                return True
            else:
                logger.error(f"Cloudflare bypass failed. Status: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Cloudflare bypass error: {e}")
            return False

    def on_open(self, ws):
        logger.info("WebSocket connected")
        self.connected = True

    def on_message(self, ws, message):
        try:
            self.message_count += 1
            
            if isinstance(message, bytes):
                message = message.decode('utf-8')

            logger.debug(f"Received #{self.message_count}: {message[:200]}...")

            # Handle different message types
            if message.startswith('0{'):
                conn_info = json.loads(message[1:])
                self.sid = conn_info.get('sid')
                self.ping_interval = conn_info.get('pingInterval', 25000)
                self.ping_timeout = conn_info.get('pingTimeout', 5000)
                logger.info(f"Connection established. SID: {self.sid}")

            elif message == '40':
                logger.info("Namespace connected, sending authentication")
                auth_data = {
                    "session": Credentials.SESSION_ID,
                    "isDemo": Credentials.IS_DEMO,
                    "tournamentId": Credentials.TOURNAMENT_ID
                }
                auth_msg = f'42["authorization",{json.dumps(auth_data)}]'
                ws.send(auth_msg)
                logger.debug(f"Sent: {auth_msg}")

            elif message.startswith('42['):
                try:
                    json_data = json.loads(message[2:])
                    self.handle_data_message(json_data)
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse JSON: {message}")

            elif message == '2':
                ws.send('3')  # Pong response
                logger.debug("Sent pong response")

            else:
                logger.debug(f"Unhandled message: {message}")

            # Send raw message to callback for processing
            if self.on_message_callback:
                self.on_message_callback(message)

        except Exception as e:
            logger.error(f"Message processing error: {e}")

    def handle_data_message(self, data):
        if not isinstance(data, list) or len(data) == 0:
            return

        message_type = data[0]

        if message_type == "authorization":
            auth_data = data[1] if len(data) > 1 else {}
            logger.info(f"Auth response: {auth_data}")

            if auth_data.get("success", False):
                logger.info("Authentication successful!")
                self.authenticated = True
                self.subscribe_to_assets()
            else:
                logger.error(f"Authentication failed: {auth_data}")

        elif message_type == "instruments/list":
            instruments = data[1] if len(data) > 1 else []
            logger.info(f"Received {len(instruments)} instruments")

        elif message_type == "tick":
            tick_data = data[1] if len(data) > 1 else {}
            logger.debug(f"Tick data: {tick_data}")

    def on_error(self, ws, error):
        logger.error(f"WebSocket error: {error}")
        self.connected = False
        self.authenticated = False

    def on_close(self, ws, close_status_code, close_msg):
        logger.info(f"WebSocket connection closed: {close_msg}")
        self.connected = False
        self.authenticated = False

    def connect(self):
        """Connect to Quotex WebSocket with Cloudflare bypass"""
        try:
            # First bypass Cloudflare
            self.bypass_cloudflare()

            # Generate WebSocket key
            key = base64.b64encode(os.urandom(16)).decode('utf-8')

            # Prepare headers with Cloudflare cookies
            headers = [
                "Host: ws2.qxbroker.com",
                "Connection: Upgrade",
                "Pragma: no-cache",
                "Cache-Control: no-cache",
                "User-Agent: Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36",
                "Upgrade: websocket",
                "Origin: https://qxbroker.com",
                "Sec-WebSocket-Version: 13",
                "Accept-Encoding: gzip, deflate, br, zstd",
                "Accept-Language: en-US,en;q=0.9",
                f"Sec-WebSocket-Key: {key}",
                "Sec-WebSocket-Extensions: permessage-deflate; client_max_window_bits"
            ]

            if self.cloudflare_cookies:
                headers.append(f"Cookie: {self.cloudflare_cookies}")

            # Create WebSocket connection
            self.ws = websocket.WebSocketApp(
                Credentials.WS_URL,
                on_open=self.on_open,
                on_message=self.on_message,
                on_error=self.on_error,
                on_close=self.on_close,
                header=headers
            )

            # Start WebSocket in background thread
            wst = threading.Thread(target=self.ws.run_forever)
            wst.daemon = True
            wst.start()

            # Wait for connection
            for i in range(50):  # 5 second timeout
                if self.connected:
                    return True
                time.sleep(0.1)

            logger.error("WebSocket connection timeout")
            return False

        except Exception as e:
            logger.error(f"Connection error: {e}")
            return False

    def subscribe_to_assets(self):
        """Subscribe to assets for trading"""
        if not self.authenticated or not self.ws:
            return

        # Use assets from settings
        from config.settings import TRADING_SETTINGS
        assets = TRADING_SETTINGS['assets']
        timeframes = TRADING_SETTINGS['timeframes']

        for asset in assets:
            for timeframe in timeframes:
                try:
                    subscribe_msg = f'42["instruments/update",{{"asset":"{asset}","period":{self._timeframe_to_seconds(timeframe)}}}]'
                    self.ws.send(subscribe_msg)
                    logger.info(f"Subscribed to {asset} ({timeframe})")
                    time.sleep(0.5)
                except Exception as e:
                    logger.error(f"Failed to subscribe to {asset}: {e}")

    def _timeframe_to_seconds(self, timeframe):
        if timeframe == '1m': return 60
        if timeframe == '2m': return 120
        if timeframe == '3m': return 180
        if timeframe == '5m': return 300
        return 60

    def keep_alive(self):
        """Keep WebSocket connection alive"""
        while self.connected:
            try:
                time.sleep(self.ping_interval / 1000)
                if self.ws and self.connected:
                    self.ws.send('2')  # Ping
            except Exception as e:
                logger.error(f"Keep alive error: {e}")
                time.sleep(5)

    def disconnect(self):
        """Disconnect from WebSocket"""
        if self.ws:
            self.ws.close()
            self.connected = False
            self.authenticated = False
            logger.info("Disconnected from WebSocket")
