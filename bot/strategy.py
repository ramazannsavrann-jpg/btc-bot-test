"""
BTC Bot - strateji motoru (geçmiş testi ve canlı kâğıt testi AYNI kodu kullanır).

Mantık (sadece spot, sadece alım yönü, kaldıraç YOK):
  1) Trend filtresi : Kapanış > EMA200 ve EMA50 > EMA200  -> sadece yükseliş trendinde işlem
  2) Giriş          : RSI(14), giriş eşiğinin altından yukarı keserse (geri çekilme bitti sinyali)
                      VEYA (breakout_len>0 ise) kapanış son N saatin en yükseğini kırarsa
                      -> bir sonraki mumun açılışında alım
  3) Stop           : giriş - stop_atr * ATR
  4) Hedef          : giriş + tp_atr * ATR
  5) Kârı koruma    : fiyat be_atr * ATR yükselince stop başa-baş noktasına çekilir,
                      sonrasında stop, (kapanış - trail_atr * ATR) seviyesini izler
  6) Süre stopu     : max_hold saatten uzun süren işlem kapanışta kapatılır
  7) Risk           : işlem başına hesabın en fazla %risk'i kaybedilir (pozisyon büyüklüğü buna göre)
  8) Fren           : art arda N kayıpta pause_hours saat bekler; max_dd düşüşte bot tamamen durur
  9) Maliyet        : her alım/satımda komisyon + kayma (slippage) düşülür

Tüm durum zaman damgası (ms) ile tutulur, indeksle değil; böylece canlı testte
kaçan çalıştırmalar sonradan sırayla doğru işlenir.
"""
from __future__ import annotations

import math

