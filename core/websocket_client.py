import socketio
import json
import threading
import time
import logging
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
            # Validate credentials
            Credentials.validate()
            logger.info("Credentials validated. Proceeding with connection...")

            # Get session token (use provided one or fetch via HTTP)
            self.session_token = Credentials.SESSION_ID
            if not self.session_token or self.session_token == "your_session_token_here":
                logger.warning("No valid SESSION_ID in env, attempting HTTP login...")
                self.session_token = self._get_session_via_http()
                if not self.session_token:
                    logger.error("Failed to obtain session token")
                    return False

            # Socket.IO client with custom headers
            self.sio = socketio.Client(
                logger=False,
                engineio_logger=False,
                ssl_verify=False,  # Some environments need this
                http_session=cloudscraper.create_scraper()  # Use cloudscraper for HTTP handshake
            )

            # Define event handlers
            @self.sio.event
            def connect():
                logger.info("Socket.IO connected, sending authorization")
                self.connected = True
                self.reconnect_attempts = 0
                # Send authorization event
                self.sio.emit('authorization', {
                    'session': self.session_token,
                    'isDemo': Credentials.IS_DEMO,
                    'tournamentId': Credentials.TOURNAMENT_ID
                })

            @self.sio.event
            def connect_error(data):
                logger.error(f"Connection error: {data}")
                self.connected = False

            @self.sio.event
            def disconnect():
                logger.warning("Socket.IO disconnected")
                self.connected = False
                self.authenticated = False
                # Auto-reconnect
                if self.reconnect_attempts < self.max_reconnect_attempts:
                    self.reconnect_attempts += 1
                    logger.info(f"Reconnecting in 5s (attempt {self.reconnect_attempts})")
                    time.sleep(5)
                    self.connect()

            @self.sio.on('authorization')
            def on_auth(data):
                logger.info(f"Authorization response: {data}")
                if data.get('success') or data.get('status') == 'ok':
                    self.authenticated = True
                    logger.info("Authentication successful!")
                    # Subscribe to assets after auth
                    self.subscribe_to_assets()
                else:
                    logger.error(f"Authentication failed: {data}")

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
                # Forward any other events to callback
                if self.on_message_callback:
                    self.on_message_callback(json.dumps([event, data]))

            # Connect to the Socket.IO server
            # Use the correct URL with Socket.IO path
            server_url = Credentials.WS_URL if hasattr(Credentials, 'WS_URL') else "https://qxbroker.com"
            # Ensure the URL uses https:// not wss:// for Socket.IO handshake
            if server_url.startswith('wss://'):
                server_url = server_url.replace('wss://', 'https://')
            if not server_url.startswith('http'):
                server_url = "https://" + server_url

            logger.info(f"Connecting to {server_url} with Socket.IO")
            self.sio.connect(server_url, transports=['websocket', 'polling'], headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                'Origin': 'https://qxbroker.com',
                'Referer': 'https://qxbroker.com/'
            })
            return True

        except Exception as e:
            logger.error(f"Connection error: {e}")
            return False

    def subscribe_to_assets(self):
        """Subscribe to assets after authentication"""
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
        """Keep connection alive (socketio handles this automatically)"""
        while self.connected:
            time.sleep(25)
            if self.sio and self.connected:
                # Socket.IO sends pings automatically, just check connection
                if not self.sio.connected:
                    logger.warning("Socket.IO not connected, reconnecting...")
                    self.connect()
                    break

    def disconnect(self):
        if self.sio:
            self.sio.disconnect()
            self.connected = False
            self.authenticated = False
            logger.info("Disconnected")

    # Property to maintain compatibility with main.py
    @property
    def ws(self):
        return self.sio
