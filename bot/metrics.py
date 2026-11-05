"""
Performans ölçümleri — günlük özsermaye eğrisinden (sadece kapanan işlemlerden değil).

  CAGR, en büyük düşüş, Calmar, Sharpe, Sortino (yıllık, 365 gün), toparlanma süresi,
  profit factor, işlem başı beklenti (expectancy), ort. kazanç / ort. kayıp, en uzun kayıp serisi,
  ort. tutma süresi, piyasada kalma oranı (exposure), haftalık işlem.
"""
from __future__ import annotations

import math
import statistics

DAY_MS = 86_400_000


def daily(points):
    """points: [(ts, özsermaye)] -> her UTC gününün son değeri."""
    out = {}
    for ts, e in points:
        out[ts // DAY_MS] = e
    return [out[k] for k in sorted(out)]


def returns(vals):
    return [vals[i] / vals[i - 1] - 1 for i in range(1, len(vals)) if vals[i - 1] > 0]


def max_dd_and_recovery(vals):
    peak, peak_i, mdd, longest, cur_start = -math.inf, 0, 0.0, 0, None
    for i, v in enumerate(vals):
        if v >= peak:
            if cur_start is not None:
                longest = max(longest, i - cur_start)
                cur_start = None
            peak, peak_i = v, i
        else:
            if cur_start is None:
                cur_start = peak_i
            mdd = max(mdd, (peak - v) / peak)
    if cur_start is not None:
        longest = max(longest, len(vals) - 1 - cur_start)
    return mdd, longest


def sharpe(r):
    if len(r) < 2:
        return 0.0
    sd = statistics.pstdev(r)
    return statistics.mean(r) / sd * math.sqrt(365) if sd > 0 else 0.0


def sortino(r):
    if len(r) < 2:
        return 0.0
    down = [min(0.0, x) for x in r]
    dd = math.sqrt(sum(x * x for x in down) / len(down))
    return statistics.mean(r) / dd * math.sqrt(365) if dd > 0 else 0.0


def trade_stats(trades):
    pnl = [t["pnl"] for t in trades]
    wins = [x for x in pnl if x > 0]
    losses = [x for x in pnl if x <= 0]
    streak = best = 0
    for x in pnl:
        streak = streak + 1 if x <= 0 else 0
        best = max(best, streak)
    hold = [(t["exit_ts"] - t["entry_ts"]) / 3_600_000 for t in trades]
    return {
        "islem": len(pnl),
        "basari_pct": round(len(wins) / len(pnl) * 100, 1) if pnl else 0.0,
        "kar_faktoru": round(sum(wins) / -sum(losses), 2) if losses and sum(losses) < 0 else None,
        "beklenti_islem_basi": round(statistics.mean(pnl), 4) if pnl else 0.0,
        "ort_kazanc": round(statistics.mean(wins), 4) if wins else 0.0,
        "ort_kayip": round(statistics.mean(losses), 4) if losses else 0.0,
        "en_uzun_kayip_serisi": best,
        "ort_tutma_saat": round(statistics.mean(hold), 1) if hold else 0.0,
    }


def full(points, trades, exposure_bars, total_bars):
    """points: [(ts, özsermaye)] bar bazında; exposure_bars: pozisyonda geçen bar sayısı."""
    d = daily(points)
    r = returns(d)
    start, end = (d[0], d[-1]) if d else (100.0, 100.0)
    days = max(1, len(d) - 1)
    cagr = (end / start) ** (365 / days) - 1 if start > 0 and end > 0 else -1.0
    mdd, rec = max_dd_and_recovery(d)
    weeks = days / 7
    out = {
        "getiri_pct": round((end / start - 1) * 100, 2),
        "cagr_pct": round(cagr * 100, 2),
        "max_dusus_pct": round(mdd * 100, 2),
        "calmar": round(cagr / mdd, 2) if mdd > 0 else None,
        "sharpe": round(sharpe(r), 2),
        "sortino": round(sortino(r), 2),
        "toparlanma_gun": rec,
        "piyasada_kalma_pct": round(exposure_bars / total_bars * 100, 1) if total_bars else 0.0,
        "haftalik_islem": round(len(trades) / weeks, 2) if weeks else 0.0,
        "gun": days,
    }
    out.update(trade_stats(trades))
    return out


def buy_hold(candles, t_from, t_to):
    seg = [c for c in candles if t_from <= c[0] < t_to]
    if not seg:
        return {}
    pts = [(c[0], 100.0 * c[4] / seg[0][1]) for c in seg]
    d = daily(pts)
    r = returns(d)
    mdd, _ = max_dd_and_recovery(d)
    days = max(1, len(d) - 1)
    end = pts[-1][1]
    cagr = (end / 100) ** (365 / days) - 1
    return {"getiri_pct": round(end - 100, 2), "cagr_pct": round(cagr * 100, 2),
            "max_dusus_pct": round(mdd * 100, 2), "sharpe": round(sharpe(r), 2),
            "sortino": round(sortino(r), 2), "calmar": round(cagr / mdd, 2) if mdd > 0 else None}
