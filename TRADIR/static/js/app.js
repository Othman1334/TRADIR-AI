// ============================================
// TRADIR AI — app.js v4
// Cache + Rate Limit + Arabic UI
// ============================================

let _rateLimitTimer = null;
let _pendingPair    = null;
let _pendingCandles = null;

// ── LICENSE ──────────────────────────────────
async function activateLicense() {
  const key = document.getElementById("licenseKey").value.trim();
  const msg = document.getElementById("message");
  if (!key) { msg.textContent = "أدخل مفتاح الترخيص"; msg.className = "msg-err"; return; }
  msg.textContent = "جاري التحقق..."; msg.className = "";
  try {
    const r = await fetch("/activate", {
      method:"POST", headers:{"Content-Type":"application/json"},
      body: JSON.stringify({licenseKey:key})
    });
    const d = await r.json();
    if (d.success) {
      msg.textContent = "✓ " + d.message; msg.className = "msg-ok";
      setTimeout(() => window.location.href = "/dashboard", 900);
    } else {
      msg.textContent = "✕ " + d.message; msg.className = "msg-err";
    }
  } catch(e) { msg.textContent = "خطأ في الاتصال"; msg.className = "msg-err"; }
}


// ── ANALYZE ──────────────────────────────────
async function analyzeMarket() {
  const sel    = document.getElementById("pairSelect");
  const option = sel.options[sel.selectedIndex];
  const pair   = option ? option.getAttribute("data-api") : "EUR/USD";
  const candles = document.getElementById("candleCount").value;
  const btn    = document.getElementById("analyzeBtn");

  btn.classList.add("loading");
  setSignalState("جاري التحليل...", "loading");
  hideCacheNotice();

  try {
    const r = await fetch("/analyze", {
      method:"POST", headers:{"Content-Type":"application/json"},
      body: JSON.stringify({pair, candles: parseInt(candles)})
    });

    if (!r.ok) {
      setSignalState("خطأ HTTP " + r.status, "wait");
      showErrorReasons(["خطأ في الخادم: " + r.status]);
      return;
    }

    const d = await r.json();

    // ── RATE LIMIT ──
    if (d.error && d.wait) {
      showRateOverlay(pair, candles);
      setSignalState("انتظار...", "wait");
      showErrorReasons(["⏱️ تجاوز حد الطلبات — يتم الانتظار تلقائياً..."]);
      return;
    }

    if (d.error) {
      setSignalState("خطأ", "wait");
      showErrorReasons(["❌ " + d.error]);
      setText("signalPair", pair);
      return;
    }

    // ── SUCCESS ──
    updateSignalPanel(d);
    updateStructurePanel(d);
    updateLiquidityPanel(d);
    updateSmartMoneyPanel(d);
    updateReasons(d.reasons || []);

    if (d.alert && (d.signal === "CALL" || d.signal === "PUT")) {
      playAlert(); showToast(d);
    }

    updateApiStatus();

  } catch(e) {
    setSignalState("خطأ", "wait");
    showErrorReasons(["خطأ في الاتصال: " + e.message]);
  } finally {
    btn.classList.remove("loading");
  }
}


// ── RATE LIMIT OVERLAY ────────────────────────
function showRateOverlay(pair, candles) {
  const overlay    = document.getElementById("rateOverlay");
  const countdown  = document.getElementById("rateCountdown");
  const bar        = document.getElementById("rateBarFill");
  if (!overlay) return;

  overlay.style.display = "flex";
  _pendingPair    = pair;
  _pendingCandles = candles;

  let seconds = 62;
  const total = seconds;

  if (_rateLimitTimer) clearInterval(_rateLimitTimer);

  _rateLimitTimer = setInterval(async () => {
    seconds--;
    if (countdown) countdown.textContent = Math.max(seconds, 0);
    if (bar) bar.style.width = ((seconds / total) * 100) + "%";

    if (seconds <= 0) {
      clearInterval(_rateLimitTimer);
      overlay.style.display = "none";
      // إعادة المحاولة تلقائياً
      await analyzeMarket();
    }
  }, 1000);
}

function hideRateOverlay() {
  const overlay = document.getElementById("rateOverlay");
  if (overlay) overlay.style.display = "none";
  if (_rateLimitTimer) { clearInterval(_rateLimitTimer); _rateLimitTimer = null; }
}


