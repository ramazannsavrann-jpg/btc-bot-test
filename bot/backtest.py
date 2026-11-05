"""
Geçmiş testi (backtest) — son 24 ayın BTC/USDT 1 saatlik verisi.

Ezber (overfitting) yapmamak için "ileri yürüyen" test:
  * Verinin ilk %70'inde 27 ayar kombinasyonu denenir, en iyisi seçilir.
  * Seçilen ayar, hiç görmediği son %30'luk dönemde test edilir. Gerçekçi sonuç budur.
  * Görülmemiş dönemde her gün yeni 100$ ile başlayan 7 günlük pencereler
    simüle edilir -> "100$ bir haftada ne olur?" sorusunun dağılımı.
"""
from __future__ import annotations

import itertools
import json
import math
import os
import statistics
from datetime import datetime, timezone

from . import strategy as S

HOUR_MS = S.HOUR_MS
WARMUP = 260  # EMA200 ısınması


def simulate(candles, params, trade_from_ts, start_equity=100.0, ind=None):
    """trade_from_ts'den önce işlem açmaz (göstergeler ısınsın)."""
    st = S.new_state(start_equity, params)
    st["pause_until"] = trade_from_ts
    ind = ind or S.indicators(candles, params)
    curve = []
    for i in range(len(candles)):
        S.process_bar(st, candles, ind, i)
        if candles[i][0] >= trade_from_ts:
            curve.append(S.equity(st, candles[i][4]))
    # dönem sonunda açık pozisyonu kapat
    if st["position"]:
        S._close_position(st, candles[-1][0], candles[-1][4], "dönem sonu")
    return st, curve


def max_drawdown(curve):
    peak, mdd = -math.inf, 0.0
    for e in curve:
        peak = max(peak, e)
        if peak > 0:
            mdd = max(mdd, (peak - e) / peak)
    return mdd * 100


def summarize(st, curve, candles_seg):
    s = S.stats(st)
    bh = (candles_seg[-1][4] / candles_seg[0][1] - 1) * 100
    return {
        "son_bakiye": round(s["equity"], 2),
        "getiri_pct": round(s["return_pct"], 2),
        "islem": s["trades"],
        "kazanan": s["wins"],
        "basari_pct": round(s["win_rate"], 1),
        "kar_faktoru": round(s["profit_factor"], 2) if math.isfinite(s["profit_factor"]) else None,
        "max_dusus_pct": round(max_drawdown(curve), 2),
        "al_tut_pct": round(bh, 2),
    }


GRID = {
    "rsi_entry": [30.0, 35.0, 40.0],
    "stop_atr": [1.5, 2.0, 2.5],
    "tp_atr": [2.0, 3.0, 4.0],
    "breakout_len": [0, 24],
}


def choose_params(candles, split_i):
    train = candles[:split_i]
    trade_from = train[min(WARMUP, len(train) - 1)][0]
    best, best_score, rows = None, -math.inf, []
    for vals in itertools.product(*GRID.values()):
        p = dict(S.DEFAULT_PARAMS, **dict(zip(GRID.keys(), vals)))
        st, curve = simulate(train, p, trade_from)
        s = S.stats(st)
        mdd = max_drawdown(curve)
        # getiri / düşüş oranı; en az 15 işlem şartı
        score = s["return_pct"] / max(mdd, 1.0) if s["trades"] >= 15 else -math.inf
        rows.append({**dict(zip(GRID.keys(), vals)), "getiri_pct": round(s["return_pct"], 2),
                     "islem": s["trades"], "max_dusus_pct": round(mdd, 2)})
        if score > best_score:
            best, best_score = p, score
    return best or dict(S.DEFAULT_PARAMS), rows


def weekly_windows(candles, params, from_i):
    """Görülmemiş dönemde her gün başlayan 7 günlük pencereler."""
    week = 24 * 7
    ind = S.indicators(candles, params)
    bot, hold = [], []
    i = max(from_i, WARMUP)
    while i + week <= len(candles):
        st = S.new_state(100.0, dict(params, max_dd=0.10))  # canlı testteki gibi %10 fren
        st["pause_until"] = candles[i][0]
        # göstergeler tüm veriden; durum sadece pencerede işleniyor
        st["last_ts"] = candles[i - 1][0]
        for j in range(i, i + week):
            S.process_bar(st, candles, ind, j)
        px = candles[i + week - 1][4]
        p = st["params"]
        # açık pozisyon satış masrafıyla değerlenir
        bot.append(st["cash"] + st["qty"] * px * (1 - p["slip"]) * (1 - p["fee"]))
        hold.append(100.0 * candles[i + week - 1][4] / candles[i][1])
        i += 24
    return bot, hold


def dist(values):
    if not values:
        return {}
    s = sorted(values)
    q = lambda f: s[min(len(s) - 1, int(f * (len(s) - 1) + 0.5))]  # noqa: E731
    return {
        "pencere": len(s),
        "ortanca": round(statistics.median(s), 2),
        "ortalama": round(statistics.mean(s), 2),
        "en_kotu": round(s[0], 2),
        "en_iyi": round(s[-1], 2),
        "kotu_yuzde10": round(q(0.10), 2),
        "iyi_yuzde10": round(q(0.90), 2),
        "kazandiran_hafta_pct": round(sum(v > 100 for v in s) / len(s) * 100, 1),
    }


