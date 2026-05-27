# ============================================
# TRADIR AI - SMART MONEY ENGINE
# ============================================

def detect_fvg(candles):
    bullish_fvg, bearish_fvg = [], []
    for i in range(1, len(candles) - 1):
        p = candles[i-1]; n = candles[i+1]
        if p["high"] < n["low"]:
            gap = n["low"] - p["high"]
            bullish_fvg.append({
                "index": i, "top": round(n["low"], 5), "bottom": round(p["high"], 5),
                "gap_size": round(gap, 5), "type": "bullish"
            })
        if p["low"] > n["high"]:
            gap = p["low"] - n["high"]
            bearish_fvg.append({
                "index": i, "top": round(p["low"], 5), "bottom": round(n["high"], 5),
                "gap_size": round(gap, 5), "type": "bearish"
            })
    return bullish_fvg, bearish_fvg


def detect_order_blocks(candles):
    bullish_obs, bearish_obs = [], []
    for i in range(2, len(candles) - 1):
        cur  = candles[i]
        nxt  = candles[i+1]
        prev = candles[i-1]
        # Bullish OB: bearish candle followed by strong bullish
        if (cur["close"] < cur["open"] and
            nxt["close"] > nxt["open"] and
            nxt["close"] > cur["high"] and
            abs(nxt["close"] - nxt["open"]) > abs(cur["close"] - cur["open"])):
            bullish_obs.append({
                "index": i, "high": round(cur["high"], 5),
                "low": round(cur["low"], 5), "type": "bullish_ob"
            })
        # Bearish OB: bullish candle followed by strong bearish
        if (cur["close"] > cur["open"] and
            nxt["close"] < nxt["open"] and
            nxt["close"] < cur["low"] and
            abs(nxt["close"] - nxt["open"]) > abs(cur["close"] - cur["open"])):
            bearish_obs.append({
                "index": i, "high": round(cur["high"], 5),
                "low": round(cur["low"], 5), "type": "bearish_ob"
            })
    return bullish_obs[-5:], bearish_obs[-5:]


def detect_breaker_blocks(candles, bullish_obs, bearish_obs):
    """OBs that were broken → become breaker blocks (opposite direction)"""
    breakers = []
    last_close = candles[-1]["close"]
    for ob in bullish_obs:
        if last_close < ob["low"]:
            breakers.append({"type": "bearish_breaker", "high": ob["high"], "low": ob["low"]})
    for ob in bearish_obs:
        if last_close > ob["high"]:
            breakers.append({"type": "bullish_breaker", "high": ob["high"], "low": ob["low"]})
    return breakers


def detect_mitigation_block(candles):
    """Price returning to OB area"""
    if len(candles) < 10:
        return None
    recent = candles[-10:]
    # Simple: check if price revisits a previous significant level
    closes = [c["close"] for c in recent]
    if len(closes) < 5:
        return None
    mid = closes[len(closes)//2]
    last = closes[-1]
    if abs(last - mid) / mid < 0.0003:
        return {"type": "mitigation", "price": round(last, 5)}
    return None


def detect_institutional_candle(candles):
    last = candles[-1]
    body = abs(last["close"] - last["open"])
    rng  = last["high"] - last["low"]
    if rng == 0:
        return None
    # Strong body ratio + above-average size
    body_ratio = body / rng
    avg_body = sum(abs(c["close"] - c["open"]) for c in candles[-20:]) / 20
    if body_ratio >= 0.68 and body >= avg_body * 1.0:
        typ = "bullish_institutional" if last["close"] > last["open"] else "bearish_institutional"
        return {
            "type": typ,
            "body_ratio": round(body_ratio * 100, 1),
            "size_vs_avg": round(body / avg_body, 2)
        }
    return None


def detect_imbalances(candles):
    """Detect price imbalances (gaps between candles)"""
    imbalances = []
    for i in range(1, len(candles)):
        prev = candles[i-1]; cur = candles[i]
        gap_up   = cur["low"] - prev["high"]
        gap_down = prev["low"] - cur["high"]
        if gap_up > 0.0001:
            imbalances.append({"type": "bullish_imbalance", "top": round(cur["low"],5), "bottom": round(prev["high"],5)})
        if gap_down > 0.0001:
            imbalances.append({"type": "bearish_imbalance", "top": round(prev["low"],5), "bottom": round(cur["high"],5)})
    return imbalances[-3:]


def analyze_smart_money(candles):
    bullish_fvg, bearish_fvg = detect_fvg(candles)
    bullish_obs, bearish_obs = detect_order_blocks(candles)
    breakers   = detect_breaker_blocks(candles, bullish_obs, bearish_obs)
    mitigation = detect_mitigation_block(candles)
    inst_candle = detect_institutional_candle(candles)
    imbalances = detect_imbalances(candles)
    return {
        "bullish_fvg": bullish_fvg[-3:],
        "bearish_fvg": bearish_fvg[-3:],
        "bullish_order_blocks": bullish_obs,
        "bearish_order_blocks": bearish_obs,
        "breaker_blocks": breakers,
        "mitigation_block": mitigation,
        "institutional_candle": inst_candle,
        "imbalances": imbalances,
        "total_bullish_fvg": len(bullish_fvg),
        "total_bearish_fvg": len(bearish_fvg),
        "total_bullish_obs": len(bullish_obs),
        "total_bearish_obs": len(bearish_obs),
    }
