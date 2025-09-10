# Trading settings
TRADING_SETTINGS = {
    'timeframes': ['1m', '2m', '3m', '5m'],
    'assets': [
        'EURUSD', 'EURUSD_otc', 'GBPUSD', 'GBPUSD_otc', 
        'USDJPY', 'USDJPY_otc', 'AUDUSD', 'AUDUSD_otc',
        'USDCAD', 'USDCAD_otc', 'USDCHF', 'USDCHF_otc',
        'BTCUSD_otc', 'ETHUSD_otc', 'XAUUSD', 'XAUUSD_otc'
    ],
    'max_concurrent_trades': 3,
    'risk_per_trade': 2.0,  # 2% of account per trade
    'stop_loss_pips': 20,
    'take_profit_pips': 40
}

# Strategy settings
STRATEGY_SETTINGS = {
    'trend_reversal': {
        'timeframe': '5m',
        'enabled': True,
        'min_confidence': 70
    },
    'trend_following': {
        'timeframes': ['1m', '2m', '3m'],
        'enabled': True,
        'min_confidence': 65
    }
}
