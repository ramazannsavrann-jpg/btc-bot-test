"""
Strateji turnuvası: tüm adaylar aynı gerçek veride, aynı maliyetlerle yarışır.

Her aday için:
  1) Eğitim (verinin ilk %70'i): küçük ayar tablosundan en iyi ayar seçilir.
  2) Sınav (son %30, aday bu veriyi HİÇ görmedi): seçilen ayarla 100$ simülasyonu.
  3) Sınav döneminde her gün başlayan 7 günlük 100$ denemeleri (canlı testteki %10 fren dahil).
Sıralama SADECE sınav sonucuna göre yapılır: getiri / en büyük düşüş, yeterli işlem sıklığı şartıyla.
"""
from __future__ import annotations

import itertools
import json
import math
import os
import statistics
import time
from datetime import datetime, timezone

from . import engines, strategy as S
from .candidates import CANDIDATES

WARMUP = 260
TRAIN_FRAC = 0.7
MIN_TRADES_PER_WEEK = 1.5   # "sık işlem" şartı (sınav döneminde)
BAR_PER_WEEK = {"1h": 24 * 7, "15m": 96 * 7}
BAR_PER_DAY = {"1h": 24, "15m": 96}


def fmt(ts):
    return datetime.fromtimestamp(ts / 1000, timezone.utc).strftime("%Y-%m-%d")


def exit_value(st, px):
    p = st["params"]
    return st["cash"] + st["qty"] * px * (1 - p["slip"]) * (1 - p["fee"])


def max_dd(curve):
    peak, mdd = -math.inf, 0.0
    for e in curve:
        peak = max(peak, e)
        mdd = max(mdd, (peak - e) / peak if peak > 0 else 0)
    return mdd * 100


def simulate(candles, params, i_from, i_to=None, ind=None):
    """[i_from, i_to) aralığında işlem yapar; göstergeler tüm veriden (geçmişe bakar)."""
    E = engines.get(params)
    i_to = i_to or len(candles)
    ind = ind if ind is not None else E.indicators(candles, params)
    st = E.new_state(100.0, params)
    st["last_ts"] = candles[i_from - 1][0]
    curve = []
    for i in range(i_from, i_to):
        E.process_bar(st, candles, ind, i)
        curve.append(exit_value(st, candles[i][4]))
    return st, curve


def summary(st, curve, candles, i_from, i_to, bar_week):
    tr = st["trades"]
    wins = sum(t["pnl"] > 0 for t in tr)
    gp = sum(t["pnl"] for t in tr if t["pnl"] > 0)
    gl = -sum(t["pnl"] for t in tr if t["pnl"] <= 0)
    weeks = (i_to - i_from) / bar_week
    end = curve[-1] if curve else 100.0
    return {
        "son_bakiye": round(end, 2),
        "getiri_pct": round(end - 100, 2),
        "islem": len(tr),
        "haftalik_islem": round(len(tr) / weeks, 2) if weeks else 0,
        "basari_pct": round(wins / len(tr) * 100, 1) if tr else 0.0,
        "kar_faktoru": round(gp / gl, 2) if gl > 0 else None,
        "max_dusus_pct": round(max_dd(curve), 2),
        "al_tut_pct": round((candles[i_to - 1][4] / candles[i_from][1] - 1) * 100, 2),
    }


def weekly(candles, params, i_from, ind, iv):
    E = engines.get(params)
    p = dict(params, max_dd=0.10)
    week, day = BAR_PER_WEEK[iv], BAR_PER_DAY[iv]
    ends, hold, ntr = [], [], []
    i = i_from
    while i + week <= len(candles):
        st = E.new_state(100.0, p)
        st["last_ts"] = candles[i - 1][0]
        for j in range(i, i + week):
            E.process_bar(st, candles, ind, j)
        px = candles[i + week - 1][4]
        ends.append(exit_value(st, px))
        hold.append(100.0 * px / candles[i][1])
        ntr.append(len(st["trades"]))
        i += day
    return ends, hold, ntr


def dist(v):
    if not v:
        return {}
    s = sorted(v)
    q = lambda f: s[min(len(s) - 1, int(f * (len(s) - 1) + 0.5))]  # noqa: E731
    return {"pencere": len(s), "ortanca": round(statistics.median(s), 2),
            "ortalama": round(statistics.mean(s), 2), "en_kotu": round(s[0], 2),
            "en_iyi": round(s[-1], 2), "kotu_yuzde10": round(q(0.1), 2),
            "iyi_yuzde10": round(q(0.9), 2),
            "kazandiran_hafta_pct": round(sum(x > 100 for x in s) / len(s) * 100, 1)}


def score(sm):
    return sm["getiri_pct"] / max(sm["max_dusus_pct"], 2.0)


