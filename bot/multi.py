"""
Çoklu coin portföy motoru — hacimce en büyük 30 coini her saat tarar, en iyi fırsatlara girer.

Modlar:
  * "score"    : AKILLI SKOR. Her coine 8 üzerinden puan verilir:
                   trend (fiyat>EMA200, EMA50>EMA200), göreceli güç (son 7 gün BTC'den güçlü),
                   momentum sıralaması (evrenin ilk üçte biri), kırılım (son 48 saatin zirvesi),
                   formasyon kırılımı (ikili dip, ters OBO, yatay direnç, fincan-kulp, takoz/üçgen),
                   hacim patlaması (hacim > 1,5× ortalama), sağlıklı RSI (50–75).
                 Puanı eşik üstündeki coinler puan ve momentuma göre sıralanır, boş yer kadar alınır.
  * "rotation" : MOMENTUM ROTASYONU. Her gün 00:00 UTC'de son N saatte en çok yükselen ilk K coini
                 (fiyatı EMA200 üstündeyse) eşit ağırlıkla tutar; listeden düşeni satar.
  * "scan"     : DONCHIAN TARAYICI. Her coinde Donchian kırılımı (trend + haber/duygu freni) arar.

Ortak: BTC piyasa yönü filtresi (BTC EMA200 altındaysa yeni alım yok), FOMC/CPI olay freni,
Korku & Açgözlülük freni, işlem başına risk, en fazla max_pos pozisyon, Chandelier iz süren stop,
coin büyüklüğüne göre kayma (küçük coin = daha pahalı), %10 düşüş freni (canlı).
Sinyal i. mum kapanışında üretilir, işlem bir sonraki mumun açılışında yapılır (geleceği görmez).
"""
from __future__ import annotations

import math

from . import external
from .signals import PATTERNS, REGISTRY, highest, lowest, sma
from .strategy import BAR_MS, HOUR_MS, atr, ema, rsi

DEFAULT = {
    "engine": "multi", "mode": "score", "interval": "1h",
    "max_pos": 5, "risk": 0.01, "stop_atr": 2.5, "chandelier_atr": 3.0, "max_hold": 120,
    "fee": 0.001, "slip_tiers": [[5, 0.0005], [15, 0.001], [99, 0.002]],
    "btc_filter": True, "event_pause": True, "fg_max": None, "max_dd": None,
    "score_min": 6, "mom_len": 168, "dc_len": 48, "dc_exit": 24,
    "rot_k": 3, "rot_hour": 23, "loss_streak": 3, "pause_hours": 24,
}
PAT_USE = ["ikili_dip", "ters_obo", "direnc", "fincan_kulp"]
NAN = math.nan


def isn(*xs):
    return any(x is None or (isinstance(x, float) and math.isnan(x)) for x in xs)


# ---------------------------------------------------------------- hazırlık
def sym_indicators(candles, p, with_patterns):
    o = [c[1] for c in candles]
    h = [c[2] for c in candles]
    lo = [c[3] for c in candles]
    cl = [c[4] for c in candles]
    v = [c[5] for c in candles]
    n = p["mom_len"]
    ind = {
        "o": o, "h": h, "l": lo, "c": cl, "v": v,
        "ema50": ema(cl, 50), "ema200": ema(cl, 200), "rsi": rsi(cl, 14), "atr": atr(h, lo, cl, 14),
        "dc_hi": highest(h, p["dc_len"]), "dc_lo": lowest(lo, p["dc_exit"]), "vol_ma": sma(v, 20),
        "mom": [cl[i] / cl[i - n] - 1 if i >= n and cl[i - n] > 0 else NAN for i in range(len(cl))],
    }
    if with_patterns:
        pp = {"pivot_k": 4}
        lv = {k: PATTERNS[k](h, lo, cl, pp) for k in PAT_USE}
        w = REGISTRY["wedge"].indicators(candles, pp, {})
        lv["takoz"] = [u if ok else NAN for u, ok in zip(w["w_up"], w["w_ok"])]
        ind["levels"] = lv
    return ind


