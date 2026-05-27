# ============================================
# TRADIR AI - SIGNAL ENGINE v5
# دائماً يعطي إشارة — مع تصنيف المخاطرة
# ============================================


def determine_entry_type(liquidity):
    if liquidity["liquidity_sweep"]:  return "دخول بعد السحب"
    if liquidity["stop_hunt"]:        return "دخول بعد صيد السيولة"
    if liquidity["fake_breakout"]:    return "دخول كسر وهمي"
    return "دخول فوري"


def determine_direction_strict(structure, smart_money, liquidity):
    """شروط قوية → مخاطرة منخفضة"""
    trend   = structure["trend"]
    bos     = structure["bos"]
    bos_dir = structure["bos_direction"]
    inst    = smart_money["institutional_candle"]
    sweep   = liquidity["liquidity_sweep"]
    bull_sm = smart_money["total_bullish_fvg"] > 0 or smart_money["total_bullish_obs"] > 0
    bear_sm = smart_money["total_bearish_fvg"] > 0 or smart_money["total_bearish_obs"] > 0

    # CALL - شروط قوية
    if trend == "bullish":
        if bos and bos_dir == "bullish" and inst and inst["type"] == "bullish_institutional" and bull_sm:
            return "CALL"
        if bos and bos_dir == "bullish" and inst and inst["type"] == "bullish_institutional":
            return "CALL"
        if bos and bos_dir == "bullish" and bull_sm:
            return "CALL"
        if inst and inst["type"] == "bullish_institutional" and bull_sm:
            return "CALL"
        if sweep and sweep["type"] == "bearish_sweep" and bull_sm:
            return "CALL"

    # PUT - شروط قوية
    if trend == "bearish":
        if bos and bos_dir == "bearish" and inst and inst["type"] == "bearish_institutional" and bear_sm:
            return "PUT"
        if bos and bos_dir == "bearish" and inst and inst["type"] == "bearish_institutional":
            return "PUT"
        if bos and bos_dir == "bearish" and bear_sm:
            return "PUT"
        if inst and inst["type"] == "bearish_institutional" and bear_sm:
            return "PUT"
        if sweep and sweep["type"] == "bullish_sweep" and bear_sm:
            return "PUT"

    return None


def determine_direction_medium(structure, smart_money, liquidity):
    """شروط متوسطة → مخاطرة متوسطة"""
    trend   = structure["trend"]
    bos     = structure["bos"]
    bos_dir = structure["bos_direction"]
    inst    = smart_money["institutional_candle"]
    sweep   = liquidity["liquidity_sweep"]
    bull_sm = smart_money["total_bullish_fvg"] > 0 or smart_money["total_bullish_obs"] > 0
    bear_sm = smart_money["total_bearish_fvg"] > 0 or smart_money["total_bearish_obs"] > 0

    # CALL - شرط أو اثنين
    if trend == "bullish":
        if bos and bos_dir == "bullish":    return "CALL"
        if inst and inst["type"] == "bullish_institutional": return "CALL"
        if bull_sm and structure["hh"] >= 1: return "CALL"

    # PUT
    if trend == "bearish":
        if bos and bos_dir == "bearish":    return "PUT"
        if inst and inst["type"] == "bearish_institutional": return "PUT"
        if bear_sm and structure["ll"] >= 1: return "PUT"

    return None


def determine_direction_weak(structure, smart_money, liquidity):
    """شرط واحد فقط → مخاطرة عالية"""
    trend   = structure["trend"]
    bull_sm = smart_money["total_bullish_fvg"] > 0 or smart_money["total_bullish_obs"] > 0
    bear_sm = smart_money["total_bearish_fvg"] > 0 or smart_money["total_bearish_obs"] > 0
    sweep   = liquidity["liquidity_sweep"]
    inst    = smart_money["institutional_candle"]

    # الاتجاه وحده يكفي للإشارة الضعيفة
    if trend == "bullish":
        return "CALL"
    if trend == "bearish":
        return "PUT"

    # تذبذب - نحكم بالسمارت موني
    if bull_sm and not bear_sm:
        return "CALL"
    if bear_sm and not bull_sm:
        return "PUT"

    # آخر حل: نظر في آخر شمعة
    return None


