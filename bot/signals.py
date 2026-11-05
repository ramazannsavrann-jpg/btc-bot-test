"""
Strateji sinyalleri (giriş/çıkış kuralları). Hepsi aynı işlem yönetimini kullanır:
ATR stop + hedef + kâr koruma + süre stopu + risk tabanlı pozisyon + komisyon/kayma
(bkz. strategy.py). Böylece turnuvada stratejiler adil şekilde karşılaştırılır.

Her sinyal:
  indicators(candles, p, base) -> dict   ek göstergeler (base: ema_fast, ema_slow, rsi, atr)
  entry(ind, i, candles, p)    -> bool   i. mum kapanışında alım sinyali var mı
  exit(ind, i, candles, p, pos)-> str|None  göstergeye dayalı çıkış sebebi
Sinyaller sadece i ve öncesindeki mumlara bakar (geleceği görmez).
"""
from __future__ import annotations

import math

from .strategy import atr, ema, rsi

NAN = math.nan


def isn(*xs):
    return any(x is None or (isinstance(x, float) and math.isnan(x)) for x in xs)


# ---------------------------------------------------------------- yardımcılar
def sma(v, n):
    out, s = [NAN] * len(v), 0.0
    for i, x in enumerate(v):
        s += x
        if i >= n:
            s -= v[i - n]
        if i >= n - 1:
            out[i] = s / n
    return out


def stdev(v, n):
    out = [NAN] * len(v)
    m = sma(v, n)
    for i in range(n - 1, len(v)):
        w = v[i - n + 1:i + 1]
        out[i] = math.sqrt(sum((x - m[i]) ** 2 for x in w) / n)
    return out


def highest(v, n):
    """i dahil son n değerin en yükseği."""
    from collections import deque
    out, dq = [NAN] * len(v), deque()
    for i, x in enumerate(v):
        while dq and v[dq[-1]] <= x:
            dq.pop()
        dq.append(i)
        if dq[0] <= i - n:
            dq.popleft()
        if i >= n - 1:
            out[i] = v[dq[0]]
    return out


def lowest(v, n):
    return [(-x if not math.isnan(x) else x) for x in highest([-y for y in v], n)]


def cols(candles):
    return ([c[1] for c in candles], [c[2] for c in candles],
            [c[3] for c in candles], [c[4] for c in candles], [c[5] for c in candles])


def cross_up(a, b, i):
    return not isn(a[i - 1], b[i - 1], a[i], b[i]) and a[i - 1] <= b[i - 1] and a[i] > b[i]


def cross_dn(a, b, i):
    return not isn(a[i - 1], b[i - 1], a[i], b[i]) and a[i - 1] >= b[i - 1] and a[i] < b[i]


class Sig:
    title = ""

    def indicators(self, candles, p, base):
        return {}

    def entry(self, ind, i, candles, p):
        return False

    def exit(self, ind, i, candles, p, pos):
        return None


REGISTRY: dict[str, Sig] = {}


def register(name):
    def deco(cls):
        REGISTRY[name] = cls()
        return cls
    return deco


def get(p):
    return REGISTRY[p.get("signal", "pullback")]


# ---------------------------------------------------------------- sinyaller
@register("pullback")
class Pullback(Sig):
    title = "Trend + RSI geri çekilme"

    def entry(self, ind, i, candles, p):
        c = candles[i][4]
        ef, es, r, rp = ind["ema_fast"][i], ind["ema_slow"][i], ind["rsi"][i], ind["rsi"][i - 1]
        if isn(ef, es, r, rp):
            return False
        trend = c > es and ef > es
        up = rp < p["rsi_entry"] <= r
        n = int(p.get("breakout_len") or 0)
        brk = n > 0 and i > n and r < 75 and c > max(x[2] for x in candles[i - n:i])
        return trend and (up or brk)