def prepare(data, p, universe=None):
    """data: {coin: mumlar}. universe: hacim sırasına göre coin listesi (kayma kademeleri için)."""
    universe = universe or list(data)
    ctx = {"data": data, "ind": {}, "idx": {}, "universe": universe}
    pat = p.get("mode") == "score"
    times = set()
    for s, c in data.items():
        ctx["ind"][s] = sym_indicators(c, p, pat)
        ctx["idx"][s] = {x[0]: i for i, x in enumerate(c)}
        times.update(ctx["idx"][s])
    ctx["times"] = sorted(times)
    return ctx


def slip_of(p, universe, sym):
    rank = universe.index(sym) + 1 if sym in universe else 99
    for lim, s in p["slip_tiers"]:
        if rank <= lim:
            return s
    return p["slip_tiers"][-1][1]


# ---------------------------------------------------------------- durum
def new_state(start_equity, params, universe):
    return {
        "multi": True, "params": dict(params), "universe": list(universe),
        "start_equity": start_equity, "cash": start_equity, "pos": {}, "pending": {}, "pending_exit": [],
        "trades": [], "peak": start_equity, "halted": False, "halt_reason": None,
        "last_ts": 0, "last_close": {}, "loss_streak": 0, "pause_until": 0,
        # tek-coin raporlarıyla uyum için
        "qty": 0.0, "position": None, "pending_entry": None,
    }


def equity(state, price=None):
    return state["cash"] + sum(ps["qty"] * state["last_close"].get(s, ps["entry_px"])
                               for s, ps in state["pos"].items())


def _close(state, sym, ts, px, reason):
    p = state["params"]
    ps = state["pos"].pop(sym)
    exit_px = px * (1 - ps["slip"])
    gross = ps["qty"] * exit_px
    fee = gross * p["fee"]
    state["cash"] += gross - fee
    pnl = gross - fee - ps["cost"]
    state["trades"].append({"coin": sym, "entry_ts": ps["entry_ts"], "exit_ts": ts,
                            "entry_px": ps["entry_px"], "exit_px": exit_px, "qty": ps["qty"],
                            "pnl": round(pnl, 4), "pnl_pct": round(pnl / ps["cost"] * 100, 3),
                            "reason": reason})
    if pnl < 0:
        state["loss_streak"] += 1
        if state["loss_streak"] >= p["loss_streak"]:
            state["pause_until"] = ts + p["pause_hours"] * HOUR_MS
            state["loss_streak"] = 0
    else:
        state["loss_streak"] = 0


def close_all(state, ts, px=None, reason="kapanış"):
    for s in list(state["pos"]):
        _close(state, s, ts, state["last_close"].get(s, state["pos"][s]["entry_px"]), reason)


def _open(state, sym, ts, open_px, a, why):
    p = state["params"]
    slip = slip_of(p, state["universe"], sym)
    px = open_px * (1 + slip)
    eq = equity(state)
    if p["mode"] == "rotation":
        notional = eq / p["rot_k"]
        stop_dist = p["stop_atr"] * a
    else:
        stop_dist = p["stop_atr"] * a
        risk_frac = stop_dist / px + 2 * (p["fee"] + slip)
        notional = min(eq * p["risk"] / risk_frac, eq / p["max_pos"])
    notional = min(notional, state["cash"] / (1 + p["fee"]))
    if notional < 5 or stop_dist <= 0:
        return
    fee = notional * p["fee"]
    state["cash"] -= notional + fee
    state["pos"][sym] = {"qty": notional / px, "entry_px": px, "entry_ts": ts, "cost": notional + fee,
                         "stop": px - stop_dist, "hh": px, "atr": a, "slip": slip, "why": why}


# ---------------------------------------------------------------- sinyaller
def _pattern_break(ind, i):
    c, cp = ind["c"][i], ind["c"][i - 1]
    for name, lv in ind.get("levels", {}).items():
        a, b = lv[i], lv[i - 1]
        ref = b if not isn(b) else a
        if not isn(a, ref) and c > a * 1.001 and cp <= ref * 1.001:
            return name
    return None


