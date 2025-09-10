import asyncio
import pandas as pd
from strategies.trend_reversal import TrendReversalStrategy
from utils.logger import setup_logger

logger = setup_logger('strategy_engine')

class StrategyEngine:
    def __init__(self, data_processor):
        self.data_processor = data_processor
        self.strategies = {}
        self.signals = []
        self.max_signals_history = 100
        
        # Initialize strategies
        self._initialize_strategies()
    
    def _initialize_strategies(self):
        # Trend Reversal Strategy for 5m timeframe
        self.strategies['trend_reversal_5m'] = TrendReversalStrategy(timeframe='5m')
        
        # Add more strategies here as needed
        # self.strategies['trend_following_1m'] = TrendFollowingStrategy(timeframe='1m')
    
    async def process_data(self, message_data):
        """Process incoming data and run strategies"""
        if message_data.get('type') == 'ohlc_update':
            asset = message_data['asset']
            timeframe = message_data['timeframe']
            data = message_data['data']
            
            # Run appropriate strategy based on timeframe
            if timeframe == '5m':
                signal = await self._run_strategy('trend_reversal_5m', asset, timeframe, data)
                if signal and signal['signal'] != 'hold':
                    self._store_signal(signal)
                    return signal
            
        return None
    
    async def _run_strategy(self, strategy_name, asset, timeframe, data):
        """Run a specific strategy"""
        if strategy_name in self.strategies:
            try:
                strategy = self.strategies[strategy_name]
                signal = strategy.analyze(data)
                
                if signal['signal'] != 'hold':
                    signal.update({
                        'asset': asset,
                        'timeframe': timeframe,
                        'strategy': strategy_name,
                        'timestamp': pd.Timestamp.now()
                    })
                    logger.info(f"Signal generated: {signal}")
                    return signal
                    
            except Exception as e:
                logger.error(f"Error running strategy {strategy_name}: {e}")
        
        return None
    
    def _store_signal(self, signal):
        """Store signal in history"""
        self.signals.append(signal)
        if len(self.signals) > self.max_signals_history:
            self.signals = self.signals[-self.max_signals_history:]
    
    def get_recent_signals(self, count=10):
        """Get recent signals"""
        return self.signals[-count:] if self.signals else []
    
    def get_signals_by_asset(self, asset):
        """Get signals for a specific asset"""
        return [s for s in self.signals if s.get('asset') == asset]
