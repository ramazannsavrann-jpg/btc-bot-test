"""
Çoklu coin turnuvası: hacimce en büyük 30 coin (geçmiş evren, ilk ay hacmine göre), 24 ay, 1 saatlik mum.
Aynı kurallar: ayarlar ilk %70'te seçilir, sıralama hiç görülmemiş son %30'a ve 2 kat maliyet testine göre.
"""
from __future__ import annotations

import itertools
import json
import math
import os
import statistics
import time

from . import multi as M
from .tournament import dist, fmt, max_dd, score

MULTI_CANDIDATES = [
    {
        "id": "coin_skor",
        "title": "30 Coin Akıllı Skor",
        "desc": "30 coinin her birine trend, göreceli güç, momentum, kırılım, formasyon, hacim ve RSI'dan "
                "8 üzerinden puan verir; eşik üstündekilerin en iyilerine girer. BTC yönü, haber ve duygu freni açık.",
        "params": {"mode": "score", "fg_max": 85},
        "grid": {"score_min": [5, 6, 7], "max_pos": [3, 5]},
    },
    {
        "id": "coin_rotasyon",
        "title": "30 Coin Momentum Rotasyonu",
        "desc": "Her gün son günlerin en güçlü coinlerini (EMA200 üstünde olanlar) eşit ağırlıkla tutar, "
                "güçten düşeni satar. BTC düşüş trendindeyse nakde geçer.",
        "params": {"mode": "rotation", "stop_atr": 6.0},
        "grid": {"rot_k": [3, 5], "mom_len": [72, 168]},
    },
    {
        "id": "coin_donchian",
        "title": "30 Coin Donchian Tarayıcı",
        "desc": "30 coinde zirve kırılımı arar (trend + haber/duygu freni), en güçlü momentumlu olanlara girer.",
        "params": {"mode": "scan", "fg_max": 85},
        "grid": {"dc_len": [24, 48], "max_pos": [3, 5]},
    },
]
IND_KEYS = {"mode", "mom_len", "dc_len", "dc_exit"}


def summary(st, curve, t_from, t_to, btc):
    tr = st["trades"]
    wins = sum(x["pnl"] > 0 for x in tr)
    gp = sum(x["pnl"] for x in tr if x["pnl"] > 0)
    gl = -sum(x["pnl"] for x in tr if x["pnl"] <= 0)
    weeks = (t_to - t_from) / (7 * 24 * M.HOUR_MS)
    end = curve[-1] if curve else 100.0
    b = [c for c in btc if t_from <= c[0] < t_to]
    coins = {}
    for x in tr:
        coins[x["coin"]] = coins.get(x["coin"], 0) + x["pnl"]
    best = sorted(coins.items(), key=lambda kv: -kv[1])
    return {
        "son_bakiye": round(end, 2), "getiri_pct": round(end - 100, 2), "islem": len(tr),
        "haftalik_islem": round(len(tr) / weeks, 2) if weeks else 0,
        "basari_pct": round(wins / len(tr) * 100, 1) if tr else 0.0,
        "kar_faktoru": round(gp / gl, 2) if gl > 0 else None,
        "max_dusus_pct": round(max_dd(curve), 2),
        "al_tut_pct": round((b[-1][4] / b[0][1] - 1) * 100, 2) if b else 0,
        "en_cok_kazandiran": [(k, round(v, 2)) for k, v in best[:3]],
        "en_cok_kaybettiren": [(k, round(v, 2)) for k, v in best[-3:]],
    }


def weekly(ctx, p, t_from):
    week = 7 * 24 * M.HOUR_MS
    times = [t for t in ctx["times"] if t >= t_from]
    ends, ntr = [], []
    k = 0
    while k < len(times) and times[k] + week <= times[-1]:
        t0 = times[k]
        st, curve = M.simulate(ctx, dict(p, max_dd=0.10), t0, t0 + week)
        ends.append(curve[-1] if curve else 100.0)
        ntr.append(len(st["trades"]))
        k += 24
    return ends, ntr