def run_candidate(cand, candles, iv):
    n = len(candles)
    split = int(n * TRAIN_FRAC)
    base = dict(S.DEFAULT_PARAMS, **cand["params"])
    if base.get("engine") == "grid":
        from .grid import DEFAULT_PARAMS as G
        base = dict(G, **cand["params"])
    keys = list(cand.get("grid", {}).keys())
    combos = list(itertools.product(*cand["grid"].values())) if keys else [()]
    bw = BAR_PER_WEEK[iv]
    best, best_sc, table = None, -math.inf, []
    any_best, any_sc = base, -math.inf
    for vals in combos:
        p = dict(base, **dict(zip(keys, vals)))
        E = engines.get(p)
        ind = E.indicators(candles[:split], p)
        st, curve = simulate(candles[:split], p, WARMUP, split, ind)
        sm = summary(st, curve, candles, WARMUP, split, bw)
        # eğitimde de en az haftada 1 işlem şartı
        sc = score(sm) if sm["haftalik_islem"] >= 1.0 else -math.inf
        table.append({**dict(zip(keys, vals)), "getiri_pct": sm["getiri_pct"],
                      "haftalik_islem": sm["haftalik_islem"], "max_dusus_pct": sm["max_dusus_pct"]})
        if sc > best_sc:
            best, best_sc = p, sc
        if score(sm) > any_sc:   # hiçbiri sıklık şartını sağlamazsa yedek
            any_best, any_sc = p, score(sm)
    best = best or any_best
    E = engines.get(best)
    ind = E.indicators(candles, best)
    st, curve = simulate(candles, best, split, n, ind)
    oos = summary(st, curve, candles, split, n, bw)
    # dayanıklılık: 2 kat komisyon + kayma
    p2 = dict(best, fee=best["fee"] * 2, slip=best["slip"] * 2)
    st2, curve2 = simulate(candles, p2, split, n, ind)
    oos2 = summary(st2, curve2, candles, split, n, bw)
    ends, hold, ntr = weekly(candles, best, split, ind, iv)
    return {
        "id": cand["id"], "baslik": cand["title"], "aciklama": cand["desc"], "zaman_dilimi": iv,
        "secilen_ayar": {k: best.get(k) for k in keys},
        "params": best,
        "sinav": oos,
        "sinav_2x_maliyet": oos2,
        "haftalik_100": dist(ends),
        "haftalik_al_tut": dist(hold),
        "haftalik_islem_ortanca": statistics.median(ntr) if ntr else 0,
        "egitim_tablosu": table,
        "uygun": oos["haftalik_islem"] >= MIN_TRADES_PER_WEEK,
        "puan": round((score(oos) + score(oos2)) / 2, 3),
        "son_islemler": st["trades"][-10:],
    }


def run(data_by_iv, out_dir, log=print):
    results = []
    for cand in CANDIDATES:
        iv = cand["params"].get("interval", "1h")
        candles, src = data_by_iv[iv]
        t = time.time()
        r = run_candidate(cand, candles, iv)
        r["kaynak"] = src
        results.append(r)
        log(f"{cand['id']:<14} {iv:>3}  sınav {r['sinav']['getiri_pct']:+6.2f}%  "
            f"düşüş {r['sinav']['max_dusus_pct']:5.2f}%  haftada {r['sinav']['haftalik_islem']:5.2f} işlem  "
            f"puan {r['puan']:+.3f}  ({time.time() - t:.0f} sn)")
    ranked = sorted(results, key=lambda r: (r["uygun"], r["puan"]), reverse=True)
    any_c = next(iter(data_by_iv.values()))[0]
    split = int(len(any_c) * TRAIN_FRAC)
    meta = {"egitim": f"{fmt(any_c[0][0])} → {fmt(any_c[split - 1][0])}",
            "sinav": f"{fmt(any_c[split][0])} → {fmt(any_c[-1][0])}",
            "olusturma": datetime.now(timezone.utc).isoformat(timespec="minutes")}
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "turnuva.json"), "w", encoding="utf-8") as f:
        json.dump({"meta": meta, "sonuclar": ranked}, f, ensure_ascii=False, indent=1)
    with open(os.path.join(out_dir, "TURNUVA.md"), "w", encoding="utf-8") as f:
        f.write(markdown(meta, ranked))
    return ranked


def markdown(meta, ranked):
    L = ["# 🏆 Strateji Turnuvası", "",
         f"Ayarlar **{meta['egitim']}** döneminde seçildi; sıralama botların **hiç görmediği** "
         f"**{meta['sinav']}** dönemindeki sonuca göre. Komisyon %0,1 + kayma %0,05 dahil, kaldıraç yok.", "",
         f"Şart: sınav döneminde haftada en az {MIN_TRADES_PER_WEEK} işlem. Puan = getiri ÷ en büyük düşüş; "
         "normal ve 2 kat komisyonlu sonucun ortalaması (komisyona dayanıksız botlar geriye düşer).", "",
         "| # | Bot | Mum | 100$ → | 2× komisyonla | Haftada işlem | Başarı | En büyük düşüş | Al-tut | 1 haftada tipik | Puan |",
         "|---|---|---|---|---|---|---|---|---|---|---|"]
    for k, r in enumerate(ranked, 1):
        s, w = r["sinav"], r["haftalik_100"]
        mark = "" if r["uygun"] else " ⚠️az işlem"
        L.append(f"| {k} | {r['baslik']}{mark} | {r['zaman_dilimi']} | {s['son_bakiye']}$ | "
                 f"{r['sinav_2x_maliyet']['son_bakiye']}$ | "
                 f"{s['haftalik_islem']} | %{s['basari_pct']} | %{s['max_dusus_pct']} | "
                 f"%{s['al_tut_pct']} | {w.get('ortanca')}$ | {r['puan']} |")
    L += ["", "## Botlar ne yapıyor?", ""]
    for r in ranked:
        w = r["haftalik_100"]
        L.append(f"- **{r['baslik']}** — {r['aciklama']} Seçilen ayar: `{r['secilen_ayar']}`. "
                 f"1 hafta 100$: en kötü {w.get('en_kotu')}$, en iyi {w.get('en_iyi')}$, "
                 f"kazandıran hafta %{w.get('kazandiran_hafta_pct')}.")
    L += ["", "_Geçmiş sonuç geleceği garanti etmez. Sanal test; yatırım tavsiyesi değildir._", ""]
    return "\n".join(L)