def score_coin(ind, i, btc_mom, top_third):
    c, e50, e200, r = ind["c"][i], ind["ema50"][i], ind["ema200"][i], ind["rsi"][i]
    if isn(c, e50, e200, r) or i < 1:
        return None, []
    if not (c > e200 and r < 80):        # zorunlu: uzun vadeli yükseliş, aşırı alım yok
        return None, []
    why = ["trend"]
    s = 1
    if e50 > e200:
        s += 1; why.append("EMA50>200")
    m = ind["mom"][i]
    if not isn(m, btc_mom) and m > btc_mom:
        s += 1; why.append("BTC'den güçlü")
    if top_third:
        s += 1; why.append("momentum ilk 1/3")
    d = ind["dc_hi"][i - 1]
    if not isn(d) and c > d:
        s += 1; why.append("48s zirve kırılımı")
    pb = _pattern_break(ind, i)
    if pb:
        s += 1; why.append(f"formasyon:{pb}")
    vm = ind["vol_ma"][i]
    if not isn(vm) and ind["v"][i] > 1.5 * vm:
        s += 1; why.append("hacim patlaması")
    if 50 < r < 75:
        s += 1; why.append("RSI sağlıklı")
    return s, why


def process_time(state, ctx, t):
    p = state["params"]
    if t <= state["last_ts"]:
        return
    D, I, X = ctx["data"], ctx["ind"], ctx["idx"]
    bar = BAR_MS.get(p.get("interval", "1h"), HOUR_MS)

    # 1) bekleyen satışlar ve alımlar bu mumun açılışında
    for s in state["pending_exit"]:
        if s in state["pos"] and t in X.get(s, {}):
            _close(state, s, t, D[s][X[s][t]][1], "rotasyon dışı")
    state["pending_exit"] = []
    for s, pe in list(state["pending"].items()):
        if s not in state["pos"] and t in X.get(s, {}) and not state["halted"]:
            _open(state, s, t, D[s][X[s][t]][1], pe["atr"], pe["why"])
    state["pending"] = {}

    # 2) açık pozisyonları yönet
    for s in list(state["pos"]):
        if t not in X.get(s, {}):
            continue
        i = X[s][t]
        _, o, h, lo, c, _ = D[s][i]
        ps = state["pos"][s]
        if lo <= ps["stop"]:
            _close(state, s, t, min(o, ps["stop"]), "stop" if ps["stop"] < ps["entry_px"] else "iz süren stop")
            continue
        a = I[s]["atr"][i]
        if not isn(a) and p.get("chandelier_atr") and p["mode"] != "rotation":
            ps["hh"] = max(ps["hh"], h)
            ps["stop"] = max(ps["stop"], ps["hh"] - p["chandelier_atr"] * a)
        if p["mode"] != "rotation" and (t + bar - ps["entry_ts"]) / HOUR_MS >= p["max_hold"]:
            _close(state, s, t, c, "süre")
        elif p["mode"] == "scan" and not isn(I[s]["dc_lo"][i - 1]) and c < I[s]["dc_lo"][i - 1]:
            _close(state, s, t, c, "kanal altı")
        elif p["mode"] == "score" and not isn(I[s]["ema200"][i]) and c < I[s]["ema200"][i]:
            _close(state, s, t, c, "trend bozuldu")

    for s in D:
        if t in X[s]:
            state["last_close"][s] = D[s][X[s][t]][4]

    # 3) düşüş freni
    eq = equity(state)
    state["peak"] = max(state["peak"], eq)
    if p.get("max_dd") and not state["halted"] and eq < state["peak"] * (1 - p["max_dd"]):
        close_all(state, t, reason="fren")
        state["halted"] = True
        state["halt_reason"] = f"Hesap zirveden %{int(p['max_dd'] * 100)} düştü, bot durdu"

    # 4) yeni sinyaller (bir sonraki mumda işlem)
    if not state["halted"]:
        _signals(state, ctx, t, bar)
    state["last_ts"] = t


