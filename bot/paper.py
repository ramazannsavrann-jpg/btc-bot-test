"""
Canlı KÂĞIT test: gerçek BTC fiyatı, SANAL 100$. Gerçek emir yok, API anahtarı yok.

Her çalıştırmada (GitHub Actions, ~15 dakikada bir):
  * Son 1000 kapanmış 1 saatlik mumu çeker,
  * Daha önce işlenmemiş mumları strateji motorundan sırayla geçirir,
  * Durumu state.json'a, bakiye geçmişini equity_history.csv'ye yazar,
  * RAPOR.md'yi (Türkçe) yeniden üretir.
Test başladıktan 7 gün sonra açık pozisyon kapatılır ve test biter.
"""
from __future__ import annotations

import csv
import json
import os
import time
from datetime import datetime, timedelta, timezone

from . import engines, strategy as S

HOUR_MS = S.HOUR_MS
TEST_DAYS = 7
SNAPSHOT_HOURS = 6
TR = timezone(timedelta(hours=3))  # İstanbul (yaz saati yok)


def tr_time(ms):
    return datetime.fromtimestamp(ms / 1000, TR).strftime("%d.%m %H:%M")


def load_json(path, default=None):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return default


def save_json(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def open_entries(state):
    if state.get("lots"):
        return state["lots"]
    return [state["position"]] if state.get("position") else []


def start_test(candles, params, now_ms, title=""):
    p = dict(params)
    p["max_dd"] = 0.10  # canlı testte %10 düşüş freni açık
    st = engines.get(p).new_state(100.0, p)
    st["title"] = title
    st["test_start"] = now_ms
    st["test_end"] = now_ms + TEST_DAYS * 24 * HOUR_MS
    st["start_price"] = candles[-1][4]
    st["last_ts"] = candles[-1][0]  # geçmişte işlem yapma; sadece bundan sonrası
    st["last_close"] = candles[-1][4]
    st["finished"] = False
    st["snapshots"] = [{"ts": now_ms, "equity": 100.0, "price": candles[-1][4], "trades": 0}]
    st["log"] = [f"{tr_time(now_ms)} Test başladı. BTC {candles[-1][4]:,.0f}$, sanal bakiye 100$."]
    return st


def step(state, candles, now_ms, source):
    E = engines.get(state["params"])
    bar_ms = S.BAR_MS.get(state["params"].get("interval", "1h"), HOUR_MS)
    ind = E.indicators(candles, state["params"])
    logged = set(state.setdefault("logged_entries", []))
    n_trades = len(state["trades"])
    last_bar = None  # test_end'den önce işlenen son mum

    def log_buy(ts, px, extra=""):
        if ts not in logged:
            logged.add(ts)
            state["log"].append(f"{tr_time(ts)} ALIM {px:,.0f}${extra}")

    for i, c in enumerate(candles):
        if c[0] >= state["test_end"]:
            break
        E.process_bar(state, candles, ind, i)
        if c[0] == state["last_ts"]:
            last_bar = c
        # aynı saatte açılıp kapanan işlemler dahil, tüm alım/satımları günlüğe yaz
        for t in state["trades"][n_trades:]:
            log_buy(t["entry_ts"], t["entry_px"])
            state["log"].append(
                f"{tr_time(t['exit_ts'])} SATIŞ {t['exit_px']:,.0f}$ ({t['reason']}) "
                f"→ {'+' if t['pnl'] >= 0 else ''}{t['pnl']:.2f}$")
        n_trades = len(state["trades"])
        for pos in open_entries(state):
            extra = (f" (stop {pos['stop']:,.0f}$, hedef {pos['tp']:,.0f}$, {pos['cost']:.2f}$ kullanıldı)"
                     if "stop" in pos else f" ({pos['cost']:.2f}$ kullanıldı)")
            log_buy(pos["entry_ts"], pos["entry_px"], extra)
    state["logged_entries"] = sorted(logged)[-80:]

    price = candles[-1][4]
    state["last_price"] = price
    state["source"] = source
    state["last_run"] = now_ms

    if not state["finished"] and now_ms >= state["test_end"]:
        # bitiş anına en yakın kapanmış mumun fiyatından kapat
        end_px = last_bar[4] if last_bar else state["last_close"]
        end_ts = (last_bar[0] + bar_ms) if last_bar else state["test_end"]
        k = len(state["trades"])
        E.close_all(state, end_ts, end_px, "test bitti")
        for t in state["trades"][k:]:
            state["log"].append(f"{tr_time(end_ts)} SATIŞ {t['exit_px']:,.0f}$ (test bitti) → {t['pnl']:+.2f}$")
        state["last_price"] = end_px
        price = end_px
        state["finished"] = True
        state["log"].append(f"{tr_time(end_ts)} 7 günlük test bitti.")

    snaps = state["snapshots"]
    if now_ms - snaps[-1]["ts"] >= SNAPSHOT_HOURS * HOUR_MS or state["finished"] and snaps[-1].get("final") is None:
        snaps.append({"ts": now_ms, "equity": round(S.equity(state, price), 2), "price": price,
                      "trades": len(state["trades"]), **({"final": True} if state["finished"] else {})})
    state["log"] = state["log"][-60:]
    return state


def report(state, backtest):
    E = engines.get(state["params"])
    price = state.get("last_price") or state["last_close"]
    s = S.stats(state, price)
    eq = s["equity"]
    bh = (price / state["start_price"] - 1) * 100
    now = state.get("last_run", state["test_start"])
    elapsed_h = (min(now, state["test_end"]) - state["test_start"]) / HOUR_MS
    day = min(TEST_DAYS, int(elapsed_h // 24) + 1)
    if state["finished"]:
        durum = "✅ TEST BİTTİ (7 gün tamamlandı)"
    elif state["halted"]:
        durum = f"⛔ DURDU: {state['halt_reason']}"
    else:
        durum = f"🟢 Test sürüyor — gün {day}/{TEST_DAYS} ({elapsed_h:.0f} saat geçti)"

    L = [
        f"# {state.get('title') or 'BTC Bot'} — Canlı Kâğıt Test Raporu",
        "",
        f"**Son güncelleme:** {tr_time(now)} (İstanbul) · Fiyat kaynağı: {state.get('source', '-')}",
        "",
        f"**Durum:** {durum}",
        "",
        f"## 💰 100$ → **{eq:.2f}$** ({s['return_pct']:+.2f}%)",
        "",
        f"- Aynı sürede sadece BTC alıp tutsaydın: **{100 * (1 + bh / 100):.2f}$** ({bh:+.2f}%)",
        f"- BTC fiyatı: {state['start_price']:,.0f}$ → {price:,.0f}$",
        f"- Biten işlem: **{s['trades']}** · Kazanan: {s['wins']} · Başarı oranı: **%{s['win_rate']:.0f}**",
    ]
    desc = E.describe_open(state, price)
    if desc:
        L.append(f"- Açık pozisyon: {desc}")
    elif state.get("pending_entry"):
        L.append("- Alım sinyali geldi, bir sonraki mumda alınacak.")
    else:
        L.append("- Açık pozisyon yok (bot uygun fırsat bekliyor; nakitte durmak da bir karardır).")

    L += ["", "## 🕕 6 saatlik özet", "", "| Zaman | Bakiye | Değişim | BTC | Toplam işlem |", "|---|---|---|---|---|"]
    prev = 100.0
    for sn in state["snapshots"]:
        L.append(f"| {tr_time(sn['ts'])} | {sn['equity']:.2f}$ | {sn['equity'] - prev:+.2f}$ | "
                 f"{sn['price']:,.0f}$ | {sn['trades']} |")
        prev = sn["equity"]

    L += ["", "## 📜 Ne oldu? (son olaylar)", ""]
    L += [f"- {x}" for x in reversed(state["log"][-20:])]

    if backtest and "gorulmemis_donem" in backtest:
        o, w = backtest["gorulmemis_donem"], backtest["haftalik_100_dolar_bot"]
        L += [
            "", "## 📊 Geçmiş test özeti (karşılaştırma için)", "",
            f"- Botun görmediği {backtest['test_donemi']['baslangic']} → {backtest['test_donemi']['bitis']} döneminde: "
            f"100$ → {o['son_bakiye']}$ (al-tut %{o['al_tut_pct']}), başarı %{o['basari_pct']}, en büyük düşüş %{o['max_dusus_pct']}",
            f"- 100$ ile 1 hafta, {w.get('pencere')} deneme: tipik {w.get('ortanca')}$, "
            f"en kötü {w.get('en_kotu')}$, en iyi {w.get('en_iyi')}$, kazandıran hafta %{w.get('kazandiran_hafta_pct')}",
            "- Ayrıntı: [GECMIS_TEST.md](GECMIS_TEST.md)",
        ]
    elif backtest and "sinav" in backtest:
        o, w = backtest["sinav"], backtest["haftalik_100"]
        L += [
            "", "## 📊 Turnuvadaki geçmiş test (karşılaştırma için)", "",
            f"- Görülmemiş dönemde: 100$ → {o['son_bakiye']}$ (al-tut %{o['al_tut_pct']}), "
            f"haftada {o['haftalik_islem']} işlem, başarı %{o['basari_pct']}, en büyük düşüş %{o['max_dusus_pct']}",
            f"- 100$ ile 1 hafta, {w.get('pencere')} deneme: tipik {w.get('ortanca')}$, "
            f"en kötü {w.get('en_kotu')}$, en iyi {w.get('en_iyi')}$, kazandıran hafta %{w.get('kazandiran_hafta_pct')}",
            "- Ayrıntı: [../TURNUVA.md](../TURNUVA.md)",
        ]
    L += ["", "_Bu SANAL paradır; gerçek emir verilmez. Sonuçlar yatırım tavsiyesi değildir._", ""]
    return "\n".join(L)


def append_equity(path, state):
    new = not os.path.exists(path)
    price = state.get("last_price") or state["last_close"]
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["zaman_istanbul", "btc_fiyat", "bakiye", "islem_sayisi"])
        w.writerow([tr_time(state["last_run"]), round(price, 2),
                    round(S.equity(state, price), 4), len(state["trades"])])


def run(candles, source, out_dir, now_ms=None, params=None, title="", backtest=None):
    now_ms = now_ms or int(time.time() * 1000)
    os.makedirs(out_dir, exist_ok=True)
    state_path = os.path.join(out_dir, "state.json")
    state = load_json(state_path)
    backtest = backtest or load_json(os.path.join(out_dir, "backtest.json"))
    if state is None:
        params = params or load_json(os.path.join(out_dir, "params.json"), S.DEFAULT_PARAMS)
        state = start_test(candles, params, now_ms, title)
    if not state["finished"]:
        step(state, candles, now_ms, source)
        append_equity(os.path.join(out_dir, "equity_history.csv"), state)
    save_json(state_path, state)
    with open(os.path.join(out_dir, "RAPOR.md"), "w", encoding="utf-8") as f:
        f.write(report(state, backtest))
    return state