HOUR_MS = 3_600_000
BAR_MS = {"1h": HOUR_MS, "15m": HOUR_MS // 4, "4h": 4 * HOUR_MS}

DEFAULT_PARAMS = {
    "ema_fast": 50,
    "ema_slow": 200,
    "rsi_len": 14,
    "rsi_entry": 35.0,
    "breakout_len": 0,       # >0 ise: trendde son N saatin zirvesi kırılınca da al (0 = kapalı)
    "atr_len": 14,
    "stop_atr": 2.0,
    "tp_atr": 3.0,
    "be_atr": 1.5,
    "trail_atr": 2.0,
    "max_hold": 72,          # saat (1 saatlik mum)
    "risk": 0.015,           # işlem başına hesabın %1.5'i
    "max_alloc": 0.99,       # paranın en fazla %99'u tek pozisyona
    "fee": 0.001,            # Binance spot %0.1
    "slip": 0.0005,          # %0.05 kayma
    "loss_streak": 3,
    "pause_hours": 24,
    "max_dd": None,          # örn. 0.10 -> %10 düşüşte dur (canlı testte açık)
    "interval": "1h",        # mum süresi: "1h" veya "15m"
    "signal": "pullback",    # "pullback" (RSI dönüşü / zirve kırılımı) veya "ema_cross"
    "x_fast": 9,             # ema_cross için hızlı EMA
    "x_slow": 21,            # ema_cross için yavaş EMA
}


# ---------------------------------------------------------------- göstergeler
def ema(values, length):
    out = [math.nan] * len(values)
    if len(values) < length:
        return out
    k = 2.0 / (length + 1)
    prev = sum(values[:length]) / length
    out[length - 1] = prev
    for i in range(length, len(values)):
        prev = values[i] * k + prev * (1 - k)
        out[i] = prev
    return out


def rsi(closes, length):
    out = [math.nan] * len(closes)
    if len(closes) <= length:
        return out
    gains = losses = 0.0
    for i in range(1, length + 1):
        d = closes[i] - closes[i - 1]
        gains += max(d, 0.0)
        losses += max(-d, 0.0)
    avg_g, avg_l = gains / length, losses / length

    def val(g, l):
        if l == 0:
            return 100.0 if g > 0 else 50.0
        return 100.0 - 100.0 / (1.0 + g / l)

    out[length] = val(avg_g, avg_l)
    for i in range(length + 1, len(closes)):
        d = closes[i] - closes[i - 1]
        avg_g = (avg_g * (length - 1) + max(d, 0.0)) / length
        avg_l = (avg_l * (length - 1) + max(-d, 0.0)) / length
        out[i] = val(avg_g, avg_l)
    return out


def atr(highs, lows, closes, length):
    n = len(closes)
    out = [math.nan] * n
    if n <= length:
        return out
    trs = [highs[0] - lows[0]]
    for i in range(1, n):
        trs.append(max(highs[i] - lows[i],
                       abs(highs[i] - closes[i - 1]),
                       abs(lows[i] - closes[i - 1])))
    prev = sum(trs[1:length + 1]) / length
    out[length] = prev
    for i in range(length + 1, n):
        prev = (prev * (length - 1) + trs[i]) / length
        out[i] = prev
    return out


def indicators(candles, p):
    closes = [c[4] for c in candles]
    highs = [c[2] for c in candles]
    lows = [c[3] for c in candles]
    out = {
        "ema_fast": ema(closes, p["ema_fast"]),
        "ema_slow": ema(closes, p["ema_slow"]),
        "rsi": rsi(closes, p["rsi_len"]),
        "atr": atr(highs, lows, closes, p["atr_len"]),
    }
    from . import signals
    out.update(signals.get(p).indicators(candles, p, out))
    out.update(signals.filter_indicators(candles, p))
    return out


# ---------------------------------------------------------------- motor
def new_state(start_equity, params):
    return {
        "params": dict(params),
        "start_equity": start_equity,
        "cash": start_equity,
        "qty": 0.0,
        "position": None,       # {entry_ts, entry_px, stop, tp, atr, qty, cost}
        "pending_entry": None,  # {signal_ts, atr}
        "loss_streak": 0,
        "pause_until": 0,
        "peak": start_equity,
        "halted": False,
        "halt_reason": None,
        "last_ts": 0,           # işlenen son mumun açılış zamanı
        "last_close": None,
        "trades": [],
    }


# Dolum kancası (gecikmeli/gerçekçi dolum). None iken davranış eskisiyle birebir aynıdır.
# İmza: FILL_HOOK(olay, olay_ts_ms, varsayilan_fiyat, state) -> fiyat. Kayma bunun ÜSTÜNE bir kez uygulanır.
FILL_HOOK = None


def _fill(kind, t_event, px, state):
    return FILL_HOOK(kind, t_event, px, state) if FILL_HOOK else px


def equity(state, price):
    return state["cash"] + state["qty"] * price


def _close_position(state, ts, px, reason):
    p = state["params"]
    pos = state["position"]
    exit_px = px * (1 - p["slip"])
    gross = pos["qty"] * exit_px
    fee = gross * p["fee"]
    state["cash"] += gross - fee
    pnl = (gross - fee) - pos["cost"]
    state["trades"].append({
        "entry_ts": pos["entry_ts"], "exit_ts": ts,
        "entry_px": round(pos["entry_px"], 2), "exit_px": round(exit_px, 2),
        "qty": pos["qty"], "pnl": round(pnl, 4),
        "pnl_pct": round(pnl / pos["cost"] * 100, 3),
        "reason": reason,
    })
    state["qty"] = 0.0
    state["position"] = None
    if pnl < 0:
        state["loss_streak"] += 1
        if state["loss_streak"] >= p["loss_streak"]:
            state["pause_until"] = ts + p["pause_hours"] * HOUR_MS
            state["loss_streak"] = 0
    else:
        state["loss_streak"] = 0


def _open_position(state, ts, open_px, atr_val, rvol=None):
    p = state["params"]
    open_px = _fill("giris", ts, open_px, state)
    entry_px = open_px * (1 + p["slip"])
    eq = state["cash"]
    stop_dist = entry_px * p["stop_pct"] if p.get("stop_pct") else p["stop_atr"] * atr_val
    if stop_dist <= 0 or eq <= 1:
        return
    # risk tabanlı büyüklük: stop çalışırsa kayıp ~ eq * risk
    risk_frac = stop_dist / entry_px + 2 * p["fee"] + 2 * p["slip"]
    notional = min(eq * p["risk"] / risk_frac, eq * p["max_alloc"])
    if p.get("vol_target") and rvol:
        # volatilite hedefleme: oynaklık yüksekse küçük, düşükse büyük pozisyon (en fazla %99)
        notional = min(eq * p["max_alloc"], eq * p["vol_target"] / rvol)
    notional = notional / (1 + p["fee"])
    if notional < 5:  # Binance min. işlem ~5 USDT
        return
    fee = notional * p["fee"]
    qty = notional / entry_px
    state["cash"] -= notional + fee
    state["qty"] = qty
    state["position"] = {
        "entry_ts": ts, "entry_px": entry_px,
        "stop": entry_px - stop_dist,
        "tp": entry_px * (1 + p["tp_pct"]) if p.get("tp_pct") else entry_px + p["tp_atr"] * atr_val,
        "hh": entry_px,
        "atr": atr_val, "qty": qty, "cost": notional + fee,
        "be_done": False,
    }


def process_bar(state, candles, ind, i):
    """i. mumu (kapanmış) işle. candles[i] = (ts, o, h, l, c, v)."""
    p = state["params"]
    ts, o, h, l, c, _ = candles[i]
    if ts <= state["last_ts"]:
        return

    # 1) bekleyen alım emri bu mumun açılışında gerçekleşir
    if state["pending_entry"] and not state["halted"] and state["position"] is None:
        _open_position(state, ts, o, state["pending_entry"]["atr"], state["pending_entry"].get("rvol"))
    state["pending_entry"] = None

    # 2) açık pozisyon: stop / hedef (aynı mumda ikisi de varsa stop önce = temkinli)
    pos = state["position"]
    if pos:
        if l <= pos["stop"]:
            _close_position(state, ts, min(o, pos["stop"]),
                            "kâr koruma stopu" if pos["be_done"] else "stop")
        elif h >= pos["tp"]:
            _close_position(state, ts, max(o, pos["tp"]), "hedef")
    pos = state["position"]
    if pos:
        a = ind["atr"][i]
        k = p.get("chandelier_atr")
        if k and not math.isnan(a):
            # Chandelier çıkışı: girişten beri en yüksek - k*ATR (sadece yukarı taşınır)
            pos["hh"] = max(pos.get("hh", pos["entry_px"]), h)
            pos["stop"] = max(pos["stop"], pos["hh"] - k * a)
        if not math.isnan(a) and p.get("be_atr"):
            if pos["be_done"] or c - pos["entry_px"] >= p["be_atr"] * pos["atr"]:
                pos["be_done"] = True
                be = pos["entry_px"] * (1 + 2 * p["fee"] + 2 * p["slip"])
                pos["stop"] = max(pos["stop"], be, c - p["trail_atr"] * a)
        bar_ms = BAR_MS.get(p.get("interval", "1h"), HOUR_MS)
        if (ts + bar_ms - pos["entry_ts"]) / HOUR_MS >= p["max_hold"]:
            _close_position(state, ts, _fill("cikis", ts + bar_ms, c, state), "süre")
        else:
            from . import signals
            why = signals.get(p).exit(ind, i, candles, p, pos)
            if why:
                _close_position(state, ts, _fill("cikis", ts + bar_ms, c, state), why)

    # 3) düşüş freni
    eq = equity(state, c)
    state["peak"] = max(state["peak"], eq)
    if p.get("max_dd") and not state["halted"] and eq < state["peak"] * (1 - p["max_dd"]):
        if state["position"]:
            _close_position(state, ts, c, "fren")
        state["halted"] = True
        state["halt_reason"] = f"Hesap zirveden %{int(p['max_dd'] * 100)} düştü, bot durdu"

    # 4) yeni sinyal (bir sonraki mumda alınır)
    if (state["position"] is None and not state["halted"] and ts >= state["pause_until"]
            and i >= 1):
        ef, es, r, a = ind["ema_fast"][i], ind["ema_slow"][i], ind["rsi"][i], ind["atr"][i]
        r_prev = ind["rsi"][i - 1]
        if not any(math.isnan(x) for x in (ef, es, r, r_prev, a)):
            from . import signals
            entry = signals.get(p).entry(ind, i, candles, p)
            if entry and p.get("trend_filter") and not c > es:
                entry = False
            if entry and not signals.filters_ok(ind, i, c, p):
                entry = False
            if entry:
                from . import external
                why = external.entry_blocked(p, ts + BAR_MS.get(p.get("interval", "1h"), HOUR_MS))
                if why:
                    entry = False
                    state["blocked"] = state.get("blocked", 0) + 1
            if entry:
                rv = ind.get("rvol")
                state["pending_entry"] = {"signal_ts": ts, "atr": a,
                                          "rvol": rv[i] if rv and not math.isnan(rv[i]) else None}

    state["last_ts"] = ts
    state["last_close"] = c


def close_all(state, ts, px, reason):
    if state["position"]:
        _close_position(state, ts, px, reason)


def describe_open(state, price):
    pos = state["position"]
    if not pos:
        return None
    unreal = pos["qty"] * price - pos["cost"]
    return (f"{pos['entry_px']:,.0f}$'dan alındı, stop {pos['stop']:,.0f}$, "
            f"hedef {pos['tp']:,.0f}$, şu an {unreal:+.2f}$")


def run(candles, params, start_equity=100.0, state=None):
    """Mum listesini baştan sona işler; mevcut state verilirse kaldığı yerden devam eder."""
    if state is None:
        state = new_state(start_equity, params)
    ind = indicators(candles, state["params"])
    for i in range(len(candles)):
        process_bar(state, candles, ind, i)
    return state


def stats(state, price=None):
    trades = state["trades"]
    wins = [t for t in trades if t["pnl"] > 0]
    gp = sum(t["pnl"] for t in wins)
    gl = -sum(t["pnl"] for t in trades if t["pnl"] <= 0)
    price = price if price is not None else (state["last_close"] or 0)
    eq = equity(state, price)
    return {
        "equity": eq,
        "return_pct": (eq / state["start_equity"] - 1) * 100,
        "trades": len(trades),
        "wins": len(wins),
        "win_rate": (len(wins) / len(trades) * 100) if trades else 0.0,
        "profit_factor": (gp / gl) if gl > 0 else (math.inf if gp > 0 else 0.0),
    }