def _btc_ok(ctx, t):
    X, I = ctx["idx"].get("BTC", {}), ctx["ind"].get("BTC")
    if t not in X:
        return True
    i = X[t]
    e = I["ema200"][i]
    return isn(e) or I["c"][i] > e


def _signals(state, ctx, t, bar):
    p = state["params"]
    D, I, X = ctx["data"], ctx["ind"], ctx["idx"]
    btc_ok = (not p.get("btc_filter")) or _btc_ok(ctx, t)
    blocked = external.entry_blocked(p, t + bar)
    live = [s for s in D if t in X[s] and X[s][t] >= 1]

    if p["mode"] == "rotation":
        if (t // HOUR_MS) % 24 != p["rot_hour"]:
            return
        ranked = []
        for s in live:
            i = X[s][t]
            m, e = I[s]["mom"][i], I[s]["ema200"][i]
            if not isn(m, e) and I[s]["c"][i] > e and m > 0:
                ranked.append((m, s))
        ranked.sort(reverse=True)
        target = [s for _, s in ranked[:p["rot_k"]]] if btc_ok else []
        state["pending_exit"] = [s for s in state["pos"] if s not in target]
        if blocked or t < state["pause_until"]:
            return
        for s in target:
            if s not in state["pos"]:
                a = I[s]["atr"][X[s][t]]
                if not isn(a):
                    state["pending"][s] = {"atr": a, "why": "momentum ilk " + str(p["rot_k"])}
        return

    free = p["max_pos"] - len(state["pos"])
    if free <= 0 or not btc_ok or blocked or t < state["pause_until"]:
        return
    moms = sorted((I[s]["mom"][X[s][t]], s) for s in live if not isn(I[s]["mom"][X[s][t]]))
    cut = moms[int(len(moms) * 2 / 3)][0] if moms else math.inf
    btc_m = I["BTC"]["mom"][X["BTC"][t]] if "BTC" in X and t in X["BTC"] else NAN
    cands = []
    for s in live:
        if s in state["pos"]:
            continue
        i = X[s][t]
        ind = I[s]
        a = ind["atr"][i]
        if isn(a):
            continue
        m = ind["mom"][i]
        if p["mode"] == "score":
            sc, why = score_coin(ind, i, btc_m, not isn(m) and m >= cut)
            if sc is not None and sc >= p["score_min"]:
                cands.append((sc, m if not isn(m) else -9, s, a, f"puan {sc}/8: " + ", ".join(why)))
        else:  # scan: Donchian kırılımı + trend
            c, e, d = ind["c"][i], ind["ema200"][i], ind["dc_hi"][i - 1]
            if not isn(e, d) and c > e and c > d:
                cands.append((1, m if not isn(m) else -9, s, a, f"{p['dc_len']}s zirve kırılımı"))
    cands.sort(reverse=True)
    for sc, m, s, a, why in cands[:free]:
        state["pending"][s] = {"atr": a, "why": why}


# ---------------------------------------------------------------- simülasyon
def simulate(ctx, p, t_from, t_to, start_equity=100.0):
    st = new_state(start_equity, p, ctx["universe"])
    st["last_ts"] = t_from - 1
    curve = []
    for t in ctx["times"]:
        if t < t_from:
            continue
        if t >= t_to:
            break
        process_time(st, ctx, t)
        curve.append(exit_value(st))
    return st, curve


def exit_value(st):
    p = st["params"]
    return st["cash"] + sum(ps["qty"] * st["last_close"].get(s, ps["entry_px"]) * (1 - ps["slip"]) * (1 - p["fee"])
                            for s, ps in st["pos"].items())


def describe_open(state, price=None):
    if not state["pos"]:
        return None
    parts = []
    for s, ps in state["pos"].items():
        px = state["last_close"].get(s, ps["entry_px"])
        parts.append(f"{s} {(px / ps['entry_px'] - 1) * 100:+.1f}%")
    return ", ".join(parts)
