# ============================================
# TRADIR AI - PROBABILITY ENGINE v5
# ============================================

AR = {
    "bull_str":   "هيكل سوق صاعد",
    "bear_str":   "هيكل سوق هابط",
    "bos_bull":   "كسر هيكل صاعد (BOS)",
    "bos_bear":   "كسر هيكل هابط (BOS)",
    "choch":      "⚠️ تغيير الشخصية (CHOCH)",
    "strong":     "شمعة قوية الجسم",
    "medium":     "شمعة متوسطة الجسم",
    "weak_body":  "شمعة ضعيفة الجسم",
    "hh_hl":      "قمم وقيعان صاعدة (HH/HL)",
    "ll_lh":      "قمم وقيعان هابطة (LL/LH)",
    "sweep":      "سحب سيولة",
    "stop_hunt":  "صيد وقف الخسارة",
    "fake_bo":    "كسر وهمي",
    "inducement": "إغراء تجاري",
    "eq_hi":      "قمم متساوية (سيولة)",
    "eq_lo":      "قيعان متساوية (سيولة)",
    "inst":       "شمعة مؤسسية قوية",
    "bull_fvg":   "فجوة قيمة عادلة صاعدة (FVG)",
    "bear_fvg":   "فجوة قيمة عادلة هابطة (FVG)",
    "bull_ob":    "بلوك طلب صاعد (OB)",
    "bear_ob":    "بلوك عرض هابط (OB)",
    "breaker":    "بلوك كسر نشط",
    "imbalance":  "خلل في الأسعار",
}


def score_structure(structure):
    score = 0; reasons = []
    trend = structure["trend"]
    if trend == "bullish":
        score += 20; reasons.append(AR["bull_str"])
    elif trend == "bearish":
        score += 20; reasons.append(AR["bear_str"])

    if structure["bos"]:
        score += 18
        reasons.append(AR["bos_bull"] if structure["bos_direction"]=="bullish" else AR["bos_bear"])

    if structure["choch"]:
        score -= 10; reasons.append(AR["choch"])
    else:
        score += 8

    st = structure["market_strength"]
    pct = structure["strength_pct"]
    if st == "strong":
        score += 12; reasons.append(f"{AR['strong']} ({pct}%)")
    elif st == "medium":
        score += 6;  reasons.append(f"{AR['medium']} ({pct}%)")
    else:
        reasons.append(f"{AR['weak_body']} ({pct}%)")

    hh=structure.get("hh",0); hl=structure.get("hl",0)
    ll=structure.get("ll",0); lh=structure.get("lh",0)
    if trend=="bullish" and hh>=2 and hl>=2:
        score += 8; reasons.append(f"{AR['hh_hl']} (HH×{hh} HL×{hl})")
    if trend=="bearish" and ll>=2 and lh>=2:
        score += 8; reasons.append(f"{AR['ll_lh']} (LL×{ll} LH×{lh})")
    return score, reasons


def score_liquidity(liquidity):
    score = 0; reasons = []
    if liquidity["liquidity_sweep"]:
        score += 18; sw=liquidity["liquidity_sweep"]
        reasons.append(f"{AR['sweep']} عند {sw['level']}")
    if liquidity["stop_hunt"]:
        score += 14; reasons.append(AR["stop_hunt"])
    if liquidity["fake_breakout"]:
        score += 9;  reasons.append(AR["fake_bo"])
    if liquidity["inducement"]:
        score += 7;  reasons.append(AR["inducement"])
    if liquidity["total_equal_highs"] >= 2:
        score += 5;  reasons.append(f"{AR['eq_hi']} ({liquidity['total_equal_highs']})")
    if liquidity["total_equal_lows"] >= 2:
        score += 5;  reasons.append(f"{AR['eq_lo']} ({liquidity['total_equal_lows']})")
    return score, reasons


def score_smart_money(smart_money):
    score = 0; reasons = []
    if smart_money["institutional_candle"]:
        ic = smart_money["institutional_candle"]
        score += 18; reasons.append(f"{AR['inst']} (جسم {ic['body_ratio']}%)")
    if smart_money["total_bullish_fvg"] > 0:
        score += 9;  reasons.append(f"{AR['bull_fvg']} ×{smart_money['total_bullish_fvg']}")
    if smart_money["total_bearish_fvg"] > 0:
        score += 9;  reasons.append(f"{AR['bear_fvg']} ×{smart_money['total_bearish_fvg']}")
    if smart_money["total_bullish_obs"] > 0:
        score += 7;  reasons.append(f"{AR['bull_ob']} ×{smart_money['total_bullish_obs']}")
    if smart_money["total_bearish_obs"] > 0:
        score += 7;  reasons.append(f"{AR['bear_ob']} ×{smart_money['total_bearish_obs']}")
    if smart_money["breaker_blocks"]:
        score += 6;  reasons.append(AR["breaker"])
    if smart_money["imbalances"]:
        score += 4;  reasons.append(f"{AR['imbalance']} ×{len(smart_money['imbalances'])}")
    return score, reasons


def calculate_confidence(structure, liquidity, smart_money):
    s1,r1 = score_structure(structure)
    s2,r2 = score_liquidity(liquidity)
    s3,r3 = score_smart_money(smart_money)
    confidence = min(s1+s2+s3, 100)
    return confidence, r1+r2+r3


def calculate_risk(confidence):
    if confidence >= 82: return "LOW"
    if confidence >= 60: return "MEDIUM"
    return "HIGH"


def validate_trade(structure, liquidity, smart_money, confidence):
    """هذه الدالة لا تمنع الإشارة — فقط للمرجع"""
    if structure["choch"]:
        return False, "⚠️ تغيير هيكل السوق (CHOCH)"
    return True, "Valid"
