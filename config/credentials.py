import os
from dotenv import load_dotenv

load_dotenv()

class Credentials:
    EMAIL = os.getenv('QUOTEX_EMAIL')
    PASSWORD = os.getenv('QUOTEX_PASSWORD')
    SESSION_ID = os.getenv('QUOTEX_SESSION_ID', '')
    IS_DEMO = int(os.getenv('QUOTEX_IS_DEMO', '0'))
    TOURNAMENT_ID = int(os.getenv('QUOTEX_TOURNAMENT_ID', '0'))
    
    # Fix: if the env var is empty string, use default
    _ws_url = os.getenv('QUOTEX_WS_URL', '')
    WS_URL = _ws_url if _ws_url and _ws_url.strip() else 'https://ws2.qxbroker.com'

    @classmethod
    def validate(cls):
        if not cls.SESSION_ID and (not cls.EMAIL or not cls.PASSWORD):
            raise ValueError("Either QUOTEX_SESSION_ID or QUOTEX_EMAIL+PASSWORD must be set")
        return True