// ── API STATUS INDICATOR ─────────────────────
async function updateApiStatus() {
  try {
    const r = await fetch("/api-status");
    const d = await r.json();
    const rates = d.rate_limits || [];
    const cache = d.cache || {};

    // حساب إجمالي الطلبات المتاحة
    let totalAvail = 0, totalLimit = 0;
    rates.forEach(k => { totalAvail += k.available; totalLimit += k.limit; });

    const pct = totalLimit > 0 ? (totalAvail / totalLimit) * 100 : 100;
    const txt = document.getElementById("apiCreditsText");
    const bar = document.getElementById("apiBarFill");
    const ind = document.getElementById("apiIndicator");

    if (txt) txt.textContent = `API: ${totalAvail}/${totalLimit}`;
    if (bar) {
      bar.style.width = pct + "%";
      bar.style.background = pct > 50 ? "var(--call)" : pct > 20 ? "var(--wait)" : "var(--put)";
    }
    if (ind) {
      ind.className = "api-indicator" + (pct < 20 ? " api-low" : "");
    }

    // Cache notice
    const cacheKeys = Object.keys(cache);
    const sel = document.getElementById("pairSelect");
    if (sel) {
      const cur = sel.options[sel.selectedIndex]?.getAttribute("data-api");
      const cacheKey = cur ? `${cur}_${document.getElementById("candleCount")?.value || 500}` : null;
      const entry = cacheKey ? cache[cacheKey] : null;
      if (entry) showCacheNotice(entry.expires_in);
      else hideCacheNotice();
    }

  } catch(e) { /* silent */ }
}

function showCacheNotice(seconds) {
  const el = document.getElementById("cacheNotice");
  const t  = document.getElementById("cacheTimer");
  if (el) el.style.display = "flex";
  if (t)  t.textContent = seconds;
}
function hideCacheNotice() {
  const el = document.getElementById("cacheNotice");
  if (el) el.style.display = "none";
}


// ── SIGNAL PANEL ─────────────────────────────
function setSignalState(text, cls) {
  const el = document.getElementById("signalDirection");
  el.textContent = text; el.className = "signal-direction " + (cls||"");
}

function updateSignalPanel(d) {
  const dir = document.getElementById("signalDirection");
  dir.textContent = d.signal === "NO TRADE" ? "لا صفقة" : d.signal;
  dir.className = "signal-direction";
  if (d.signal === "CALL") dir.classList.add("call");
  else if (d.signal === "PUT") dir.classList.add("put");
  else dir.classList.add("wait");

  // Warning banner for high-risk signals
  updateRiskBanner(d);

  setText("signalPair",      d.pair || "—");
  setText("signalConfidence",(d.confidence||0)+"%");
  setText("signalEntry",     d.entry_price||"—");
  setText("signalExpiry",    d.expiry||"—");
  setText("signalRisk",      d.risk||"—");
  setText("signalEntryType", d.entry_type||"—");

  const fill = document.getElementById("confFill");
  if (fill) setTimeout(() => fill.style.width = Math.min(d.confidence||0,100)+"%", 50);

  const riskEl = document.getElementById("signalRisk");
  if (riskEl) riskEl.style.color =
    d.risk==="منخفضة" ? "var(--call)" : d.risk==="متوسطة" ? "var(--wait)" : "var(--put)";
}


// ── STRUCTURE ────────────────────────────────
function updateStructurePanel(d) {
  setEngVal("eTrend", d.trend||"—",
    d.trend==="صاعد"?"val-bull":d.trend==="هابط"?"val-bear":"val-dim");

  const bosDir = d.bos_direction;
  const bosClass = bosDir==="صاعد"||bosDir==="bullish" ? "val-bull" : "val-bear";
  setEngVal("eBos", d.bos ? "BOS " + (bosDir||"") : "لا يوجد", d.bos ? bosClass : "val-dim");

  setEngVal("eChoch", d.choch ? "⚠ مكتشف":"آمن", d.choch?"val-warn":"val-bull");
  setEngVal("eStrength",
    (d.market_strength||"—")+(d.strength_pct?` (${d.strength_pct}%)`:""),
    d.market_strength==="قوية"?"val-bull":d.market_strength==="ضعيفة"?"val-bear":"val-gold");
  setEngVal("eHHHL",`HH×${d.hh||0}  HL×${d.hl||0}`,"val-bull");
  setEngVal("eLLLH",`LL×${d.ll||0}  LH×${d.lh||0}`,"val-bear");
}


// ── LIQUIDITY ────────────────────────────────
function updateLiquidityPanel(d) {
  const sw = d.liquidity_sweep;
  if (sw && sw.type)
    setEngVal("eSweep", `${sw.type==="bullish_sweep"?"سحب صاعد":"سحب هابط"} @ ${sw.level}`, "val-gold");
  else setEngVal("eSweep","لا يوجد","val-dim");

  const sh = d.stop_hunt;
  if (sh && sh.direction)
    setEngVal("eStopHunt",`صيد ${sh.direction==="bullish"?"صاعد":"هابط"}`,"val-warn");
  else setEngVal("eStopHunt","لا يوجد","val-dim");

  const fb = d.fake_breakout;
  if (fb && fb.direction)
    setEngVal("eFakeBO",`كسر وهمي ${fb.direction==="bullish"?"صاعد":"هابط"}`,"val-warn");
  else setEngVal("eFakeBO",fb?"نعم":"لا يوجد",fb?"val-warn":"val-dim");

  setEngVal("eEqHL",`قمم:${d.equal_highs||0}  قيعان:${d.equal_lows||0}`,
    (d.equal_highs>2||d.equal_lows>2)?"val-gold":"val-dim");
}