def run_backtest(candles, source, out_dir):
    split_i = int(len(candles) * 0.7)
    params, grid_rows = choose_params(candles, split_i)

    trade_from = candles[split_i][0]
    oos_seg = candles[split_i:]
    st, curve = simulate(candles, params, trade_from)
    oos = summarize(st, curve, oos_seg)

    st_d, curve_d = simulate(candles, S.DEFAULT_PARAMS, trade_from)
    oos_default = summarize(st_d, curve_d, oos_seg)

    bot_w, hold_w = weekly_windows(candles, params, split_i)

    fmt = lambda ts: datetime.fromtimestamp(ts / 1000, timezone.utc).strftime("%Y-%m-%d")  # noqa: E731
    result = {
        "kaynak": source,
        "veri": {"baslangic": fmt(candles[0][0]), "bitis": fmt(candles[-1][0]), "mum": len(candles)},
        "egitim_donemi": {"baslangic": fmt(candles[0][0]), "bitis": fmt(candles[split_i - 1][0])},
        "test_donemi": {"baslangic": fmt(candles[split_i][0]), "bitis": fmt(candles[-1][0])},
        "secilen_ayar": {k: params[k] for k in GRID},
        "gorulmemis_donem": oos,
        "gorulmemis_donem_varsayilan_ayar": oos_default,
        "haftalik_100_dolar_bot": dist(bot_w),
        "haftalik_100_dolar_al_tut": dist(hold_w),
        "son_islemler": st["trades"][-15:],
        "ayar_tablosu": grid_rows,
    }
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "backtest.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    with open(os.path.join(out_dir, "params.json"), "w", encoding="utf-8") as f:
        json.dump(params, f, indent=1)
    with open(os.path.join(out_dir, "GECMIS_TEST.md"), "w", encoding="utf-8") as f:
        f.write(markdown(result))
    return result, params


def markdown(r):
    o, w, h = r["gorulmemis_donem"], r["haftalik_100_dolar_bot"], r["haftalik_100_dolar_al_tut"]
    d = r["gorulmemis_donem_varsayilan_ayar"]
    lines = [
        "# Geçmiş Test (Backtest) Sonucu",
        "",
        f"Veri: {r['kaynak']}, {r['veri']['baslangic']} → {r['veri']['bitis']} ({r['veri']['mum']} saatlik mum)",
        "",
        f"Ayarlar {r['egitim_donemi']['baslangic']} → {r['egitim_donemi']['bitis']} arasında seçildi, "
        f"sonra botun **hiç görmediği** {r['test_donemi']['baslangic']} → {r['test_donemi']['bitis']} döneminde denendi.",
        "",
        f"Seçilen ayar: RSI giriş {r['secilen_ayar']['rsi_entry']}, stop {r['secilen_ayar']['stop_atr']}×ATR, "
        f"hedef {r['secilen_ayar']['tp_atr']}×ATR, zirve kırılımı "
        f"{'açık (' + str(r['secilen_ayar']['breakout_len']) + ' saat)' if r['secilen_ayar']['breakout_len'] else 'kapalı'}",
        "",
        "## Görülmemiş dönemde 100$",
        "",
        "| | Bot (seçilen ayar) | Bot (varsayılan ayar) |",
        "|---|---|---|",
        f"| Son bakiye | {o['son_bakiye']}$ | {d['son_bakiye']}$ |",
        f"| Getiri | %{o['getiri_pct']} | %{d['getiri_pct']} |",
        f"| İşlem sayısı | {o['islem']} | {d['islem']} |",
        f"| Başarı oranı | %{o['basari_pct']} | %{d['basari_pct']} |",
        f"| En büyük düşüş | %{o['max_dusus_pct']} | %{d['max_dusus_pct']} |",
        f"| Aynı dönem BTC al-tut | %{o['al_tut_pct']} | %{d['al_tut_pct']} |",
        "",
        "## 100$ bir haftada ne olur? (görülmemiş dönem, her gün başlayan 7 günlük denemeler)",
        "",
        "| | Bot | Sadece BTC alıp tutmak |",
        "|---|---|---|",
        f"| Deneme sayısı | {w.get('pencere')} | {h.get('pencere')} |",
        f"| Tipik sonuç (ortanca) | {w.get('ortanca')}$ | {h.get('ortanca')}$ |",
        f"| En kötü hafta | {w.get('en_kotu')}$ | {h.get('en_kotu')}$ |",
        f"| En iyi hafta | {w.get('en_iyi')}$ | {h.get('en_iyi')}$ |",
        f"| Kötü %10'luk dilim | {w.get('kotu_yuzde10')}$ | {h.get('kotu_yuzde10')}$ |",
        f"| İyi %10'luk dilim | {w.get('iyi_yuzde10')}$ | {h.get('iyi_yuzde10')}$ |",
        f"| Kazandıran hafta oranı | %{w.get('kazandiran_hafta_pct')} | %{h.get('kazandiran_hafta_pct')} |",
        "",
        "_Komisyon (%0,1) ve kayma (%0,05) dahildir. Geçmiş sonuç geleceği garanti etmez._",
        "",
    ]
    return "\n".join(lines)
