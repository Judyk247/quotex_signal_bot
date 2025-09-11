import asyncio
import websockets
import json
import os
from config.credentials import Credentials

async def test_auth():
    try:
        print("Testing Quotex authentication...")
        print(f"Session ID: {Credentials.SESSION_ID[:20]}...")
        print(f"Is Demo: {Credentials.IS_DEMO}")
        
        async with websockets.connect(Credentials.WS_URL) as ws:
            print("✓ WebSocket connected")
            
            # Handshake
            await ws.send('0{"sid":"test","upgrades":[],"pingInterval":25000,"pingTimeout":5000}')
            await ws.send('40')
            
            # Authorization
            auth_data = {
                "session": Credentials.SESSION_ID,
                "isDemo": Credentials.IS_DEMO,
                "tournamentId": Credentials.TOURNAMENT_ID
            }
            await ws.send(f'42["authorization",{json.dumps(auth_data)}]')
            
            # Get response
            response = await ws.recv()
            print(f"Response: {response}")
            
            if "unauthorized" in response.lower():
                print("❌ Authentication failed!")
                return False
            else:
                print("✓ Authentication successful!")
                return True
                
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_auth())
