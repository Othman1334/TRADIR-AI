# ============================================
# TRADIR AI - CANDLE FETCHER v4
# Cache + Rate Limiter + Multi-Key Rotation
# ============================================

import requests
import time
import threading
from collections import deque

# ============================================
# API KEYS - أضف keys جديدة هنا
# سجّل مجاناً على twelvedata.com للحصول على keys إضافية
# كل key = 8 requests/minute مجاناً
# ============================================

API_KEYS = [
    "45f3103dd4c64e57ad69421b29cd3e30",   # Key 1
    # "YOUR_SECOND_KEY_HERE",              # Key 2 - أضف هنا
    # "YOUR_THIRD_KEY_HERE",               # Key 3 - أضف هنا
]

BASE_URL = "https://api.twelvedata.com/time_series"

FOREX_PAIRS = [
    "EUR/USD","GBP/USD","USD/JPY","USD/CHF","AUD/USD","USD/CAD","NZD/USD",
    "EUR/GBP","EUR/JPY","EUR/AUD","EUR/CAD","GBP/JPY","GBP/AUD","GBP/CAD",
    "AUD/JPY","CAD/JPY","CHF/JPY","NZD/JPY","EUR/CHF","AUD/CAD","AUD/CHF",
    "GBP/CHF","NZD/CAD","NZD/CHF"
]

TV_SYMBOLS = {p: f"FX:{p.replace('/', '')}" for p in FOREX_PAIRS}


# ============================================
# CACHE SYSTEM
# يحفظ النتائج لمدة 60 ثانية
# نفس الزوج في نفس الدقيقة = لا طلب جديد
# ============================================

_cache = {}           # { "EUR/USD_500": (candles, timestamp) }
_cache_lock = threading.Lock()
CACHE_TTL = 60        # ثانية


def _get_cache(pair, outputsize):
    key = f"{pair}_{outputsize}"
    with _cache_lock:
        if key in _cache:
            candles, ts = _cache[key]
            age = time.time() - ts
            remaining = int(CACHE_TTL - age)
            if age < CACHE_TTL:
                print(f"[CACHE HIT] {pair} ({remaining}s remaining)")
                return candles
    return None


def _set_cache(pair, outputsize, candles):
    key = f"{pair}_{outputsize}"
    with _cache_lock:
        _cache[key] = (candles, time.time())


# ============================================
# RATE LIMITER - KEY ROTATION
# يتتبع استخدام كل key ويدور بينهم
# ============================================

_key_usage = {k: deque() for k in API_KEYS}
_key_lock  = threading.Lock()
LIMIT_PER_MIN = 7   # نحتاط بـ 7 بدل 8


def _get_best_key():
    """يرجع الـ key الأقل استخداماً في الدقيقة الأخيرة"""
    now = time.time()
    with _key_lock:
        best_key   = None
        best_usage = 999
        best_wait  = 0

        for key in API_KEYS:
            # أزل الطلبات القديمة (أكثر من دقيقة)
            while _key_usage[key] and now - _key_usage[key][0] > 60:
                _key_usage[key].popleft()

            usage = len(_key_usage[key])

            if usage < LIMIT_PER_MIN:
                if usage < best_usage:
                    best_usage = usage
                    best_key   = key
                    best_wait  = 0
            else:
                # احسب وقت الانتظار لهذا الـ key
                oldest = _key_usage[key][0]
                wait   = 61 - (now - oldest)
                if best_key is None or wait < best_wait:
                    best_wait = wait
                    best_key  = key  # fallback

        return best_key, best_wait


def _record_key_usage(key):
    with _key_lock:
        _key_usage[key].append(time.time())


# ============================================
# SMART WAIT
# إذا كل الـ keys فاضت، ينتظر ذكياً
# ============================================

