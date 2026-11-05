"""
Grid bot (Binance "Spot Grid" mantığı, sadece alım yönü, kaldıraç yok) — 7/24 çalışır.

  * Başlangıç fiyatının ±range_pct aralığına n_levels eşit aralıklı seviye kurulur.
  * Fiyat bir seviyenin altına inince o seviyeden küçük bir parça BTC alınır,
    fiyat bir üst seviyeye çıkınca o parça satılır (her tur ~bir aralık kadar kâr).
  * Fiyat aralığın üstüne çıkar ve elde BTC kalmazsa ızgara yeni fiyata taşınır.
  * Fiyat aralığın stop_pct altına düşerse elde ne varsa satılır (zarar kesme),
    sonra ızgara yeni fiyata taşınır.
  * Aynı mumda alınan parça o mumda satılmaz (mum içi sırayı bilemeyiz = temkinli).
"""
from __future__ import annotations

from . import strategy as S

DEFAULT_PARAMS = {
    "engine": "grid",
    "interval": "15m",
    "n_levels": 10,
    "range_pct": 0.04,
    "stop_pct": 0.03,
    "fee": 0.001,
    "slip": 0.0005,
    "max_dd": None,
}


def indicators(candles, p):
    return {}


def new_state(start_equity, params):
    st = S.new_state(start_equity, params)
    st["grid"] = None   # {levels: [...], alloc}
    st["lots"] = []     # açık parçalar: {lvl, qty, cost, entry_ts, entry_px}
    return st


equity = S.equity
stats = S.stats


def _build(state, center):
    p = state["params"]
    n, r = p["n_levels"], p["range_pct"]
    lo, hi = center * (1 - r), center * (1 + r)
    step = (hi - lo) / n
    levels = [lo + k * step for k in range(n + 1)]
    state["grid"] = {"levels": levels, "alloc": S.equity(state, center) / n, "center": center}


def _sell_lot(state, lot, ts, px, reason):
    p = state["params"]
    exit_px = px * (1 - p["slip"])
    gross = lot["qty"] * exit_px
    fee = gross * p["fee"]
    state["cash"] += gross - fee
    state["qty"] -= lot["qty"]
    pnl = gross - fee - lot["cost"]
    state["trades"].append({
        "entry_ts": lot["entry_ts"], "exit_ts": ts,
        "entry_px": round(lot["entry_px"], 2), "exit_px": round(exit_px, 2),
        "qty": lot["qty"], "pnl": round(pnl, 4),
        "pnl_pct": round(pnl / lot["cost"] * 100, 3), "reason": reason,
    })
    state["lots"].remove(lot)
    if not state["lots"]:
        state["qty"] = 0.0


def close_all(state, ts, px, reason):
    for lot in list(state["lots"]):
        _sell_lot(state, lot, ts, px, reason)


def process_bar(state, candles, ind, i):
    p = state["params"]
    ts, o, h, l, c, _ = candles[i]
    if ts <= state["last_ts"]:
        return
    if state["grid"] is None:
        _build(state, o)

    from . import external
    no_buy = bool(external.entry_blocked(p, ts))
    if not state["halted"]:
        g = state["grid"]
        lv = g["levels"]
        held = {lot["lvl"] for lot in state["lots"]}
        new_lots = []
        # 1) alımlar: mumun düşüğünün değdiği, elde olmayan seviyeler (en üst seviye hariç)
        ref = state["last_close"] if state["last_close"] else o
        for k in range(len(lv) - 1):
            # bekleyen alım emri sadece fiyatın ALTINDAKİ seviyelerde durur
            if no_buy or k in held or lv[k] >= ref or l > lv[k]:
                continue
            px = min(o, lv[k]) * (1 + p["slip"])
            notional = min(g["alloc"], state["cash"] / (1 + p["fee"]))
            if notional < 5:
                break
            fee = notional * p["fee"]
            lot = {"lvl": k, "qty": notional / px, "cost": notional + fee, "entry_ts": ts, "entry_px": px}
            state["cash"] -= notional + fee
            state["qty"] += lot["qty"]
            state["lots"].append(lot)
            new_lots.append(lot)
        # 2) satışlar: önceki mumlardan kalan parçalar, bir üst seviyeye değince
        for lot in list(state["lots"]):
            if lot in new_lots:
                continue
            target = lv[lot["lvl"] + 1]
            if h >= target:
                _sell_lot(state, lot, ts, max(o, target), "grid kârı")
        # 3) zarar kesme / ızgarayı taşıma
        if c < lv[0] * (1 - p["stop_pct"]):
            close_all(state, ts, c, "grid stop")
            _build(state, c)
        elif c > lv[-1] and not state["lots"]:
            _build(state, c)

    eq = S.equity(state, c)
    state["peak"] = max(state["peak"], eq)
    if p.get("max_dd") and not state["halted"] and eq < state["peak"] * (1 - p["max_dd"]):
        close_all(state, ts, c, "fren")
        state["halted"] = True
        state["halt_reason"] = f"Hesap zirveden %{int(p['max_dd'] * 100)} düştü, bot durdu"

    state["last_ts"] = ts
    state["last_close"] = c


def describe_open(state, price):
    if not state["lots"]:
        return None
    unreal = sum(lot["qty"] * price - lot["cost"] for lot in state["lots"])
    g = state["grid"]["levels"]
    return (f"{len(state['lots'])} parça BTC elde, şu an {unreal:+.2f}$ "
            f"(ızgara {g[0]:,.0f}$ – {g[-1]:,.0f}$)")
