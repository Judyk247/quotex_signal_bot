import asyncio
import pandas as pd
from strategies.trend_reversal import TrendReversalStrategy
from strategies.trend_following import TrendFollowingStrategy  # Add this import
from utils.logger import setup_logger

logger = setup_logger('strategy_engine')

class StrategyEngine:
    def __init__(self, data_processor):
        self.data_processor = data_processor
        self.strategies = {}
        self.signals = []
        self.max_signals_history = 100
        
        # Initialize ALL strategies
        self._initialize_strategies()
    
    def _initialize_strategies(self):
        # Trend Reversal Strategy for 5m timeframe
        self.strategies['trend_reversal_5m'] = TrendReversalStrategy(timeframe='5m')
        
        # Trend Following Strategies for shorter timeframes
        self.strategies['trend_following_1m'] = TrendFollowingStrategy(timeframe='1m')
        self.strategies['trend_following_2m'] = TrendFollowingStrategy(timeframe='2m')
        self.strategies['trend_following_3m'] = TrendFollowingStrategy(timeframe='3m')
    
    async def process_data(self, message_data):
        """Process incoming data and run appropriate strategies"""
        if message_data.get('type') == 'ohlc_update':
            asset = message_data['asset']
            timeframe = message_data['timeframe']
            data = message_data['data']
            
            # Run appropriate strategy based on timeframe
            if timeframe == '5m':
                signal = await self._run_strategy('trend_reversal_5m', asset, timeframe, data)
            elif timeframe in ['1m', '2m', '3m']:
                strategy_name = f'trend_following_{timeframe}'
                signal = await self._run_strategy(strategy_name, asset, timeframe, data)
            else:
                signal = None
            
            if signal and signal['signal'] != 'hold':
                self._store_signal(signal)
                return signal
            
        return None
    
    # ... rest of the file remains the same