@register("ema_cross")
class EmaCross(Sig):
    title = "EMA 9/21 kesişimi"

    def indicators(self, candles, p, base):
        cl = [c[4] for c in candles]
        return {"x_fast": ema(cl, p.get("x_fast", 9)), "x_slow": ema(cl, p.get("x_slow", 21))}

    def entry(self, ind, i, candles, p):
        c, es, r = candles[i][4], ind["ema_slow"][i], ind["rsi"][i]
        return (not isn(es, r) and c > es and r < 75
                and cross_up(ind["x_fast"], ind["x_slow"], i))

    def exit(self, ind, i, candles, p, pos):
        return "ters kesişim" if cross_dn(ind["x_fast"], ind["x_slow"], i) else None


def supertrend_dir(highs, lows, closes, length, mult):
    """Standart Supertrend yönü: 1 yukarı, -1 aşağı, 0 yok."""
    n = len(closes)
    a = atr(highs, lows, closes, length)
    out = [0] * n
    up = dn = None
    d = 1
    for i in range(n):
        if math.isnan(a[i]):
            continue
        hl2 = (highs[i] + lows[i]) / 2
        bu, bd = hl2 - mult * a[i], hl2 + mult * a[i]
        if up is None:
            up, dn = bu, bd
            out[i] = d
            continue
        pu, pd = up, dn
        up = max(bu, pu) if closes[i - 1] > pu else bu
        dn = min(bd, pd) if closes[i - 1] < pd else bd
        if d == -1 and closes[i] > pd:
            d = 1
        elif d == 1 and closes[i] < pu:
            d = -1
        out[i] = d
    return out


@register("supertrend")
class Supertrend(Sig):
    title = "Supertrend (TradingView)"

    def indicators(self, candles, p, base):
        _, h, l, c, _ = cols(candles)
        return {"st_dir": supertrend_dir(h, l, c, p.get("st_len", 10), p.get("st_mult", 3.0))}

    def entry(self, ind, i, candles, p):
        d = ind["st_dir"]
        return d[i - 1] == -1 and d[i] == 1

    def exit(self, ind, i, candles, p, pos):
        return "supertrend aşağı döndü" if ind["st_dir"][i] == -1 else None


@register("rsi2")
class Rsi2(Sig):
    title = "Connors RSI(2) dönüşü"

    def indicators(self, candles, p, base):
        cl = [c[4] for c in candles]
        return {"rsi2": rsi(cl, 2), "sma_trend": sma(cl, p.get("trend_len", 200)),
                "sma_exit": sma(cl, p.get("exit_len", 5))}

    def entry(self, ind, i, candles, p):
        c, r, t = candles[i][4], ind["rsi2"][i], ind["sma_trend"][i]
        return not isn(r, t) and c > t and r < p.get("rsi2_entry", 10)

    def exit(self, ind, i, candles, p, pos):
        m = ind["sma_exit"][i]
        return "ortalamaya döndü" if not isn(m) and candles[i][4] > m else None


@register("bb_revert")
class BBRevert(Sig):
    title = "Bollinger + RSI dönüşü"

    def indicators(self, candles, p, base):
        cl = [c[4] for c in candles]
        n, k = p.get("bb_len", 20), p.get("bb_k", 2.0)
        m, sd = sma(cl, n), stdev(cl, n)
        return {"bb_mid": m, "bb_lo": [a - k * b if not isn(a, b) else NAN for a, b in zip(m, sd)]}

    def entry(self, ind, i, candles, p):
        c, lo, r = candles[i][4], ind["bb_lo"][i], ind["rsi"][i]
        es = ind["ema_slow"][i]
        trend_ok = (not p.get("bb_trend")) or (not isn(es) and c > es)
        return not isn(lo, r) and c < lo and r < p.get("bb_rsi", 30) and trend_ok

    def exit(self, ind, i, candles, p, pos):
        m = ind["bb_mid"][i]
        return "orta banda döndü" if not isn(m) and candles[i][4] > m else None


@register("donchian")
class Donchian(Sig):
    title = "Donchian kırılımı (kaplumbağa)"

    def indicators(self, candles, p, base):
        _, h, l, _, _ = cols(candles)
        return {"dc_hi": highest(h, p.get("dc_entry", 20)), "dc_lo": lowest(l, p.get("dc_exit", 10))}

    def entry(self, ind, i, candles, p):
        prev = ind["dc_hi"][i - 1]  # önceki N mumun zirvesi (bu mum hariç)
        return not isn(prev) and candles[i][4] > prev

    def exit(self, ind, i, candles, p, pos):
        prev = ind["dc_lo"][i - 1]
        return "kanal altı" if not isn(prev) and candles[i][4] < prev else None


