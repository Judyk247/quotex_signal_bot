import signal
import sys
import threading
import time
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
        
    def initialize(self):
        """Initialize the trading bot"""
        logger.info("Initializing Quotex Trading Bot...")
        
        # Connect to WebSocket (synchronous now)
        connected = self.ws_client.connect()
        if not connected:
            logger.error("Failed to connect to WebSocket")
            return False
            
        # Wait a bit for authentication
        time.sleep(2)
        
        # Start keep-alive in background thread
        self.keep_alive_thread = threading.Thread(target=self.ws_client.keep_alive, daemon=True)
        self.keep_alive_thread.start()
        
        # Subscribe to assets
        for asset in TRADING_SETTINGS['assets']:
            for timeframe in TRADING_SETTINGS['timeframes']:
                self.ws_client.subscribe_to_assets()  # This now handles all subscriptions
                time.sleep(0.1)
        
        self.running = True
        logger.info("Trading bot initialized successfully")
        return True
    
    def run(self):
        """Main trading bot loop"""
        try:
            logger.info("Bot started. Waiting for messages...")
            
            # The new WebSocket client handles messages via callbacks
            # We just need to keep the main thread alive
            while self.running:
                time.sleep(1)
                
                # Check if still connected
                if not self.ws_client.connected:
                    logger.warning("WebSocket disconnected. Attempting reconnect...")
                    self.initialize()  # Reinitialize
                    
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
        finally:
            self.running = False
            self.ws_client.disconnect()
    
    def shutdown(self):
        """Graceful shutdown"""
        logger.info("Shutting down trading bot...")
        self.running = False
        self.ws_client.disconnect()

# Create bot instance
bot = QuotexTradingBot()

def run_bot():
    """Run the trading bot in background"""
    if bot.initialize():
        bot.run()

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
    bot.shutdown()

signal.signal(signal.SIGTERM, handle_shutdown)
signal.signal(signal.SIGINT, handle_shutdown)

# For WebSocket message processing - add this to your DataProcessor
def process_websocket_message(message):
    """Callback function for WebSocket messages"""
    try:
        processed_data = bot.data_processor.process_message(message)
        if processed_data:
            signal = bot.strategy_engine.process_data(processed_data)
            if signal and signal.get('signal') != 'hold':
                dashboard.add_signal(signal)
                logger.info(f"New trading signal: {signal}")
    except Exception as e:
        logger.error(f"Error processing message: {e}")

# Set the callback in the WebSocket client
bot.ws_client.on_message_callback = process_websocket_message
