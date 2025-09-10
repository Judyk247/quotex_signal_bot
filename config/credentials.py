import os
from dotenv import load_dotenv

load_dotenv()

class Credentials:
    SESSION_ID = os.getenv('SESSION_ID', '')
    IS_DEMO = int(os.getenv('IS_DEMO', 0))
    TOURNAMENT_ID = int(os.getenv('TOURNAMENT_ID', 0))
    WS_URL = os.getenv('WS_URL', 'wss://ws2.qxbroker.com/socket.io/?EIO=3&transport=websocket')
