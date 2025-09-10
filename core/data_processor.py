import pandas as pd
import numpy as np
import json
import logging
from utils.logger import setup_logger

logger = setup_logger('data_processor')

class DataProcessor:
    def __init__(self):
        self.ohlc_data = {}
        self.instruments = {}
    
    def process_message(self, message):
        try:
            if message.startswith('0'):
                return self._process_handshake(message)
            elif message.startswith('40'):
                return self._process_connection_ack(message)
            elif message.startswith('42'):
                return self._process_data_message(message)
            elif message.startswith('2'):
                return self._process_pong(message)
            else:
                logger.warning(f"Unknown message format: {message}")
                return None
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return None
    
    def _process_handshake(self, message):
        try:
            data = json.loads(message[1:])
            return {'type': 'handshake', 'data': data}
        except:
            return {'type': 'handshake', 'raw': message}
    
    def _process_connection_ack(self, message):
        return {'type': 'connection_ack'}
    
    def _process_pong(self, message):
        return {'type': 'pong'}
    
    def _process_data_message(self, message):
        try:
            # Extract JSON part from the message
            json_str = message[2:]
            data = json.loads(json_str)
            
            if isinstance(data, list) and len(data) > 0:
                event_type = data[0]
                event_data = data[1] if len(data) > 1 else {}
                
                if event_type == 'instruments/list':
                    return self._process_instruments_list(event_data)
                elif event_type == 'instruments/update':
                    return self._process_instruments_update(event_data)
                elif event_type == 'tick':
                    return self._process_tick_data(event_data)
                elif event_type == 's_authorization':
                    return self._process_authorization(event_data)
                elif event_type == 'balance/list':
                    return self._process_balance(event_data)
                else:
                    return {'type': event_type, 'data': event_data}
            
            return {'type': 'unknown', 'data': data}
        except Exception as e:
            logger.error(f"Error parsing data message: {e}")
            return None
    
    def _process_instruments_list(self, data):
        self.instruments = {}
        for instrument in data:
            if isinstance(instrument, list) and len(instrument) > 1:
                instrument_id = instrument[0]
                instrument_name = instrument[2] if len(instrument) > 2 else f"Instrument_{instrument_id}"
                self.instruments[instrument_id] = {
                    'name': instrument_name,
                    'type': instrument[3] if len(instrument) > 3 else 'unknown',
                    'digits': instrument[4] if len(instrument) > 4 else 5
                }
        return {'type': 'instruments_list', 'data': self.instruments}
    
    def _process_instruments_update(self, data):
        if 'asset' in data and 'period' in data:
            asset = data['asset']
            timeframe = self._seconds_to_timeframe(data['period'])
            
            if 'candles' in data:
                candles = data['candles']
                if asset not in self.ohlc_data:
                    self.ohlc_data[asset] = {}
                
                if timeframe not in self.ohlc_data[asset]:
                    self.ohlc_data[asset][timeframe] = pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                
                new_data = []
                for candle in candles:
                    if isinstance(candle, list) and len(candle) >= 5:
                        new_data.append({
                            'timestamp': candle[0],
                            'open': candle[1],
                            'high': candle[2],
                            'low': candle[3],
                            'close': candle[4],
                            'volume': candle[5] if len(candle) > 5 else 0
                        })
                
                if new_data:
                    new_df = pd.DataFrame(new_data)
                    self.ohlc_data[asset][timeframe] = pd.concat([self.ohlc_data[asset][timeframe], new_df]).drop_duplicates('timestamp').sort_values('timestamp')
                    
                    return {
                        'type': 'ohlc_update',
                        'asset': asset,
                        'timeframe': timeframe,
                        'data': new_df.tail(50)  # Return last 50 candles
                    }
        
        return None
    
    def _process_tick_data(self, data):
        return {'type': 'tick', 'data': data}
    
    def _process_authorization(self, data):
        return {'type': 'authorization', 'data': data}
    
    def _process_balance(self, data):
        return {'type': 'balance', 'data': data}
    
    def _seconds_to_timeframe(self, seconds):
        if seconds == 60: return '1m'
        if seconds == 120: return '2m'
        if seconds == 180: return '3m'
        if seconds == 300: return '5m'
        return f"{seconds}s"
    
    def get_ohlc_data(self, asset, timeframe, count=100):
        if asset in self.ohlc_data and timeframe in self.ohlc_data[asset]:
            return self.ohlc_data[asset][timeframe].tail(count)
        return None
