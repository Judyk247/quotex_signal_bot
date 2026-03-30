import os
from dotenv import load_dotenv

load_dotenv()

class Credentials:
    EMAIL = os.getenv('QUOTEX_EMAIL')
    PASSWORD = os.getenv('QUOTEX_PASSWORD')
    SESSION_ID = os.getenv('QUOTEX_SESSION_ID', '')  # optional, will auto-login if missing
    IS_DEMO = int(os.getenv('QUOTEX_IS_DEMO', '0'))  # 0 = live, 1 = demo
    TOURNAMENT_ID = int(os.getenv('QUOTEX_TOURNAMENT_ID', '0'))
    WS_URL = os.getenv('QUOTEX_WS_URL', 'https://qxbroker.com')  # Socket.IO endpoint

    @classmethod
    def validate(cls):
        if not cls.EMAIL or not cls.PASSWORD:
            if not cls.SESSION_ID:
                raise ValueError("Either QUOTEX_EMAIL/PASSWORD or QUOTEX_SESSION_ID must be set")
        # If email/password are present but no session, we'll login via HTTP
        return True