// ── SMART MONEY ──────────────────────────────
function updateSmartMoneyPanel(d) {
  const ic = d.institutional_candle;
  if (ic && ic.type) {
    const isB = ic.type==="bullish_institutional";
    setEngVal("eInstit",`${isB?"صاعدة":"هابطة"} · جسم ${ic.body_ratio}%`, isB?"val-bull":"val-bear");
  } else setEngVal("eInstit","لا يوجد","val-dim");

  setEngVal("eBullFVG",d.total_bullish_fvg||0,(d.total_bullish_fvg||0)>0?"val-bull":"val-dim");
  setEngVal("eBearFVG",d.total_bearish_fvg||0,(d.total_bearish_fvg||0)>0?"val-bear":"val-dim");
  setEngVal("eBullOB", d.total_bullish_obs||0,(d.total_bullish_obs||0)>0?"val-bull":"val-dim");
  setEngVal("eBearOB", d.total_bearish_obs||0,(d.total_bearish_obs||0)>0?"val-bear":"val-dim");
  setEngVal("eBreakers",d.breaker_blocks||0,(d.breaker_blocks||0)>0?"val-gold":"val-dim");
  setEngVal("eImbalances",d.imbalances||0,(d.imbalances||0)>0?"val-gold":"val-dim");
  setEngVal("eRound",d.round_number||"—","val-gold");
}


// ── REASONS ──────────────────────────────────
function updateReasons(reasons) {
  const ul = document.getElementById("reasonsList");
  if (!ul) return;
  if (!reasons||!reasons.length) {
    ul.innerHTML='<li class="reason-placeholder">لا توجد أسباب</li>'; return;
  }
  ul.innerHTML = reasons.map(r => {
    const isWarn = r.includes("⚠")||r.includes("⏱")||r.includes("❌");
    return `<li class="reason-item${isWarn?" reason-warn":""}">${escHtml(r)}</li>`;
  }).join("");
}

function showErrorReasons(msgs) {
  const ul = document.getElementById("reasonsList");
  if (!ul) return;
  ul.innerHTML = msgs.map(m =>
    `<li class="reason-item reason-warn">${escHtml(m)}</li>`
  ).join("");
}


// ── RISK BANNER ─────────────────────────────
function updateRiskBanner(d) {
  let banner = document.getElementById("riskBanner");
  if (!banner) {
    banner = document.createElement("div");
    banner.id = "riskBanner";
    const card = document.querySelector(".card--signal");
    if (card) card.appendChild(banner);
  }

  const lvl = d.risk_level || 3;
  const warn = d.warning;

  if (!warn || d.signal === "NO TRADE") {
    banner.style.display = "none";
    return;
  }

  banner.style.display = "flex";
  banner.className = "risk-banner risk-lvl-" + lvl;

  if (lvl === 2) {
    banner.innerHTML = "⚠️ مخاطرة متوسطة — الشروط جزئية";
  } else if (lvl === 3) {
    banner.innerHTML = "🔴 مخاطرة عالية — الشروط غير مكتملة<br><small>تحقق من الشارت قبل الدخول</small>";
  }
}


// ── TOAST ────────────────────────────────────
function showToast(d) {
  const toast=document.getElementById("signalToast");
  const dir=document.getElementById("toastDir");
  const det=document.getElementById("toastDetails");
  if (!toast) return;
  dir.textContent=d.signal;
  dir.className="toast-dir "+(d.signal==="CALL"?"call":"put");
  det.innerHTML=`${d.pair}  |  دخول: ${d.entry_price}<br>الثقة: ${d.confidence}%  |  المدة: ${d.expiry}`;
  toast.classList.add("visible");
  setTimeout(()=>toast.classList.remove("visible"),6000);
}


// ── AUDIO ─────────────────────────────────────
function playAlert() {
  const s=document.getElementById("entrySound");
  if (s) { s.currentTime=0; s.play().catch(()=>{}); }
}


// ── HELPERS ──────────────────────────────────
function setText(id,val) { const el=document.getElementById(id); if(el) el.textContent=val; }
function setEngVal(id,val,cls) {
  const el=document.getElementById(id); if(!el) return;
  el.textContent=val; el.className="eng-val "+(cls||"");
}
function escHtml(s) {
  return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
}