def run(data, out_dir, log=print):
    universe = list(data)            # hacim sırasına göre
    btc = data["BTC"]
    times = sorted({c[0] for cs in data.values() for c in cs})
    split_t = times[int(len(times) * 0.7)]
    t0 = times[260]
    results = []
    for cand in MULTI_CANDIDATES:
        tic = time.time()
        base = dict(M.DEFAULT, **cand["params"])
        keys = list(cand["grid"])
        cache = {}
        best, best_sc, table = None, -math.inf, []
        any_best, any_sc = None, -math.inf
        for vals in itertools.product(*cand["grid"].values()):
            p = dict(base, **dict(zip(keys, vals)))
            ik = tuple(sorted((k, p[k]) for k in IND_KEYS))
            if ik not in cache:
                cache[ik] = M.prepare(data, p, universe)
            st, curve = M.simulate(cache[ik], p, t0, split_t)
            sm = summary(st, curve, t0, split_t, btc)
            sc = score(sm) if sm["haftalik_islem"] >= 1.0 else -math.inf
            table.append({**dict(zip(keys, vals)), "getiri_pct": sm["getiri_pct"],
                          "haftalik_islem": sm["haftalik_islem"], "max_dusus_pct": sm["max_dusus_pct"]})
            if sc > best_sc:
                best, best_sc = p, sc
            if score(sm) > any_sc:
                any_best, any_sc = p, score(sm)
        best = best or any_best
        ctx = cache[tuple(sorted((k, best[k]) for k in IND_KEYS))]
        st, curve = M.simulate(ctx, best, split_t, times[-1] + 1)
        oos = summary(st, curve, split_t, times[-1] + 1, btc)
        p2 = dict(best, fee=best["fee"] * 2, slip_tiers=[[a, b * 2] for a, b in best["slip_tiers"]])
        st2, curve2 = M.simulate(ctx, p2, split_t, times[-1] + 1)
        oos2 = summary(st2, curve2, split_t, times[-1] + 1, btc)
        ends, ntr = weekly(ctx, best, split_t)
        r = {
            "id": cand["id"], "baslik": cand["title"], "aciklama": cand["desc"], "zaman_dilimi": "1h",
            "secilen_ayar": {k: best[k] for k in keys}, "params": best,
            "sinav": oos, "sinav_2x_maliyet": oos2, "haftalik_100": dist(ends),
            "haftalik_islem_ortanca": statistics.median(ntr) if ntr else 0,
            "egitim_tablosu": table, "uygun": oos["haftalik_islem"] >= 1.5,
            "puan": round((score(oos) + score(oos2)) / 2, 3), "son_islemler": st["trades"][-15:],
            "evren": universe,
        }
        results.append(r)
        log(f"{cand['id']:<14} sınav {oos['getiri_pct']:+6.2f}%  düşüş {oos['max_dusus_pct']:5.2f}%  "
            f"haftada {oos['haftalik_islem']:5.2f} işlem  puan {r['puan']:+.3f}  ({time.time() - tic:.0f} sn)")
    ranked = sorted(results, key=lambda r: (r["uygun"], r["puan"]), reverse=True)
    meta = {"egitim": f"{fmt(t0)} → {fmt(split_t)}", "sinav": f"{fmt(split_t)} → {fmt(times[-1])}",
            "evren": universe}
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "coin_turnuva.json"), "w", encoding="utf-8") as f:
        json.dump({"meta": meta, "sonuclar": ranked}, f, ensure_ascii=False, indent=1)
    with open(os.path.join(out_dir, "COIN_TURNUVA.md"), "w", encoding="utf-8") as f:
        f.write(markdown(meta, ranked))
    return ranked


def markdown(meta, ranked):
    L = ["# 🪙 30 Coin Turnuvası", "",
         f"Coin listesi, testin başındaki (Kasım 2024) hacme göre seçildi (bugünün kazananlarını seçip "
         f"sonucu şişirmemek için): {', '.join(meta['evren'])}", "",
         f"Ayarlar **{meta['egitim']}** döneminde seçildi; sonuçlar botun **hiç görmediği** "
         f"**{meta['sinav']}** dönemine ait. Komisyon %0,1; kayma büyük coinlerde %0,05, orta %0,1, küçük %0,2.", "",
         "| # | Bot | 100$ → | 2× maliyetle | Haftada işlem | Başarı | En büyük düşüş | BTC al-tut | 1 haftada tipik | Puan |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for k, r in enumerate(ranked, 1):
        s, w = r["sinav"], r["haftalik_100"]
        L.append(f"| {k} | {r['baslik']}{'' if r['uygun'] else ' ⚠️az işlem'} | {s['son_bakiye']}$ | "
                 f"{r['sinav_2x_maliyet']['son_bakiye']}$ | {s['haftalik_islem']} | %{s['basari_pct']} | "
                 f"%{s['max_dusus_pct']} | %{s['al_tut_pct']} | {w.get('ortanca')}$ | {r['puan']} |")
    L += ["", "## Ayrıntı", ""]
    for r in ranked:
        s, w = r["sinav"], r["haftalik_100"]
        L.append(f"- **{r['baslik']}** — {r['aciklama']} Ayar: `{r['secilen_ayar']}`. "
                 f"1 hafta 100$: en kötü {w.get('en_kotu')}$, en iyi {w.get('en_iyi')}$, kazandıran hafta "
                 f"%{w.get('kazandiran_hafta_pct')}. En çok kazandıran: {s['en_cok_kazandiran']}; "
                 f"en çok kaybettiren: {s['en_cok_kaybettiren']}.")
    L += ["", "_Geçmiş sonuç geleceği garanti etmez. Sanal test; yatırım tavsiyesi değildir._", ""]
    return "\n".join(L)