def _smart_wait():
    """انتظر إذا كل الـ keys وصلت الحد"""
    max_attempts = 5
    for attempt in range(max_attempts):
        key, wait = _get_best_key()
        if wait == 0:
            return key
        if attempt == 0:
            print(f"[RATE LIMIT] جميع الـ keys محدودة، انتظار {wait:.1f}s...")
        time.sleep(min(wait + 0.5, 15))  # انتظر بحد أقصى 15 ثانية
    return API_KEYS[0]  # fallback


# ============================================
# MAIN FETCH FUNCTION
# ============================================

def fetch_candles(symbol, interval="1min", outputsize=500):
    # 1. تحقق من الـ Cache أولاً
    cached = _get_cache(symbol, outputsize)
    if cached:
        return cached, None

    # 2. اختر الـ Key المناسب
    key = _smart_wait()
    _record_key_usage(key)

    params = {
        "symbol":     symbol,
        "interval":   interval,
        "outputsize": outputsize,
        "apikey":     key
    }

    try:
        resp = requests.get(BASE_URL, params=params, timeout=15)

        if resp.status_code != 200:
            return None, f"HTTP {resp.status_code}: {resp.text[:100]}"

        try:
            data = resp.json()
        except Exception:
            return None, f"استجابة غير صالحة: {resp.text[:80]}"

        # Rate limit hit → انتظر وأعد المحاولة تلقائياً
        if "values" not in data:
            msg = data.get("message", str(data)[:120])
            if "run out of API credits" in msg or "limit" in msg.lower():
                print(f"[RATE LIMIT HIT] {msg[:80]}")
                # أضغط usage لهذا الـ key حتى يصل الحد
                with _key_lock:
                    while len(_key_usage[key]) < LIMIT_PER_MIN:
                        _key_usage[key].append(time.time())
                # انتظر وأعد المحاولة بـ key مختلف
                time.sleep(2)
                new_key = _smart_wait()
                if new_key != key:
                    _record_key_usage(new_key)
                    params["apikey"] = new_key
                    resp2 = requests.get(BASE_URL, params=params, timeout=15)
                    try:
                        data = resp2.json()
                    except Exception:
                        pass

            if "values" not in data:
                msg = data.get("message") or data.get("status") or str(data)[:100]
                return None, f"خطأ API: {msg}"

        if len(data["values"]) == 0:
            return None, "لا توجد بيانات لهذا الزوج"

        values  = list(reversed(data["values"]))
        candles = []
        for c in values:
            candles.append({
                "datetime": c.get("datetime", ""),
                "open":     float(c["open"]),
                "high":     float(c["high"]),
                "low":      float(c["low"]),
                "close":    float(c["close"]),
            })

        # 3. خزّن في الـ Cache
        _set_cache(symbol, outputsize, candles)
        print(f"[FETCHED] {symbol}: {len(candles)} candles → cached 60s")
        return candles, None

    except requests.exceptions.Timeout:
        return None, "انتهت مهلة الاتصال (15s)"
    except requests.exceptions.ConnectionError:
        return None, "لا يوجد اتصال بالإنترنت"
    except Exception as e:
        return None, f"خطأ غير متوقع: {str(e)}"


# ============================================
# CACHE STATUS - للـ Dashboard
# ============================================

def get_cache_status():
    now = time.time()
    status = {}
    with _cache_lock:
        for k, (candles, ts) in _cache.items():
            age = now - ts
            if age < CACHE_TTL:
                status[k] = {
                    "candles": len(candles),
                    "age_sec": int(age),
                    "expires_in": int(CACHE_TTL - age)
                }
    return status


def get_rate_status():
    now = time.time()
    result = []
    with _key_lock:
        for i, key in enumerate(API_KEYS):
            usage = sum(1 for t in _key_usage[key] if now - t <= 60)
            result.append({
                "key_index": i + 1,
                "usage_per_min": usage,
                "limit": LIMIT_PER_MIN,
                "available": max(0, LIMIT_PER_MIN - usage)
            })
    return result
