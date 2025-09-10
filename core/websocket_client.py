import websockets
import asyncio
import json
import logging
from config.credentials import Credentials
from utils.logger import setup_logger

logger = setup_logger('websocket_client')

class QuotexWebSocketClient:
    def __init__(self):
        self.ws = None
        self.connected = False
        self.ping_interval = 25000
        self.ping_timeout = 5000
        self.session_id = None
        
    async def connect(self):
        try:
            self.ws = await websockets.connect(Credentials.WS_URL)
            self.connected = True
            logger.info("Connected to Quotex WebSocket")
            
            # Send initial handshake
            await self.send('0{"sid":"dPM2e_Q_YtY46okiLc8u","upgrades":[],"pingInterval":25000,"pingTimeout":5000}')
            await self.send('40')
            
            # Send authorization
            auth_data = {
                "session": Credentials.SESSION_ID,
                "isDemo": Credentials.IS_DEMO,
                "tournamentId": Credentials.TOURNAMENT_ID
            }
            await self.send(f'42["authorization",{json.dumps(auth_data)}]')
            
            # Request instruments list
            await self.send('451-["instruments/list",{"_placeholder":true,"num":0}]')
            
            return True
            
        except Exception as e:
            logger.error(f"Connection error: {e}")
            return False
    
    async def send(self, message):
        if self.ws and self.connected:
            try:
                await self.ws.send(message)
                logger.debug(f"Sent: {message}")
            except Exception as e:
                logger.error(f"Send error: {e}")
                self.connected = False
    
    async def receive(self):
        while self.connected:
            try:
                message = await self.ws.recv()
                logger.debug(f"Received: {message}")
                yield message
            except Exception as e:
                logger.error(f"Receive error: {e}")
                self.connected = False
                break
    
    async def keep_alive(self):
        while self.connected:
            try:
                await asyncio.sleep(self.ping_interval / 1000)
                await self.send('2')
            except Exception as e:
                logger.error(f"Keep alive error: {e}")
                self.connected = False
                break
    
    async def subscribe_to_asset(self, asset, timeframe):
        subscribe_msg = f'42["instruments/update",{{"asset":"{asset}","period":{self._timeframe_to_seconds(timeframe)}}}]'
        await self.send(subscribe_msg)
        logger.info(f"Subscribed to {asset} ({timeframe})")
    
    def _timeframe_to_seconds(self, timeframe):
        if timeframe == '1m': return 60
        if timeframe == '2m': return 120
        if timeframe == '3m': return 180
        if timeframe == '5m': return 300
        return 60
    
    async def disconnect(self):
        if self.ws:
            await self.ws.close()
            self.connected = False
            logger.info("Disconnected from WebSocket")