def ut_trail(closes, a, key):
    """UT Bot Alerts ATR iz süren stop çizgisi."""
    n = len(closes)
    out = [NAN] * n
    prev = None
    for i in range(n):
        if math.isnan(a[i]):
            continue
        loss = key * a[i]
        c = closes[i]
        if prev is None:
            prev = c - loss
        else:
            pc = closes[i - 1]
            if c > prev and pc > prev:
                prev = max(prev, c - loss)
            elif c < prev and pc < prev:
                prev = min(prev, c + loss)
            elif c > prev:
                prev = c - loss
            else:
                prev = c + loss
        out[i] = prev
    return out


@register("ut_bot")
class UTBot(Sig):
    title = "UT Bot Alerts (TradingView)"

    def indicators(self, candles, p, base):
        _, h, l, c, _ = cols(candles)
        a = atr(h, l, c, p.get("ut_atr", 10))
        return {"ut": ut_trail(c, a, p.get("ut_key", 1.0)), "cl": c}

    def entry(self, ind, i, candles, p):
        return cross_up(ind["cl"], ind["ut"], i)

    def exit(self, ind, i, candles, p, pos):
        return "UT sat sinyali" if cross_dn(ind["cl"], ind["ut"], i) else None


@register("ssl")
class SSL(Sig):
    title = "SSL Channel (TradingView)"

    def indicators(self, candles, p, base):
        _, h, l, c, _ = cols(candles)
        n = p.get("ssl_len", 10)
        sh, sl = sma(h, n), sma(l, n)
        hlv, d = [0] * len(c), 0
        for i in range(len(c)):
            if isn(sh[i], sl[i]):
                continue
            d = 1 if c[i] > sh[i] else (-1 if c[i] < sl[i] else d)
            hlv[i] = d
        return {"ssl_dir": hlv}

    def entry(self, ind, i, candles, p):
        d = ind["ssl_dir"]
        return d[i - 1] == -1 and d[i] == 1

    def exit(self, ind, i, candles, p, pos):
        return "SSL aşağı döndü" if ind["ssl_dir"][i] == -1 else None


def linreg_end(v, n):
    """Son n değerin doğrusal regresyon çizgisinin son noktası (TradingView linreg(x, n, 0))."""
    out = [NAN] * len(v)
    xm = (n - 1) / 2
    sxx = sum((x - xm) ** 2 for x in range(n))
    for i in range(n - 1, len(v)):
        w = v[i - n + 1:i + 1]
        if any(math.isnan(y) for y in w):
            continue
        ym = sum(w) / n
        b = sum((x - xm) * (y - ym) for x, y in enumerate(w)) / sxx
        out[i] = ym + b * (n - 1 - xm)
    return out


@register("squeeze")
class Squeeze(Sig):
    title = "Squeeze Momentum (LazyBear)"

    def indicators(self, candles, p, base):
        _, h, l, c, _ = cols(candles)
        n = p.get("sq_len", 20)
        m, sd = sma(c, n), stdev(c, n)
        tr = [h[0] - l[0]] + [max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1]))
                              for i in range(1, len(c))]
        rm = sma(tr, n)
        on = [False] * len(c)
        for i in range(len(c)):
            if not isn(m[i], sd[i], rm[i]):
                on[i] = (m[i] - 2 * sd[i] > m[i] - p.get("sq_kc", 1.5) * rm[i]
                         and m[i] + 2 * sd[i] < m[i] + p.get("sq_kc", 1.5) * rm[i])
        hh, ll = highest(h, n), lowest(l, n)
        src = [c[i] - ((hh[i] + ll[i]) / 2 + m[i]) / 2 if not isn(hh[i], ll[i], m[i]) else NAN
               for i in range(len(c))]
        return {"sq_on": on, "sq_val": linreg_end(src, n), "ema50": ema(c, 50)}

    def entry(self, ind, i, candles, p):
        k = p.get("sq_min_bars", 6)
        if i < k + 1 or ind["sq_on"][i] or not all(ind["sq_on"][i - k:i]):
            return False
        v, vp, e = ind["sq_val"][i], ind["sq_val"][i - 1], ind["ema50"][i]
        return not isn(v, vp, e) and v > 0 and v > vp and candles[i][4] > e

    def exit(self, ind, i, candles, p, pos):
        v, vp = ind["sq_val"][i], ind["sq_val"][i - 1]
        return "momentum zayıfladı" if not isn(v, vp) and v < vp else None


