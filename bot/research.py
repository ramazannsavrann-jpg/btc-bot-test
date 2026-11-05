"""
ARAŞTIRMA TURNUVASI — ChatGPT denetimindeki önerilerle güçlendirilmiş test.

  * 48 ay BTC/USDT (2022 düşüşü, 2023–24 yükselişi, yatay dönemler dahil); 1s ve 4s mumlar.
  * Kayan walk-forward: 12 ay eğitim -> sonraki 3 ay sınav, 3 ay ileri kay (12 sınav penceresi).
    Her pencerede ayar SADECE önceki 12 ayda seçilir (günlük özsermaye Sharpe'ı ile).
    Bakiye pencereden pencereye taşınır; pencere sonunda açık pozisyon kapatılır (temkinli).
  * Her pencerenin piyasa rejimi (o tarihe kadar bilinen veriyle): yükseliş / düşüş / yatay, oynaklık.
  * Ölçümler: CAGR, Sharpe, Sortino, Calmar, en büyük düşüş, toparlanma, PF, beklenti, exposure...
  * Maliyet eğrisi: aynı kararlar 1×, 1,5×, 2×, 3× maliyetle.
  * Ezber riski: tüm aday×ayarların günlük getirileriyle PBO (CSCV) ve kazanan için Deflated Sharpe.
Sınav pencerelerinin hiçbiri ayar seçiminde kullanılmaz; ama bu dönemlerin bir kısmına önceki
turnuvalarda bakıldığı için "tamamen dokunulmamış" değildir (raporda belirtilir).
"""
from __future__ import annotations

import bisect
import itertools
import json
import math
import os
import statistics
import time
from datetime import datetime, timezone

from . import engines, metrics as MX, overfit, strategy as S
from .research_candidates import RESEARCH

HOUR_MS = S.HOUR_MS
DAY_MS = 24 * HOUR_MS


