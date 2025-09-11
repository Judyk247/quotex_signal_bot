import json
import logging
from utils.logger import setup_logger

logger = setup_logger('data_processor')

class DataProcessor:
    def __init__(self):
        self.message_buffer = []
        
    def process_message(self, message):
        """
        Process raw WebSocket messages
        Returns: Processed data or None if not relevant
        """
        try:
            if isinstance(message, bytes):
                message = message.decode('utf-8')
            
            # Log the message for debugging
            logger.debug(f"Processing message: {message[:100]}...")
            
            # Handle different message types
            if message.startswith('42['):
                # This is a data message
                try:
                    json_data = json.loads(message[2:])
                    if isinstance(json_data, list) and len(json_data) > 0:
                        message_type = json_data[0]
                        
                        if message_type == "tick":
                            tick_data = json_data[1] if len(json_data) > 1 else {}
                            return self._process_tick_data(tick_data)
                            
                        elif message_type == "instruments/update":
                            update_data = json_data[1] if len(json_data) > 1 else {}
                            return self._process_instrument_update(update_data)
                
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse JSON message: {message}")
                    return None
            
            return None
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return None
    
    def _process_tick_data(self, tick_data):
        """Process tick data messages"""
        if isinstance(tick_data, dict) and 'symbol' in tick_data:
            return {
                'type': 'tick',
                'asset': tick_data['symbol'],
                'price': tick_data.get('price'),
                'timestamp': tick_data.get('timestamp'),
                'raw_data': tick_data
            }
        return None
    
    def _process_instrument_update(self, update_data):
        """Process instrument update messages"""
        if isinstance(update_data, dict) and 'asset' in update_data:
            return {
                'type': 'instrument_update',
                'asset': update_data['asset'],
                'period': update_data.get('period'),
                'candles': update_data.get('candles', []),
                'raw_data': update_data
            }
        return None
