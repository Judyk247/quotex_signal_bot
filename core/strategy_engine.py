import pandas as pd
from strategies.trend_reversal import TrendReversalStrategy
from strategies.trend_following import TrendFollowingStrategy
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
    
    def process_data(self, processed_data):
        """
        Process data and generate trading signals
        Returns: Signal dict or None
        """
        try:
            if not processed_data:
                return None
                
            data_type = processed_data.get('type')
            
            if data_type == 'tick':
                return self._process_tick_signal(processed_data)
                
            elif data_type == 'instrument_update':
                return self._process_ohlc_signal(processed_data)
                
            return None
            
        except Exception as e:
            logger.error(f"Error processing data: {e}")
            return None
    
    def _process_tick_signal(self, tick_data):
        """Process tick data for signals"""
        asset = tick_data.get('asset', '')
        price = tick_data.get('price', 0)
        
        logger.debug(f"Processing tick: {asset} = {price}")
        
        # For tick data, we might want to use different strategies
        # For now, return None as ticks are less reliable for our strategies
        return None
    
    def _process_ohlc_signal(self, ohlc_data):
        """Process OHLC data for signals using our strategies"""
        asset = ohlc_data.get('asset', '')
        candles = ohlc_data.get('candles', [])
        timeframe = ohlc_data.get('period', '5m')
        
        logger.debug(f"Processing OHLC: {asset} with {len(candles)} candles (TF: {timeframe})")
        
        # Convert candles to DataFrame for our strategies
        if candles and len(candles) > 0:
            df = self._candles_to_dataframe(candles)
            
            # Run appropriate strategy based on timeframe
            if timeframe == 300 or timeframe == '5m':  # 5 minutes
                signal = self.strategies['trend_reversal_5m'].analyze(df)
            elif timeframe == 60 or timeframe == '1m':  # 1 minute
                signal = self.strategies['trend_following_1m'].analyze(df)
            elif timeframe == 120 or timeframe == '2m':  # 2 minutes
                signal = self.strategies['trend_following_2m'].analyze(df)
            elif timeframe == 180 or timeframe == '3m':  # 3 minutes
                signal = self.strategies['trend_following_3m'].analyze(df)
            else:
                signal = {'signal': 'hold', 'confidence': 0}
            
            # Add asset and timeframe to signal
            if signal and signal['signal'] != 'hold':
                signal['asset'] = asset
                signal['timeframe'] = self._seconds_to_timeframe(timeframe)
                self._store_signal(signal)
                return signal
        
        return None
    
    def _candles_to_dataframe(self, candles):
        """Convert candles list to pandas DataFrame"""
        if not candles:
            return pd.DataFrame()
            
        # Assuming candles format: [timestamp, open, high, low, close, volume]
        df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
        df.set_index('timestamp', inplace=True)
        return df
    
    def _seconds_to_timeframe(self, seconds):
        """Convert seconds to timeframe string"""
        if seconds == 60: return '1m'
        if seconds == 120: return '2m'
        if seconds == 180: return '3m'
        if seconds == 300: return '5m'
        return f"{seconds}s"
    
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