def build_weak_reasons(structure, smart_money, liquidity, direction):
    """أسباب للإشارات الضعيفة"""
    reasons = []
    trend = structure["trend"]

    if trend == "bullish":
        reasons.append("الاتجاه العام صاعد")
    elif trend == "bearish":
        reasons.append("الاتجاه العام هابط")
    else:
        reasons.append("⚠️ السوق في تذبذب")

    if structure["hh"] > 0:
        reasons.append(f"قمم صاعدة HH×{structure['hh']}")
    if structure["ll"] > 0:
        reasons.append(f"قيعان هابطة LL×{structure['ll']}")

    fvg_bull = smart_money["total_bullish_fvg"]
    fvg_bear = smart_money["total_bearish_fvg"]
    if direction == "CALL" and fvg_bull > 0:
        reasons.append(f"FVG صاعد ×{fvg_bull}")
    if direction == "PUT" and fvg_bear > 0:
        reasons.append(f"FVG هابط ×{fvg_bear}")

    sweep = liquidity["liquidity_sweep"]
    if sweep:
        reasons.append(f"سحب سيولة عند {sweep.get('level','')}")

    reasons.append("⚠️ تنبيه: الشروط غير مكتملة — مخاطرة عالية")
    return reasons


def generate_signal(analysis):
    structure   = analysis["structure"]
    liquidity   = analysis["liquidity"]
    smart_money = analysis["smart_money"]
    confidence  = analysis["confidence"]
    reasons     = analysis["reasons"]
    entry_type  = determine_entry_type(liquidity)

    # ── المستوى 1: شروط قوية → مخاطرة منخفضة ──────────────
    if confidence >= 72 and not structure["choch"]:
        direction = determine_direction_strict(structure, smart_money, liquidity)
        if direction:
            return {
                "signal":     direction,
                "entry_type": entry_type,
                "expiry":     "دقيقتان",
                "confidence": confidence,
                "risk":       "LOW" if confidence >= 82 else "MEDIUM",
                "risk_level": 1,
                "reasons":    reasons,
                "alert":      True,
                "warning":    False
            }

    # ── المستوى 2: شروط متوسطة → مخاطرة متوسطة ──────────────
    if not structure["choch"] and structure["trend"] != "neutral":
        direction = determine_direction_medium(structure, smart_money, liquidity)
        if direction:
            med_reasons = reasons if reasons else [f"اتجاه {structure['trend']} مع تأكيد جزئي"]
            med_reasons = med_reasons + ["⚠️ الشروط جزئية — تحقق من الشارت"]
            return {
                "signal":     direction,
                "entry_type": entry_type,
                "expiry":     "دقيقتان",
                "confidence": min(confidence, 74),
                "risk":       "MEDIUM",
                "risk_level": 2,
                "reasons":    med_reasons,
                "alert":      True,
                "warning":    True
            }

    # ── المستوى 3: أي إشارة — مخاطرة عالية ──────────────────
    direction = determine_direction_weak(structure, smart_money, liquidity)
    if direction:
        weak_reasons = build_weak_reasons(structure, smart_money, liquidity, direction)
        return {
            "signal":     direction,
            "entry_type": "دخول احتياطي",
            "expiry":     "دقيقتان",
            "confidence": max(min(confidence, 60), 35),
            "risk":       "HIGH",
            "risk_level": 3,
            "reasons":    weak_reasons,
            "alert":      False,   # لا صوت للإشارات الضعيفة
            "warning":    True
        }

    # ── Fallback مطلق: استناداً للشمعة الأخيرة فقط ──────────
    # هذا لا يُمكن أن يحدث مع 500 شمعة حقيقية لكن للأمان
    return {
        "signal":     "CALL",
        "entry_type": "دخول احتياطي",
        "expiry":     "دقيقتان",
        "confidence": 30,
        "risk":       "HIGH",
        "risk_level": 3,
        "reasons":    ["⚠️ بيانات غير كافية للتحليل — تجنب هذه الصفقة"],
        "alert":      False,
        "warning":    True
    }