def ym_add(ts, months):
    d = datetime.fromtimestamp(ts / 1000, timezone.utc)
    m = d.month - 1 + months
    d2 = d.replace(year=d.year + m // 12, month=m % 12 + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
    return int(d2.timestamp() * 1000)


def fmt(ts):
    return datetime.fromtimestamp(ts / 1000, timezone.utc).strftime("%Y-%m-%d")


def windows(t0, t_end, train_m=12, test_m=3):
    out = []
    s = ym_add(t0, 1)  # ilk ayı ısınmaya bırak
    while True:
        tr_end = ym_add(s, train_m)
        te_end = ym_add(tr_end, test_m)
        if te_end > t_end:
            break
        out.append((s, tr_end, te_end))
        s = ym_add(s, test_m)
    return out


def base_params(cand):
    if cand["params"].get("engine") == "ensemble":
        return dict(cand["params"], fee=0.001, slip=0.0005)
    if cand["params"].get("engine") == "grid":
        from .grid import DEFAULT_PARAMS as G
        return dict(G, **cand["params"])
    return dict(S.DEFAULT_PARAMS, **cand["params"])


def exit_value(st, px):
    p = st["params"]
    return st["cash"] + st["qty"] * px * (1 - p["slip"]) * (1 - p["fee"])


def sim(E, candles, ts_list, ind, p, t_from, t_to, start_eq=100.0):
    i0 = bisect.bisect_left(ts_list, t_from)
    i1 = bisect.bisect_left(ts_list, t_to)
    st = E.new_state(start_eq, p)
    st["last_ts"] = candles[i0 - 1][0] if i0 > 0 else 0
    pts, expo = [], 0
    for i in range(i0, i1):
        E.process_bar(st, candles, ind, i)
        pts.append((candles[i][0], exit_value(st, candles[i][4])))
        expo += st["qty"] > 0
    if i1 > i0:
        E.close_all(st, candles[i1 - 1][0], candles[i1 - 1][4], "pencere sonu")
        if pts:
            pts[-1] = (pts[-1][0], st["cash"])
    return st, pts, expo, i1 - i0


def regime(btc1h, t):
    """t anına kadar bilinen veriyle: günlük EMA200'e göre yön + 30 günlük oynaklık seviyesi."""
    days = {}
    for c in btc1h:
        if c[0] >= t:
            break
        days[c[0] // DAY_MS] = c[4]
    cl = [days[k] for k in sorted(days)]
    if len(cl) < 220:
        return "veri az", "?"
    e200 = S.ema(cl, 200)
    e50 = S.ema(cl, 50)
    up = cl[-1] > e200[-1]
    slope = e50[-1] - e50[-11]
    yon = "Yükseliş" if up and slope > 0 else "Düşüş" if (not up and slope < 0) else "Yatay/kararsız"
    r = [cl[i] / cl[i - 1] - 1 for i in range(1, len(cl))]
    vol30 = statistics.pstdev(r[-30:])
    hist = [statistics.pstdev(r[i - 30:i]) for i in range(max(30, len(r) - 365), len(r), 5)]
    lvl = "yüksek oynaklık" if hist and vol30 > statistics.median(hist) * 1.25 else \
          "düşük oynaklık" if hist and vol30 < statistics.median(hist) * 0.8 else "normal oynaklık"
    return yon, lvl


def run_candidate(cand, data, wins, log):
    iv = cand["params"].get("interval", "1h")
    candles = data[iv]
    ts_list = [c[0] for c in candles]
    base = base_params(cand)
    keys = list(cand.get("grid", {}))
    combos = list(itertools.product(*cand["grid"].values())) if keys else [()]
    configs = []
    for vals in combos:
        p = dict(base, **dict(zip(keys, vals)))
        E = engines.get(p)
        configs.append((vals, p, E, E.indicators(candles, p)))

    eq = 100.0
    pts_all, trades_all, expo_all, bars_all, per = [], [], 0, 0, []
    chosen = []
    for (tr_s, tr_e, te_e) in wins:
        best, best_sc = None, -math.inf
        for vals, p, E, ind in configs:
            st, pts, _, _ = sim(E, candles, ts_list, ind, p, tr_s, tr_e)
            d = MX.daily(pts)
            sc = MX.sharpe(MX.returns(d)) if len(st["trades"]) >= 4 else -math.inf
            if sc > best_sc or best is None:
                best, best_sc = (vals, p, E, ind), sc
        vals, p, E, ind = best
        chosen.append((vals, p, E, ind))
        st, pts, expo, nb = sim(E, candles, ts_list, ind, p, tr_e, te_e, eq)
        eq_end = pts[-1][1] if pts else eq
        bh = MX.buy_hold(data["1h"], tr_e, te_e)
        yon, vol = regime(data["1h"], tr_e)
        per.append({"sinav": f"{fmt(tr_e)} → {fmt(te_e)}", "rejim": yon, "oynaklik": vol,
                    "ayar": dict(zip(keys, vals)), "getiri_pct": round((eq_end / eq - 1) * 100, 2),
                    "btc_al_tut_pct": bh.get("getiri_pct"), "islem": len(st["trades"]),
                    "piyasada_pct": round(expo / nb * 100, 1) if nb else 0})
        eq = eq_end
        pts_all += pts
        trades_all += st["trades"]
        expo_all += expo
        bars_all += nb

    m = MX.full(pts_all, trades_all, expo_all, bars_all)
    # maliyet eğrisi: aynı pencere kararları, artırılmış maliyet
    cost = {"1x": m["getiri_pct"]}
    for mult in (1.5, 2.0, 3.0):
        e2 = 100.0
        for (tr_s, tr_e, te_e), (vals, p, E, ind) in zip(wins, chosen):
            p2 = dict(p, fee=p["fee"] * mult, slip=p["slip"] * mult)
            _, pts, _, _ = sim(E, candles, ts_list, ind, p2, tr_e, te_e, e2)
            e2 = pts[-1][1] if pts else e2
        cost[f"{mult:g}x"] = round(e2 - 100, 2)
    # PBO/DSR için: her ayarın tüm sınav dönemindeki sabit-ayar günlük getirisi
    full_ret = {}
    t_a, t_b = wins[0][1], wins[-1][2]
    for vals, p, E, ind in configs:
        _, pts, _, _ = sim(E, candles, ts_list, ind, p, t_a, t_b)
        full_ret[f"{cand['id']}|{vals}"] = MX.returns(MX.daily(pts))
    ok_w = sum(1 for w in per if w["getiri_pct"] > 0)
    beat = sum(1 for w in per if w["btc_al_tut_pct"] is not None and w["getiri_pct"] > w["btc_al_tut_pct"])
    by_reg = {}
    for w in per:
        by_reg.setdefault(w["rejim"], []).append(w["getiri_pct"])
    return {
        "id": cand["id"], "baslik": cand["title"], "aciklama": cand["desc"], "zaman_dilimi": iv,
        "olcum": m, "maliyet_egrisi": cost, "pencereler": per,
        "pozitif_pencere": f"{ok_w}/{len(per)}", "al_tutu_gecen_pencere": f"{beat}/{len(per)}",
        "rejime_gore_ort_getiri": {k: round(statistics.mean(v), 2) for k, v in by_reg.items()},
        "son_ayar": dict(zip(keys, chosen[-1][0])) if chosen else {},
        "params_son": chosen[-1][1] if chosen else base,
    }, full_ret


def run(btc1h, out_dir, log=print):
    from .data import aggregate
    data = {"1h": btc1h, "4h": aggregate(btc1h, 4)}
    wins = windows(btc1h[0][0], btc1h[-1][0] + HOUR_MS)
    log(f"{len(wins)} sınav penceresi: {fmt(wins[0][1])} → {fmt(wins[-1][2])}")
    results, all_ret = [], {}
    for cand in RESEARCH:
        t = time.time()
        r, fr = run_candidate(cand, data, wins, log)
        results.append(r)
        all_ret.update(fr)
        m = r["olcum"]
        log(f"{cand['id']:<18} getiri {m['getiri_pct']:+7.2f}%  Sharpe {m['sharpe']:5.2f}  düşüş {m['max_dusus_pct']:5.2f}%  "
            f"haftada {m['haftalik_islem']:5.2f}  2x {r['maliyet_egrisi']['2x']:+7.2f}%  ({time.time() - t:.0f} sn)")
    bh = MX.buy_hold(btc1h, wins[0][1], wins[-1][2])
    # ezber riski
    T = min(len(v) for v in all_ret.values())
    series = {k: v[:T] for k, v in all_ret.items()}
    pb = overfit.pbo(series)
    daily_sh = {k: (statistics.mean(v) / statistics.pstdev(v) if statistics.pstdev(v) > 0 else 0.0)
                for k, v in series.items()}
    best_k = max(daily_sh, key=daily_sh.get)
    dsr = overfit.deflated_sharpe(series[best_k], list(daily_sh.values()))
    ranked = sorted(results, key=lambda r: r["olcum"]["sharpe"], reverse=True)
    meta = {"sinav": f"{fmt(wins[0][1])} → {fmt(wins[-1][2])}", "pencere": len(wins),
            "al_tut": bh, "pbo": pb, "dsr": dsr, "dsr_kazanan": best_k,
            "olusturma": datetime.now(timezone.utc).isoformat(timespec="minutes")}
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "arastirma.json"), "w", encoding="utf-8") as f:
        json.dump({"meta": meta, "sonuclar": ranked}, f, ensure_ascii=False, indent=1)
    with open(os.path.join(out_dir, "ARASTIRMA.md"), "w", encoding="utf-8") as f:
        f.write(markdown(meta, ranked))
    return meta, ranked


