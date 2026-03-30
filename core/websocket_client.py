import socketio
import json
import threading
import time
import cloudscraper
from config.credentials import Credentials
from utils.logger import setup_logger

logger = setup_logger('websocket_client')

class QuotexWebSocketClient:
    def __init__(self):
        self.sio = None
        self.connected = False
        self.authenticated = False
        self.on_message_callback = None
        self.session_token = None
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5

    def _get_session_via_http(self):
        """Fallback: obtain a fresh session token via HTTP login using cloudscraper"""
        try:
            scraper = cloudscraper.create_scraper()
            login_url = "https://qxbroker.com/api/login"
            payload = {
                "email": Credentials.EMAIL,
                "password": Credentials.PASSWORD
            }
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Origin": "https://qxbroker.com",
                "Referer": "https://qxbroker.com/"
            }
            resp = scraper.post(login_url, json=payload, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                token = data.get('session') or data.get('ssid') or data.get('token')
                if token:
                    logger.info("Obtained fresh session token via HTTP login")
                    return token
            logger.error(f"HTTP login failed: {resp.status_code} - {resp.text[:200]}")
            return None
        except Exception as e:
            logger.error(f"HTTP login error: {e}")
            return None

    def connect(self):
        """Connect to Quotex using Socket.IO client"""
        try:
            Credentials.validate()
            logger.info("Credentials validated. Proceeding with connection...")

            # --- HARDCODED SESSION TOKEN (replace with your current token if needed) ---
            self.session_token = "xgq9rwpdsFBD2deyugI1FhQnTPrdfWSOwfonxSZr"
            logger.info(f"Using hardcoded session token (length: {len(self.session_token)})")
            
            # If the hardcoded token fails, uncomment the line below to try env var or HTTP login
            # if not self.session_token:
            #     self.session_token = Credentials.SESSION_ID
            #     if not self.session_token:
            #         logger.warning("No SESSION_ID, attempting HTTP login...")
            #         self.session_token = self._get_session_via_http()
            #         if not self.session_token:
            #             logger.error("Failed to obtain session token")
            #             return False

            # --- HARDCODED WEBSOCKET URL (bypass env vars completely) ---
            base_url = "https://ws2.qxbroker.com"
            logger.info(f"Connecting to Socket.IO server at {base_url}")

            # Create Socket.IO client with detailed logging
            self.sio = socketio.Client(
                logger=True,           # Enable detailed logs
                engineio_logger=True,  # Show handshake details
                ssl_verify=False,
                http_session=cloudscraper.create_scraper()
            )

            # Event handlers
            @self.sio.event
            def connect():
                logger.info("Socket.IO connected, sending authorization")
                self.connected = True
                self.reconnect_attempts = 0
                self.sio.emit('authorization', {
                    'session': self.session_token,
                    'isDemo': Credentials.IS_DEMO,
                    'tournamentId': Credentials.TOURNAMENT_ID
                })

            @self.sio.event
            def connect_error(data):
                logger.error(f"Socket.IO connect_error: {data}")
                self.connected = False

            @self.sio.event
            def disconnect():
                logger.warning("Socket.IO disconnected")
                self.connected = False
                self.authenticated = False
                if self.reconnect_attempts < self.max_reconnect_attempts:
                    self.reconnect_attempts += 1
                    logger.info(f"Reconnecting in 5s (attempt {self.reconnect_attempts})")
                    time.sleep(5)
                    self.connect()

            @self.sio.on('authorization')
            def on_auth(data):
                logger.info(f"Authorization response: {data}")
                if data.get('success') or data.get('status') == 'ok' or data.get('success') == True:
                    self.authenticated = True
                    logger.info("Authentication successful!")
                    self.subscribe_to_assets()
                else:
                    logger.error(f"Authentication failed: {data}")
                    self.disconnect()

            @self.sio.on('tick')
            def on_tick(data):
                if self.on_message_callback:
                    self.on_message_callback(json.dumps(['tick', data]))

            @self.sio.on('instruments/update')
            def on_instruments(data):
                if self.on_message_callback:
                    self.on_message_callback(json.dumps(['instruments/update', data]))

            @self.sio.on('*')
            def catch_all(event, data):
                if self.on_message_callback:
                    self.on_message_callback(json.dumps([event, data]))

            # Connect with timeout
            self.sio.connect(
                base_url,
                transports=['websocket', 'polling'],
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                    'Origin': 'https://qxbroker.com',
                    'Referer': 'https://qxbroker.com/'
                },
                wait_timeout=15,
                wait=True
            )
            return True

        except socketio.exceptions.ConnectionError as e:
            logger.error(f"Socket.IO connection refused: {e}")
            return False
        except Exception as e:
            logger.error(f"Connection error: {type(e).__name__}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    def subscribe_to_assets(self):
        if not self.authenticated or not self.sio:
            return
        from config.settings import TRADING_SETTINGS
        assets = TRADING_SETTINGS['assets']
        timeframes = TRADING_SETTINGS['timeframes']
        for asset in assets:
            for timeframe in timeframes:
                try:
                    period = self._timeframe_to_seconds(timeframe)
                    self.sio.emit('instruments/update', {
                        'asset': asset,
                        'period': period
                    })
                    logger.info(f"Subscribed to {asset} ({timeframe})")
                    time.sleep(0.5)
                except Exception as e:
                    logger.error(f"Failed to subscribe to {asset}: {e}")

    def _timeframe_to_seconds(self, timeframe):
        mapping = {'1m': 60, '2m': 120, '3m': 180, '5m': 300}
        return mapping.get(timeframe, 60)

    def keep_alive(self):
        while self.connected:
            time.sleep(25)
            if self.sio and self.connected and not self.sio.connected:
                logger.warning("Socket.IO not connected, reconnecting...")
                self.connect()
                break

    def disconnect(self):
        if self.sio:
            self.sio.disconnect()
            self.connected = False
            self.authenticated = False
            logger.info("Disconnected")

    @property
    def ws(self):
        return self.sio
