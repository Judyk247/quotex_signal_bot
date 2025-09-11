import asyncio
import signal
import sys
import threading
from core.websocket_client import QuotexWebSocketClient
from core.data_processor import DataProcessor
from core.strategy_engine import StrategyEngine
from utils.logger import setup_logger
from config.settings import TRADING_SETTINGS
from dashboard.app import dashboard

print(f"Python version: {sys.version}")

logger = setup_logger('main')

class QuotexTradingBot:
    def __init__(self):
        self.ws_client = QuotexWebSocketClient()
        self.data_processor = DataProcessor()
        self.strategy_engine = StrategyEngine(self.data_processor)
        self.running = False
        
    async def initialize(self):
        """Initialize the trading bot"""
        logger.info("Initializing Quotex Trading Bot...")
        
        # Connect to WebSocket
        connected = await self.ws_client.connect()
        if not connected:
            logger.error("Failed to connect to WebSocket")
            return False
            
        # Subscribe to assets
        for asset in TRADING_SETTINGS['assets']:
            for timeframe in TRADING_SETTINGS['timeframes']:
                await self.ws_client.subscribe_to_asset(asset, timeframe)
                await asyncio.sleep(0.1)
        
        self.running = True
        logger.info("Trading bot initialized successfully")
        return True
    
    async def run(self):
        """Main trading bot loop"""
        try:
            # Start keep-alive task
            keep_alive_task = asyncio.create_task(self.ws_client.keep_alive())
            
            # Process incoming messages
            async for message in self.ws_client.receive():
                if not self.running:
                    break
                    
                processed_data = self.data_processor.process_message(message)
                
                if processed_data:
                    signal = await self.strategy_engine.process_data(processed_data)
                    
                    if signal and signal.get('signal') != 'hold':
                        dashboard.add_signal(signal)
                        logger.info(f"New trading signal: {signal}")
            
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

# Create bot instance
bot = QuotexTradingBot()

def run_bot():
    """Run the trading bot in background"""
    async def bot_main():
        if await bot.initialize():
            await bot.run()
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(bot_main())

# ===== RENDER DEPLOYMENT SETUP =====
# Import your Flask app from dashboard
from dashboard.app import app

# Export for Gunicorn - Render will automatically find this
application = app

# Start bot immediately when module loads (Production)
if not bot.running:
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    logger.info("Trading bot started in background thread")

# Clean shutdown handling for production
def handle_shutdown(signum, frame):
    """Handle graceful shutdown"""
    logger.info("Received shutdown signal")
    async def shutdown_async():
        await bot.shutdown()
    asyncio.run(shutdown_async())

signal.signal(signal.SIGTERM, handle_shutdown)
signal.signal(signal.SIGINT, handle_shutdown)