def markdown(meta, ranked):
    bh = meta["al_tut"]
    pb, dsr = meta["pbo"] or {}, meta["dsr"] or {}
    L = ["# 🔬 Araştırma Turnuvası (4 yıl, walk-forward)", "",
         f"Sınav dönemi **{meta['sinav']}** ({meta['pencere']} pencere × 3 ay). Her pencerede ayarlar sadece "
         "önceki 12 ayda seçildi. Komisyon %0,1 + kayma %0,05, kaldıraç yok, sadece alım yönü.", "",
         f"**BTC al-tut aynı dönemde:** getiri %{bh.get('getiri_pct')}, yıllık %{bh.get('cagr_pct')}, "
         f"Sharpe {bh.get('sharpe')}, en büyük düşüş %{bh.get('max_dusus_pct')}, Calmar {bh.get('calmar')}", "",
         "| # | Bot | Mum | Getiri | Yıllık | Sharpe | Sortino | Calmar | En büyük düşüş | Piyasada | Haftada işlem | PF | 2× maliyet | 3× maliyet | Pozitif pencere |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for k, r in enumerate(ranked, 1):
        m, c = r["olcum"], r["maliyet_egrisi"]
        L.append(f"| {k} | {r['baslik']} | {r['zaman_dilimi']} | %{m['getiri_pct']} | %{m['cagr_pct']} | {m['sharpe']} | "
                 f"{m['sortino']} | {m['calmar']} | %{m['max_dusus_pct']} | %{m['piyasada_kalma_pct']} | "
                 f"{m['haftalik_islem']} | {m['kar_faktoru']} | %{c['2x']} | %{c['3x']} | {r['pozitif_pencere']} |")
    L += ["", "## Ezber (overfitting) riski", "",
          f"- **PBO = %{round(pb.get('pbo', 0) * 100, 1) if pb else '-'}** ({pb.get('deneme')} aday×ayar). "
          "Eğitimde en iyi görünen ayarın sınavda ortancanın altında kalma olasılığı. %50 civarı = seçim yazı-turadan farksız.",
          f"- **Deflated Sharpe = %{round(dsr.get('dsr', 0) * 100, 1) if dsr else '-'}** (en iyi: `{meta['dsr_kazanan']}`, "
          f"yıllık Sharpe {dsr.get('sharpe_yillik')}, bu kadar denemede şansla beklenen en iyi Sharpe "
          f"{dsr.get('beklenen_en_iyi_sans_sharpe_yillik')}). %95 üstü güçlü kanıt sayılır.", "",
          "## Rejime göre ortalama 3 aylık getiri", "",
          "| Bot | " + " | ".join(["Yükseliş", "Yatay/kararsız", "Düşüş"]) + " |", "|---|---|---|---|"]
    for r in ranked:
        g = r["rejime_gore_ort_getiri"]
        L.append(f"| {r['baslik']} | " + " | ".join(f"%{g[k]}" if k in g else "-" for k in
                                                     ["Yükseliş", "Yatay/kararsız", "Düşüş"]) + " |")
    L += ["", "## Botlar", ""]
    for r in ranked:
        m = r["olcum"]
        L.append(f"- **{r['baslik']}** — {r['aciklama']} İşlem {m['islem']}, başarı %{m['basari_pct']}, "
                 f"işlem başı beklenti {m['beklenti_islem_basi']}$, ort. kazanç {m['ort_kazanc']}$ / ort. kayıp "
                 f"{m['ort_kayip']}$, en uzun kayıp serisi {m['en_uzun_kayip_serisi']}, ort. tutma {m['ort_tutma_saat']} saat. "
                 f"Al-tutu geçen pencere {r['al_tutu_gecen_pencere']}. Son ayar: `{r['son_ayar']}`.")
    L += ["", "_Not: Sınav pencerelerinin bir kısmına önceki turnuvalarda bakıldı; bu yüzden tamamen dokunulmamış "
          "değiller. Geçmiş sonuç geleceği garanti etmez. Yatırım tavsiyesi değildir._", ""]
    return "\n".join(L)
