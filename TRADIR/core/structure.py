# ============================================
# TRADIR AI - MARKET STRUCTURE ENGINE
# ============================================

def detect_swings(candles, left=2, right=2):
    swing_highs = []
    swing_lows = []
    for i in range(left, len(candles) - right):
        ch = candles[i]["high"]
        cl = candles[i]["low"]
        is_sh = all(candles[j]["high"] < ch for j in range(i-left, i+right+1) if j != i)
        is_sl = all(candles[j]["low"] > cl for j in range(i-left, i+right+1) if j != i)
        if is_sh:
            swing_highs.append({"index": i, "price": ch})
        if is_sl:
            swing_lows.append({"index": i, "price": cl})
    return swing_highs, swing_lows


def detect_market_structure(swing_highs, swing_lows):
    if len(swing_highs) < 2 or len(swing_lows) < 2:
        return "neutral", [], []

    highs = [s["price"] for s in swing_highs[-5:]]
    lows  = [s["price"] for s in swing_lows[-5:]]

    hh = sum(1 for i in range(1, len(highs)) if highs[i] > highs[i-1])
    hl = sum(1 for i in range(1, len(lows))  if lows[i]  > lows[i-1])
    ll = sum(1 for i in range(1, len(lows))  if lows[i]  < lows[i-1])
    lh = sum(1 for i in range(1, len(highs)) if highs[i] < highs[i-1])

    if hh >= 2 and hl >= 2:
        trend = "bullish"
    elif ll >= 2 and lh >= 2:
        trend = "bearish"
    else:
        trend = "neutral"

    return trend, swing_highs, swing_lows


def detect_bos(candles, swing_highs, swing_lows):
    if not swing_highs or not swing_lows:
        return False, None
    close = candles[-1]["close"]
    last_sh = swing_highs[-1]["price"]
    last_sl = swing_lows[-1]["price"]
    if close > last_sh:
        return True, "bullish"
    if close < last_sl:
        return True, "bearish"
    return False, None


def detect_choch(trend, bos_dir):
    if trend == "bullish" and bos_dir == "bearish":
        return True
    if trend == "bearish" and bos_dir == "bullish":
        return True
    return False


def calculate_strength(candles):
    last = candles[-1]
    body = abs(last["close"] - last["open"])
    rng  = last["high"] - last["low"]
    if rng == 0:
        return "weak", 0
    ratio = body / rng
    if ratio > 0.75:
        return "strong", round(ratio * 100, 1)
    if ratio > 0.45:
        return "medium", round(ratio * 100, 1)
    return "weak", round(ratio * 100, 1)


def analyze_structure(candles):
    sh, sl = detect_swings(candles)
    trend, sh, sl = detect_market_structure(sh, sl)
    bos, bos_dir = detect_bos(candles, sh, sl)
    choch = detect_choch(trend, bos_dir)
    strength, strength_pct = calculate_strength(candles)

    recent_highs = [s["price"] for s in sh[-5:]]
    recent_lows  = [s["price"] for s in sl[-5:]]

    hh = sum(1 for i in range(1, len(recent_highs)) if recent_highs[i] > recent_highs[i-1])
    hl = sum(1 for i in range(1, len(recent_lows))  if recent_lows[i]  > recent_lows[i-1])
    ll = sum(1 for i in range(1, len(recent_lows))  if recent_lows[i]  < recent_lows[i-1])
    lh = sum(1 for i in range(1, len(recent_highs)) if recent_highs[i] < recent_highs[i-1])

    return {
        "trend": trend,
        "bos": bos,
        "bos_direction": bos_dir,
        "choch": choch,
        "market_strength": strength,
        "strength_pct": strength_pct,
        "hh": hh, "hl": hl, "ll": ll, "lh": lh,
        "last_swing_high": sh[-1] if sh else None,
        "last_swing_low":  sl[-1] if sl else None,
        "total_swing_highs": len(sh),
        "total_swing_lows":  len(sl),
    }
