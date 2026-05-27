# ============================================
# TRADIR AI - MASTER ANALYZER
# ============================================

from core.structure        import analyze_structure
from core.liquidity        import analyze_liquidity
from core.smart_money      import analyze_smart_money
from core.probability_engine import calculate_confidence, calculate_risk
from core.signal_engine    import generate_signal


def analyze_market(candles):
    if len(candles) < 20:
        return {"error": "Not enough candles"}

    structure   = analyze_structure(candles)
    liquidity   = analyze_liquidity(candles)
    smart_money = analyze_smart_money(candles)

    confidence, reasons = calculate_confidence(structure, liquidity, smart_money)
    risk = calculate_risk(confidence)

    analysis = {
        "structure":   structure,
        "liquidity":   liquidity,
        "smart_money": smart_money,
        "confidence":  confidence,
        "risk":        risk,
        "reasons":     reasons,
    }

    signal_data = generate_signal(analysis)
    analysis.update(signal_data)
    return analysis
