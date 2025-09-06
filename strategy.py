import numpy as np
import pandas as pd

# ----------------- EMA ----------------- #
def calculate_ema(prices, period):
    emas = []
    k = 2 / (period + 1)
    for i, price in enumerate(prices):
        if i == 0:
            emas.append(price)
        else:
            ema = price * k + emas[-1] * (1 - k)
            emas.append(ema)
    return emas

# ----------------- Heikin Ashi ----------------- #
def heikin_ashi(df):
    ha_df = df.copy()
    ha_df['close'] = (df['open'] + df['high'] + df['low'] + df['close']) / 4
    ha_df['open'] = (df['open'].shift(1) + df['close'].shift(1)) / 2
    ha_df.iloc[0, ha_df.columns.get_loc('open')] = df['open'].iloc[0]
    ha_df['high'] = ha_df[['open', 'close', 'high']].max(axis=1)
    ha_df['low'] = ha_df[['open', 'close', 'low']].min(axis=1)
    return ha_df

# ----------------- ATR ----------------- #
def calculate_atr(df, period=14):
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift(1))
    low_close = np.abs(df['low'] - df['close'].shift(1))
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()
    return atr

# ----------------- Alligator ----------------- #
def calculate_alligator(df, jaw=13, teeth=8, lips=5):
    median_price = (df['high'] + df['low']) / 2
    jaw_line = median_price.rolling(jaw).mean()
    teeth_line = median_price.rolling(teeth).mean()
    lips_line = median_price.rolling(lips).mean()
    return jaw_line, teeth_line, lips_line

# ----------------- Stochastic ----------------- #
def stochastic_oscillator(df, k_period=14, d_period=3):
    low_min = df['low'].rolling(k_period).min()
    high_max = df['high'].rolling(k_period).max()
    k = 100 * (df['close'] - low_min) / (high_max - low_min)
    d = k.rolling(d_period).mean()
    return k, d

# ----------------- Candlestick Patterns ----------------- #
def detect_bullish_engulfing(df):
    if len(df) < 2:
        return False
    prev, last = df.iloc[-2], df.iloc[-1]
    return last['close'] > last['open'] and prev['close'] < prev['open'] \
           and last['close'] > prev['open'] and last['open'] < prev['close']

def detect_bearish_engulfing(df):
    if len(df) < 2:
        return False
    prev, last = df.iloc[-2], df.iloc[-1]
    return last['close'] < last['open'] and prev['close'] > prev['open'] \
           and last['open'] > prev['close'] and last['close'] < prev['open']

# ----------------- Multi-Timeframe Confirmation ----------------- #
def multi_timeframe_confirmation(lower_signal, mid_df, high_df):
    if lower_signal is None:
        return None

    def get_bias(df):
        if df is None or len(df) < 50:
            return None, 0
        ha = heikin_ashi(df)
        ema = ha['close'].ewm(span=100, adjust=False).mean()
        ema_slope = ema.iloc[-1] - ema.iloc[-5]
        bullish = ha['close'].mean() > ha['open'].mean()
        bearish = ha['close'].mean() < ha['open'].mean()
        return ("bullish" if ema_slope > 0 and bullish else
                "bearish" if ema_slope < 0 and bearish else None), ema_slope

    mid_bias, _ = get_bias(mid_df)
    high_bias, _ = get_bias(high_df)

    if lower_signal == "buy" and mid_bias == "bullish" and high_bias != "bearish":
        return "buy"
    elif lower_signal == "sell" and mid_bias == "bearish" and high_bias != "bullish":
        return "sell"
    else:
        return None

# ----------------- Main Analyzer ----------------- #
def analyze_candles(df, mid_df=None, high_df=None, debug=False):
    if len(df) < 50:
        if debug:
            print("Not enough candles:", len(df))
        return {"signal": "hold", "confidence": 0}

    ha_df = heikin_ashi(df)
    atr = calculate_atr(df)
    jaw, teeth, lips = calculate_alligator(ha_df)
    k, d = stochastic_oscillator(ha_df)
    ema = ha_df['close'].ewm(span=150, adjust=False).mean()

    last_idx = -1
    recent = ha_df.iloc[-30:]
    bullish_bias = recent['close'].mean() > recent['open'].mean()
    bearish_bias = recent['close'].mean() < recent['open'].mean()
    bullish_pattern = detect_bullish_engulfing(recent)
    bearish_pattern = detect_bearish_engulfing(recent)
    ema_slope = ema.iloc[-1] - ema.iloc[-5]
    min_atr = atr.iloc[last_idx] > df['close'].mean() * 0.001
    last_candle = ha_df.iloc[last_idx]
    momentum_bull = (ha_df['close'].iloc[-3:] > ha_df['open'].iloc[-3:]).sum() >= 2
    momentum_bear = (ha_df['close'].iloc[-3:] < ha_df['open'].iloc[-3:]).sum() >= 2

    # --- Scoring ---
    score = 0
    total_checks = 10

    # Buy
    if ha_df['close'].iloc[last_idx] > jaw.iloc[last_idx]: score += 1
    if ha_df['close'].iloc[last_idx] > teeth.iloc[last_idx]: score += 1
    if ha_df['close'].iloc[last_idx] > lips.iloc[last_idx]: score += 1
    if k.iloc[last_idx] > d.iloc[last_idx]: score += 1
    if k.iloc[last_idx] < 30: score += 1
    if bullish_bias: score += 1
    if bullish_pattern: score += 1
    if atr.iloc[last_idx] > 0 and min_atr: score += 1
    if ema_slope > 0: score += 1
    if momentum_bull: score += 1
    buy_score = score

    # Sell
    score = 0
    if ha_df['close'].iloc[last_idx] < jaw.iloc[last_idx]: score += 1
    if ha_df['close'].iloc[last_idx] < teeth.iloc[last_idx]: score += 1
    if ha_df['close'].iloc[last_idx] < lips.iloc[last_idx]: score += 1
    if k.iloc[last_idx] < d.iloc[last_idx]: score += 1
    if k.iloc[last_idx] > 80: score += 1
    if bearish_bias: score += 1
    if bearish_pattern: score += 1
    if atr.iloc[last_idx] > 0 and min_atr: score += 1
    if ema_slope < 0: score += 1
    if momentum_bear: score += 1
    sell_score = score

    # Raw signal
    if buy_score >= sell_score and buy_score >= 6:
        raw_signal = "buy"
        confidence = int((buy_score / total_checks) * 100)
    elif sell_score > buy_score and sell_score >= 6:
        raw_signal = "sell"
        confidence = int((sell_score / total_checks) * 100)
    else:
        raw_signal, confidence = "hold", 0

    # Multi-timeframe confirmation
    confirmed = multi_timeframe_confirmation(raw_signal, mid_df, high_df)
    if confirmed is None:
        confirmed = "hold"
        confidence = 0

    if debug:
        print(f"[DEBUG] Raw: {raw_signal}, Confirmed: {confirmed}, Confidence: {confidence}")

    # Return signal suitable for dashboard/Telegram
    signal_map = {"buy": "Buy/Call", "sell": "Sell/Put", "hold": "Hold"}
    return {"signal": signal_map.get(confirmed, "Hold"), "confidence": confidence}