@register("binh_cluc")
class BinHCluc(Sig):
    title = "CombinedBinHAndCluc (Freqtrade)"

    def indicators(self, candles, p, base):
        _, h, l, c, v = cols(candles)
        m40, sd40 = sma(c, 40), stdev(c, 40)
        tp = [(a + b + d) / 3 for a, b, d in zip(h, l, c)]
        m20, sd20 = sma(tp, 20), stdev(tp, 20)
        return {"m40": m40, "lo40": [a - 2 * b if not isn(a, b) else NAN for a, b in zip(m40, sd40)],
                "m20": m20, "lo20": [a - 2 * b if not isn(a, b) else NAN for a, b in zip(m20, sd20)],
                "ema50": ema(c, 50), "vmean": sma(v, 30)}

    def entry(self, ind, i, candles, p):
        l, c, v = candles[i][3], candles[i][4], candles[i][5]
        pc = candles[i - 1][4]
        lo_prev, m40 = ind["lo40"][i - 1], ind["m40"][i]
        lo40 = ind["lo40"][i]
        binh = False
        if not isn(lo_prev, m40, lo40):
            bbdelta = abs(m40 - lo40)
            binh = (lo_prev > 0 and bbdelta > c * 0.008 and abs(c - pc) > c * 0.0175
                    and abs(c - l) < bbdelta * 0.25 and c < lo_prev and c <= pc)
        e, lo20, vm = ind["ema50"][i], ind["lo20"][i], ind["vmean"][i - 1]
        cluc = (not isn(e, lo20, vm) and c < e and c < 0.985 * lo20 and v < vm * 20)
        return binh or cluc

    def exit(self, ind, i, candles, p, pos):
        m = ind["m20"][i]
        c = candles[i][4]
        in_profit = c * (1 - p["slip"]) * (1 - p["fee"]) > pos["cost"] / pos["qty"]
        return "orta banda döndü (kârda)" if not isn(m) and c > m and in_profit else None


