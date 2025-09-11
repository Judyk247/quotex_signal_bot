import asyncio
import json
import signal
import sys
from datetime import datetime
from core.websocket_client import QuotexWebSocketClient
from core.data_processor import DataProcessor
from core.strategy_engine import StrategyEngine
from utils.logger import setup_logger
from config.settings import TRADING_SETTINGS
from dashboard.app import dashboard, run_dashboard
import threading
import sys
print(f"ACTUAL Python version: {sys.version}")

logger = setup_logger('main')

class QuotexTradingBot:
    def __init__(self):
        self.ws_client = QuotexWebSocketClient()
        self.data_processor = DataProcessor()
        self.strategy_engine = StrategyEngine(self.data_processor)
        self.running = False
        self.dashboard_thread = None
        
    async def initialize(self):
        """Initialize the trading bot"""
        logger.info("Initializing Quotex Trading Bot...")
        
        # Start dashboard in a separate thread
        self.start_dashboard()
        
        # Connect to WebSocket
        connected = await self.ws_client.connect()
        if not connected:
            logger.error("Failed to connect to WebSocket")
            return False
            
        # Subscribe to assets
        for asset in TRADING_SETTINGS['assets']:
            for timeframe in TRADING_SETTINGS['timeframes']:
                await self.ws_client.subscribe_to_asset(asset, timeframe)
                await asyncio.sleep(0.1)  # Small delay between subscriptions
        
        self.running = True
        logger.info("Trading bot initialized successfully")
        return True
    
    def start_dashboard(self):
        """Start the dashboard in a separate thread"""
        def run_dashboard_thread():
            try:
                from dashboard.app import run_dashboard
                run_dashboard()
            except Exception as e:
                logger.error(f"Dashboard error: {e}")
        
        self.dashboard_thread = threading.Thread(target=run_dashboard_thread, daemon=True)
        self.dashboard_thread.start()
        logger.info("Dashboard started on http://localhost:5000")
    
    async def run(self):
        """Main trading bot loop"""
        try:
            # Start keep-alive task
            keep_alive_task = asyncio.create_task(self.ws_client.keep_alive())
            
            # Process incoming messages
            async for message in self.ws_client.receive():
                if not self.running:
                    break
                    
                # Process the message
                processed_data = self.data_processor.process_message(message)
                
                if processed_data:
                    # Run strategies on the processed data
                    signal = await self.strategy_engine.process_data(processed_data)
                    
                    # Send signal to dashboard
                    if signal and signal.get('signal') != 'hold':
                        dashboard.add_signal(signal)
                        logger.info(f"New signal sent to dashboard: {signal}")
            
            # Cleanup
            keep_alive_task.cancel()
            await self.ws_client.disconnect()
            
        except asyncio.CancelledError:
            logger.info("Bot stopped by user")
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
        finally:
            self.running = False
    
    async def shutdown(self):
        """Graceful shutdown"""
        logger.info("Shutting down trading bot...")
        self.running = False
        await self.ws_client.disconnect()

async def main():
    """Main function"""
    bot = QuotexTradingBot()
    
    # Setup signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logger.info("Received shutdown signal")
        asyncio.create_task(bot.shutdown())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Initialize and run the bot
    if await bot.initialize():
        try:
            await bot.run()
        except Exception as e:
            logger.error(f"Fatal error: {e}")
    else:
        logger.error("Failed to initialize bot")
    
    logger.info("Trading bot stopped")

if __name__ == "__main__":
    # Check if credentials are set
    from config.credentials import Credentials
    if not Credentials.SESSION_ID:
        print("ERROR: SESSION_ID not found in environment variables or .env file")
        print("Please create a .env file with your Quotex credentials:")
        print("SESSION_ID=your_session_id_here")
        print("IS_DEMO=0")
        print("TOURNAMENT_ID=0")
        sys.exit(1)
    
    # Run the bot
    asyncio.run(main())
