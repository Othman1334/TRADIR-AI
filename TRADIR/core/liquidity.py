# ============================================
# TRADIR AI - LIQUIDITY ENGINE
# ============================================

def detect_equal_highs(candles, tolerance=0.0002):
    eq = []
    for i in range(len(candles) - 1):
        if abs(candles[i]["high"] - candles[i+1]["high"]) <= tolerance:
            eq.append({"index_1": i, "index_2": i+1, "price": candles[i]["high"]})
    return eq


def detect_equal_lows(candles, tolerance=0.0002):
    eq = []
    for i in range(len(candles) - 1):
        if abs(candles[i]["low"] - candles[i+1]["low"]) <= tolerance:
            eq.append({"index_1": i, "index_2": i+1, "price": candles[i]["low"]})
    return eq


def detect_liquidity_sweep(candles):
    if len(candles) < 5:
        return None
    last = candles[-1]
    prev = candles[-2]
    # Check last 10 candles for swing high/low
    recent = candles[-11:-1]
    swing_high = max(c["high"] for c in recent)
    swing_low  = min(c["low"]  for c in recent)

    if last["high"] > swing_high and last["close"] < swing_high:
        return {"type": "bullish_sweep", "price": round(last["high"], 5),
                "level": round(swing_high, 5), "description": "Swept sell-side liquidity"}

    if last["low"] < swing_low and last["close"] > swing_low:
        return {"type": "bearish_sweep", "price": round(last["low"], 5),
                "level": round(swing_low, 5), "description": "Swept buy-side liquidity"}
    return None


def detect_stop_hunt(candles):
    if len(candles) < 10:
        return False
    last = candles[-1]
    recent = candles[-10:-1]
    swing_high = max(c["high"] for c in recent)
    swing_low  = min(c["low"]  for c in recent)
    wick_up   = last["high"] - max(last["open"], last["close"])
    wick_down = min(last["open"], last["close"]) - last["low"]
    body      = abs(last["close"] - last["open"])
    if last["high"] > swing_high and wick_up > body * 1.5:
        return {"direction": "bearish", "description": "Bearish stop hunt above highs"}
    if last["low"] < swing_low and wick_down > body * 1.5:
        return {"direction": "bullish", "description": "Bullish stop hunt below lows"}
    return False


def detect_fake_breakout(candles):
    if len(candles) < 6:
        return False
    last = candles[-1]
    recent = candles[-6:-1]
    highs = [c["high"] for c in recent]
    lows  = [c["low"]  for c in recent]
    if last["high"] > max(highs) and last["close"] < max(highs):
        return {"direction": "bearish", "description": "Fake breakout above resistance"}
    if last["low"] < min(lows) and last["close"] > min(lows):
        return {"direction": "bullish", "description": "Fake breakout below support"}
    return False


def detect_inducement(candles):
    if len(candles) < 8:
        return None
    recent = candles[-8:]
    highs = [c["high"] for c in recent[:-1]]
    lows  = [c["low"]  for c in recent[:-1]]
    last  = recent[-1]
    # Small wick that baits traders
    wick_up   = last["high"] - max(last["open"], last["close"])
    wick_down = min(last["open"], last["close"]) - last["low"]
    avg_range = sum(c["high"] - c["low"] for c in recent[:-1]) / 7
    if wick_up > avg_range * 0.6 and last["close"] < last["open"]:
        return {"type": "bearish_inducement", "description": "Upper wick inducement"}
    if wick_down > avg_range * 0.6 and last["close"] > last["open"]:
        return {"type": "bullish_inducement", "description": "Lower wick inducement"}
    return None


def analyze_liquidity(candles):
    eq_highs = detect_equal_highs(candles[-50:])
    eq_lows  = detect_equal_lows(candles[-50:])
    sweep    = detect_liquidity_sweep(candles)
    stop_hunt = detect_stop_hunt(candles)
    fake_bo  = detect_fake_breakout(candles)
    inducement = detect_inducement(candles)
    return {
        "equal_highs": eq_highs[-3:],
        "equal_lows":  eq_lows[-3:],
        "liquidity_sweep": sweep,
        "stop_hunt": stop_hunt,
        "fake_breakout": fake_bo,
        "inducement": inducement,
        "total_equal_highs": len(eq_highs),
        "total_equal_lows":  len(eq_lows),
    }
