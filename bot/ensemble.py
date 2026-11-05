"""
Ansambl motoru: aynı stratejinin farklı ayarlı K kopyası, paranın 1/K'sı ile ayrı ayrı çalışır.
Tek bir "en iyi" ayara bahis yapmaz (ezber riskini azaltır). Sonuç = kopyaların toplamı.
"""
from __future__ import annotations

from . import strategy as S


def sub_params(p):
    shared = {k: v for k, v in p.items() if k not in ("engine", "subs")}
    return [dict(S.DEFAULT_PARAMS, **shared, **sp) for sp in p["subs"]]


def new_state(start_equity, params):
    st = S.new_state(start_equity, params)
    sp = sub_params(params)
    st["subs"] = [S.new_state(start_equity / len(sp), x) for x in sp]
    return st


def indicators(candles, p):
    return [S.indicators(candles, x) for x in sub_params(p)]


def _sync(st):
    st["cash"] = sum(s["cash"] for s in st["subs"])
    st["qty"] = sum(s["qty"] for s in st["subs"])


def process_bar(st, candles, ind, i):
    if candles[i][0] <= st["last_ts"]:
        return
    for k, sub in enumerate(st["subs"]):
        if sub["last_ts"] < st["last_ts"]:
            sub["last_ts"] = st["last_ts"]
        n = len(sub["trades"])
        S.process_bar(sub, candles, ind[k], i)
        st["trades"].extend(sub["trades"][n:])
    _sync(st)
    st["peak"] = max(st["peak"], S.equity(st, candles[i][4]))
    st["halted"] = all(s["halted"] for s in st["subs"])
    st["last_ts"] = candles[i][0]
    st["last_close"] = candles[i][4]


def close_all(st, ts, px, reason):
    for sub in st["subs"]:
        n = len(sub["trades"])
        S.close_all(sub, ts, px, reason)
        st["trades"].extend(sub["trades"][n:])
    _sync(st)


equity = S.equity
stats = S.stats


def describe_open(st, price):
    open_ = [s for s in st["subs"] if s["position"]]
    if not open_:
        return None
    unreal = sum(s["position"]["qty"] * price - s["position"]["cost"] for s in open_)
    return f"{len(open_)}/{len(st['subs'])} kopya pozisyonda, şu an {unreal:+.2f}$"
