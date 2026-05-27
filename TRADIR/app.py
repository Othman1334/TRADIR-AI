# ============================================
# TRADIR AI - MAIN SERVER v4
# Leaders Of Trading
# ============================================

from flask import Flask, render_template, request, jsonify
from core.candle_fetcher import fetch_candles, FOREX_PAIRS, TV_SYMBOLS, get_cache_status, get_rate_status
from core.analyzer import analyze_market

app = Flask(__name__)

VALID_LICENSES = ["LOT-1234-5678","LOT-9999-0000","LOT-ABCD-EFGH"]

TREND_AR    = {"bullish":"صاعد","bearish":"هابط","neutral":"تذبذب"}
STRENGTH_AR = {"strong":"قوية","medium":"متوسطة","weak":"ضعيفة"}
RISK_AR     = {"LOW":"منخفضة","MEDIUM":"متوسطة","HIGH":"عالية"}
BOS_AR      = {"bullish":"صاعد","bearish":"هابط"}


def normalize_pair(raw):
    p = raw.strip()
    for prefix in ("FX_IDC:","FX:","OANDA:","FOREX:"):
        if p.upper().startswith(prefix.upper()):
            p = p[len(prefix):]
    if "/" not in p and len(p) == 6:
        p = p[:3] + "/" + p[3:]
    return p.upper()


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/activate", methods=["POST"])
def activate():
    data = request.get_json()
    key  = data.get("licenseKey","")
    if key in VALID_LICENSES:
        return jsonify({"success":True,"message":"تم تفعيل الترخيص بنجاح"})
    return jsonify({"success":False,"message":"مفتاح الترخيص غير صحيح"})


@app.route("/dashboard")
def dashboard():
    pairs = [{"label":p,"tv":TV_SYMBOLS[p]} for p in FOREX_PAIRS]
    return render_template("dashboard.html", pairs=pairs)


# ── NEW: API Status endpoint ──────────────────
@app.route("/api-status")
def api_status():
    return jsonify({
        "cache":       get_cache_status(),
        "rate_limits": get_rate_status()
    })


@app.route("/analyze", methods=["POST"])
def analyze():
    try:
        data         = request.get_json(force=True)
        raw_pair     = data.get("pair","EUR/USD")
        pair         = normalize_pair(raw_pair)
        candle_count = int(data.get("candles",500))

        print(f"[ANALYZE] {pair} ({candle_count} candles)")

        candles, error = fetch_candles(pair, outputsize=candle_count)

        if error or not candles:
            msg = error or "لا توجد بيانات"
            # إذا rate limit، أعطِ رسالة واضحة
            if "credits" in (msg or "") or "limit" in (msg or "").lower():
                return jsonify({
                    "error": "⏱️ تجاوزت الحد المسموح (8 طلبات/دقيقة). انتظر دقيقة ثم أعد المحاولة.",
                    "wait": True
                })
            return jsonify({"error": msg})

        analysis = analyze_market(candles)

        current_price = candles[-1]["close"]
        round_number  = round(current_price * 100) / 100
        raw_trend     = analysis["structure"]["trend"]
        raw_strength  = analysis["structure"]["market_strength"]
        raw_risk      = analysis.get("risk","HIGH")
        raw_bos_dir   = analysis["structure"].get("bos_direction")

        return jsonify({
            "pair":          pair,
            "candles":       candle_count,
            "signal":        analysis.get("signal","NO TRADE"),
            "confidence":    analysis.get("confidence",0),
            "risk":          RISK_AR.get(raw_risk,raw_risk),
            "entry_type":    analysis.get("entry_type","انتظار"),
            "expiry":        analysis.get("expiry","لا يوجد"),
            "entry_price":   round(current_price,5),
            "round_number":  round_number,
            "alert":         analysis.get("alert",False),
            "warning":       analysis.get("warning",False),
            "risk_level":    analysis.get("risk_level",3),
            "reasons":       analysis.get("reasons",[]),

            "trend":           TREND_AR.get(raw_trend,raw_trend),
            "bos":             analysis["structure"]["bos"],
            "bos_direction":   BOS_AR.get(raw_bos_dir, raw_bos_dir or "—"),
            "choch":           analysis["structure"]["choch"],
            "market_strength": STRENGTH_AR.get(raw_strength,raw_strength),
            "strength_pct":    analysis["structure"]["strength_pct"],
            "hh": analysis["structure"]["hh"],
            "hl": analysis["structure"]["hl"],
            "ll": analysis["structure"]["ll"],
            "lh": analysis["structure"]["lh"],

            "liquidity_sweep": analysis["liquidity"]["liquidity_sweep"],
            "stop_hunt":       analysis["liquidity"]["stop_hunt"],
            "fake_breakout":   analysis["liquidity"]["fake_breakout"],
            "equal_highs":     analysis["liquidity"]["total_equal_highs"],
            "equal_lows":      analysis["liquidity"]["total_equal_lows"],

            "institutional_candle": analysis["smart_money"]["institutional_candle"],
            "total_bullish_fvg":    analysis["smart_money"]["total_bullish_fvg"],
            "total_bearish_fvg":    analysis["smart_money"]["total_bearish_fvg"],
            "total_bullish_obs":    analysis["smart_money"]["total_bullish_obs"],
            "total_bearish_obs":    analysis["smart_money"]["total_bearish_obs"],
            "breaker_blocks":       len(analysis["smart_money"]["breaker_blocks"]),
            "imbalances":           len(analysis["smart_money"]["imbalances"]),
        })

    except Exception as e:
        import traceback
        print("[EXCEPTION]", traceback.format_exc())
        return jsonify({"error": f"خطأ داخلي: {str(e)}"})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