@register("late_utc")
class LateUTC(Sig):
    title = "Gece saati etkisi (kontrol)"

    def indicators(self, candles, p, base):
        return {"ema168": ema([c[4] for c in candles], 168)}

    def entry(self, ind, i, candles, p):
        hour = (candles[i][0] // 3_600_000) % 24
        e = ind["ema168"][i]
        return hour == 21 and not isn(e) and candles[i][4] > e   # 22:00 UTC açılışında al

    def exit(self, ind, i, candles, p, pos):
        return "gece 00:00 UTC" if (candles[i][0] // 3_600_000) % 24 == 23 else None


@register("fear_dip")
class FearDip(Sig):
    title = "Aşırı Korkuda Dip Alımı"

    def indicators(self, candles, p, base):
        return {"ema20": ema([c[4] for c in candles], 20), "cl": [c[4] for c in candles]}

    def entry(self, ind, i, candles, p):
        from . import external
        v = external.fg_value(candles[i][0])
        # aşırı korku + fiyat 20'lik ortalamanın üstüne dönüyor (düşüş duruluyor)
        return v is not None and v <= p.get("fg_buy", 25) and cross_up(ind["cl"], ind["ema20"], i)


def pivots(v, k, is_high):
    """k mum sağı/solu doğrulanmış tepe/dip. (j, değer, onay_indeksi=j+k) listesi."""
    out = []
    for j in range(k, len(v) - k):
        w = v[j - k:j + k + 1]
        if (v[j] == max(w)) if is_high else (v[j] == min(w)):
            out.append((j, v[j], j + k))
    return out


@register("wedge")
class Wedge(Sig):
    title = "Takoz / Üçgen Kırılımı"

    def indicators(self, candles, p, base):
        _, h, l, c, v = cols(candles)
        k = p.get("pivot_k", 4)
        look = p.get("pattern_bars", 120)
        ph, pl = pivots(h, k, True), pivots(l, k, False)
        n = len(c)
        upper = [NAN] * n
        hi_ok = [False] * n
        a = b = 0
        for i in range(n):
            # sadece i anında DOĞRULANMIŞ pivotlar (onay_indeksi <= i) -> geleceği görmez
            while a < len(ph) and ph[a][2] <= i:
                a += 1
            while b < len(pl) and pl[b][2] <= i:
                b += 1
            if a < 2 or b < 2:
                continue
            (h1i, h1, _), (h2i, h2, _) = ph[a - 2], ph[a - 1]
            (l1i, l1, _), (l2i, l2, _) = pl[b - 2], pl[b - 1]
            if i - min(h1i, l1i) > look:
                continue
            su = (h2 - h1) / (h2i - h1i)
            sl = (l2 - l1) / (l2i - l1i)
            up_i = h2 + su * (i - h2i)
            lo_i = l2 + sl * (i - l2i)
            # daralan formasyon: düşen takoz, simetrik/yükselen üçgen (üst çizgi yatay ya da düşen)
            converging = su < sl and su <= 0.0002 * c[i] and up_i > lo_i
            upper[i] = up_i
            hi_ok[i] = converging
        return {"w_up": upper, "w_ok": hi_ok, "cl": c, "vol_ma": sma(v, 20), "vol": v}

    def entry(self, ind, i, candles, p):
        if not ind["w_ok"][i] or isn(ind["w_up"][i], ind["w_up"][i - 1]):
            return False
        brk = ind["cl"][i] > ind["w_up"][i] and ind["cl"][i - 1] <= ind["w_up"][i - 1]
        if brk and p.get("vol_confirm"):
            vm = ind["vol_ma"][i]
            brk = not isn(vm) and ind["vol"][i] > vm * 1.2
        return brk


# ================================================================ klasik formasyonlar
# Hepsi sadece DOĞRULANMIŞ pivotları (tepe/dip, k mum sonra onaylanır) kullanır -> geleceği görmez.
# Her formasyon i. mumda bir "kırılım seviyesi" üretir; kapanış bu seviyeyi yukarı keserse alım.

def _confirmed(piv, i, ptr):
    while ptr < len(piv) and piv[ptr][2] <= i:
        ptr += 1
    return ptr


def pat_double_bottom(h, l, c, p):
    k, tol, recent = p.get("pivot_k", 4), p.get("pat_tol", 0.015), p.get("pat_recent", 48)
    pl = pivots(l, k, False)
    out, b = [NAN] * len(c), 0
    for i in range(len(c)):
        b = _confirmed(pl, i, b)
        if b < 2:
            continue
        (j1, l1, _), (j2, l2, _) = pl[b - 2], pl[b - 1]
        if j2 - j1 >= 10 and abs(l2 - l1) / l1 <= tol and i - j2 <= recent and min(l[j2:i + 1]) >= min(l1, l2) * 0.995:
            out[i] = max(h[j1:j2 + 1])          # boyun çizgisi
    return out


def pat_inv_hs(h, l, c, p):
    k, tol, recent = p.get("pivot_k", 4), p.get("pat_tol", 0.015) * 2, p.get("pat_recent", 48)
    pl = pivots(l, k, False)
    out, b = [NAN] * len(c), 0
    for i in range(len(c)):
        b = _confirmed(pl, i, b)
        if b < 3:
            continue
        (j1, l1, _), (j2, l2, _), (j3, l3, _) = pl[b - 3], pl[b - 2], pl[b - 1]
        if not (l2 < min(l1, l3) * 0.995 and abs(l3 - l1) / l1 <= tol and i - j3 <= recent):
            continue
        n1 = max(range(j1, j2 + 1), key=lambda x: h[x])
        n2 = max(range(j2, j3 + 1), key=lambda x: h[x])
        if n2 == n1:
            continue
        slope = (h[n2] - h[n1]) / (n2 - n1)
        out[i] = h[n2] + slope * (i - n2)       # eğimli boyun çizgisi
    return out


def pat_bull_flag(h, l, c, p):
    pole_bars, pole_pct = p.get("pole_bars", 12), p.get("pole_pct", 0.04)
    out = [NAN] * len(c)
    for i in range(pole_bars + 20, len(c)):
        for n in range(4, 17):                  # bayrak (dinlenme) uzunluğu
            s = i - n
            pole_lo = min(l[s - pole_bars:s])
            pole_h = c[s - 1] - pole_lo
            if pole_h <= 0 or pole_h / pole_lo < pole_pct:
                continue
            fh, fl = max(h[s:i]), min(l[s:i])
            # dar ve direğin yarısından fazla geri vermeyen dinlenme
            if fh - fl <= 0.5 * pole_h and fl >= c[s - 1] - 0.5 * pole_h:
                out[i] = fh
                break
    return out


def pat_resistance(h, l, c, p):
    k, tol, look = p.get("pivot_k", 4), p.get("res_tol", 0.004), p.get("pattern_bars", 120)
    ph = pivots(h, k, True)
    out, a = [NAN] * len(c), 0
    for i in range(len(c)):
        a = _confirmed(ph, i, a)
        if a < 2:
            continue
        last = ph[a - 1][1]
        touches = [v for (j, v, _) in ph[max(0, a - 8):a] if i - j <= look and abs(v - last) / last <= tol]
        if len(touches) >= 2:
            out[i] = max(touches)               # en az 2 kez test edilmiş yatay direnç
    return out


def pat_cup_handle(h, l, c, p):
    k = p.get("pivot_k", 4)
    ph = pivots(h, k, True)
    out, a = [NAN] * len(c), 0
    for i in range(len(c)):
        a = _confirmed(ph, i, a)
        if a < 2:
            continue
        (j1, h1, _), (j2, h2, _) = ph[a - 2], ph[a - 1]
        if j2 - j1 < 30 or abs(h2 - h1) / h1 > 0.03 or i - j2 > 30:
            continue
        low = min(l[j1:j2 + 1])
        depth = (max(h1, h2) - low) / max(h1, h2)
        if 0.05 <= depth <= 0.35 and min(l[j2:i + 1]) >= h2 - (h2 - low) / 2:   # kulp çanağın yarısından sığ
            out[i] = max(h1, h2)                # fincan ağzı
    return out


PATTERNS = {
    "ikili_dip": pat_double_bottom,
    "ters_obo": pat_inv_hs,
    "bayrak": pat_bull_flag,
    "direnc": pat_resistance,
    "fincan_kulp": pat_cup_handle,
}
PATTERN_TR = {"ikili_dip": "İkili dip (W)", "ters_obo": "Ters OBO", "bayrak": "Boğa bayrağı",
              "direnc": "Yatay direnç", "fincan_kulp": "Fincan-kulp", "takoz": "Takoz/üçgen"}


@register("pattern")
class Pattern(Sig):
    title = "Formasyon kırılımı"

    def indicators(self, candles, p, base):
        _, h, l, c, v = cols(candles)
        names = p.get("patterns", list(PATTERNS))
        lv = {n: PATTERNS[n](h, l, c, p) for n in names if n in PATTERNS}
        if "takoz" in names:
            w = REGISTRY["wedge"].indicators(candles, p, base)
            lv["takoz"] = [u if ok else NAN for u, ok in zip(w["w_up"], w["w_ok"])]
        return {"levels": lv, "cl": c, "vol": v, "vol_ma": sma(v, 20)}

    def entry(self, ind, i, candles, p):
        c, cp = ind["cl"][i], ind["cl"][i - 1]
        for name, lv in ind["levels"].items():
            a, b = lv[i], lv[i - 1]
            ref_prev = b if not isn(b) else a
            if not isn(a, ref_prev) and c > a * 1.001 and cp <= ref_prev * 1.001:
                if p.get("vol_confirm"):
                    vm = ind["vol_ma"][i]
                    if isn(vm) or ind["vol"][i] <= vm * 1.2:
                        continue
                return True
        return False
