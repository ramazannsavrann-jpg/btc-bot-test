"""
Giriş noktası:  python -m bot.main

  1) Eski tek-bot dosyaları varsa results/temkinli/ klasörüne taşınır (test kaldığı yerden sürer).
  2) results/turnuva.json yoksa: tüm aday stratejiler 24 aylık gerçek veride yarışır (bir kere).
  3) Turnuvanın en iyi botları + temkinli bot, her biri ayrı sanal 100$ ile canlı kâğıt testte ilerler.
  4) results/RAPOR.md: tüm botların karşılaştırmalı Türkçe özeti.
"""
from __future__ import annotations

import os
import shutil
import sys
import time

from . import backtest, data, engines, external, multi_live, multi_tournament, paper, strategy as S, tournament

OUT = os.environ.get("BOT_OUT", "results")
TOP_N = 3
OLD_FILES = ["state.json", "equity_history.csv", "RAPOR.md", "backtest.json", "params.json", "GECMIS_TEST.md"]


def migrate():
    dst = os.path.join(OUT, "temkinli")
    if os.path.exists(os.path.join(OUT, "state.json")) and not os.path.exists(os.path.join(dst, "state.json")):
        os.makedirs(dst, exist_ok=True)
        for f in OLD_FILES:
            if os.path.exists(os.path.join(OUT, f)):
                shutil.move(os.path.join(OUT, f), os.path.join(dst, f))
        st = paper.load_json(os.path.join(dst, "state.json"))
        st["title"] = "Temkinli Trend (1s)"
        paper.save_json(os.path.join(dst, "state.json"), st)


def ensure_temkinli_backtest():
    d = os.path.join(OUT, "temkinli")
    if not os.path.exists(os.path.join(d, "backtest.json")):
        candles, src = data.history(24, "1h")
        backtest.run_backtest(candles, src, d)


def ensure_tournament():
    path = os.path.join(OUT, "turnuva.json")
    if os.path.exists(path):
        return paper.load_json(path)
    print("Turnuva başlıyor...")
    print("Korku & Açgözlülük geçmişi:", "tamam" if external.load_fear_greed(0) else "ALINAMADI")
    need = sorted({c["params"].get("interval", "1h") for c in tournament.CANDIDATES})
    data_by_iv = {}
    for iv in need:
        t = time.time()
        data_by_iv[iv] = data.history(24, iv)
        print(f"{iv}: {len(data_by_iv[iv][0])} mum ({data_by_iv[iv][1]}), {time.time() - t:.0f} sn")
    tournament.run(data_by_iv, OUT)
    return paper.load_json(path)


def ensure_coin_tournament():
    path = os.path.join(OUT, "coin_turnuva.json")
    if os.path.exists(path):
        return paper.load_json(path)
    print("30 coin turnuvası başlıyor...")
    if not external.FG:
        external.load_fear_greed(0)
    t = time.time()
    uni = data.history_universe(24, 30)
    print(f"Coin verisi hazır ({time.time() - t:.0f} sn)")
    multi_tournament.run(uni, OUT)
    return paper.load_json(path)


def coin_bots(ctour):
    """Akıllı Skor botu her zaman + turnuva birincisi (farklıysa). Seçim ilk seferde kilitlenir."""
    path = os.path.join(OUT, "secilen_coin_botlari.json")
    sel = paper.load_json(path)
    by_id = {r["id"]: r for r in ctour["sonuclar"]}
    if sel is None:
        ids = ["coin_skor"]
        top = ctour["sonuclar"][0]["id"]
        if top not in ids:
            ids.append(top)
        sel = [{"id": i, "title": by_id[i]["baslik"]} for i in ids if i in by_id]
        paper.save_json(path, sel)
    return [{"id": s["id"], "title": s["title"], "params": by_id[s["id"]]["params"], "bt": by_id[s["id"]]}
            for s in sel if s["id"] in by_id]


def bot_list(tour):
    """Temkinli + turnuvanın ilk TOP_N botu. Seçim ilk seferde kilitlenir (test boyunca değişmez)."""
    sel_path = os.path.join(OUT, "secilen_botlar.json")
    sel = paper.load_json(sel_path)
    if sel is None:
        ranked = tour["sonuclar"]
        ok = [r for r in ranked if r["uygun"]] or ranked
        sel = [{"id": r["id"], "title": f"{r['baslik']} ({r['zaman_dilimi']})"} for r in ok[:TOP_N]]
        paper.save_json(sel_path, sel)
    by_id = {r["id"]: r for r in tour["sonuclar"]}
    bots = [{"id": "temkinli", "title": "Temkinli Trend (1s)", "params": None, "bt": None,
             "interval": "1h"}]
    for s in sel:
        r = by_id[s["id"]]
        bots.append({"id": s["id"], "title": s["title"], "params": r["params"], "bt": r,
                     "interval": r["params"].get("interval", "1h")})
    return bots


def combined_report(rows, tour):
    now = max((st.get("last_run", 0) for _, st in rows), default=0)
    L = ["# 🤖 BTC Botları — Canlı Kâğıt Test", "",
         f"**Son güncelleme:** {paper.tr_time(now)} (İstanbul). Her bot ayrı **sanal 100$** ile, gerçek BTC fiyatıyla çalışır.", "",
         "| Bot | 100$ → | Getiri | Aynı sürede al-tut | Biten işlem | Başarı | Durum |",
         "|---|---|---|---|---|---|---|"]
    for b, st in rows:
        if st.get("multi"):
            s = multi_live.stats(st)
            bh = (st["last_price"] / st["start_price"] - 1) * 100
            el = (min(st["last_run"], st["test_end"]) - st["test_start"]) / S.HOUR_MS
            durum = "✅ bitti" if st["finished"] else "⛔ durdu" if st["halted"] else f"gün {min(7, int(el // 24) + 1)}/7"
            L.append(f"| [{b['title']}]({b['id']}/RAPOR.md) | **{s['equity']:.2f}$** | {s['return_pct']:+.2f}% | "
                     f"{bh:+.2f}% (BTC) | {s['trades']} | %{s['win_rate']:.0f} | {durum} |")
            continue
        px = st.get("last_price") or st["last_close"]
        s = S.stats(st, px)
        bh = (px / st["start_price"] - 1) * 100
        elapsed = (min(st.get("last_run", st["test_start"]), st["test_end"]) - st["test_start"]) / S.HOUR_MS
        if st["finished"]:
            durum = "✅ bitti"
        elif st["halted"]:
            durum = "⛔ durdu"
        else:
            durum = f"gün {min(7, int(elapsed // 24) + 1)}/7"
        L.append(f"| [{b['title']}]({b['id']}/RAPOR.md) | **{s['equity']:.2f}$** | {s['return_pct']:+.2f}% | "
                 f"{bh:+.2f}% | {s['trades']} | %{s['win_rate']:.0f} | {durum} |")
    L += [""]
    for b, st in rows:
        px = st.get("last_price") or st["last_close"]
        if st.get("multi"):
            from . import multi as MM
            desc = MM.describe_open(st)
        else:
            desc = engines.get(st["params"]).describe_open(st, px)
        L += [f"### {b['title']}", f"- Başlangıç: {paper.tr_time(st['test_start'])}, BTC {st['start_price']:,.0f}$",
              f"- Açık pozisyon: {desc or 'yok'}"]
        L += [f"- {x}" for x in list(reversed(st["log"]))[:6]]
        L.append("")
    if tour:
        L += ["## 🏆 Turnuvalar", "", "- BTC stratejileri (2 yıl): [TURNUVA.md](TURNUVA.md)",
              "- 30 coin botları (2 yıl): [COIN_TURNUVA.md](COIN_TURNUVA.md)", ""]
    L += ["_Bu SANAL paradır; gerçek emir verilmez. Sonuçlar yatırım tavsiyesi değildir._", ""]
    return "\n".join(L)


def main():
    os.makedirs(OUT, exist_ok=True)
    migrate()
    ensure_temkinli_backtest()
    tour = ensure_tournament()
    bots = bot_list(tour)

    if not external.FG:
        external.load_fear_greed(30)
    cache, rows = {}, []
    for b in bots:
        d = os.path.join(OUT, b["id"])
        st_old = paper.load_json(os.path.join(d, "state.json"))
        if st_old and st_old.get("finished"):
            rows.append((b, st_old))
            continue
        iv = b["interval"]
        if iv not in cache:
            cache[iv] = data.recent(1000, prefer=(st_old or {}).get("source"), interval=iv)
        candles, src = cache[iv]
        st = paper.run(candles, src, d, params=b["params"], title=b["title"], backtest=b["bt"])
        rows.append((b, st))
        print(f"{b['id']:<14} bakiye={S.equity(st, st['last_price']):.2f}$ işlem={len(st['trades'])}")

    try:
        ctour = ensure_coin_tournament()
        for b in coin_bots(ctour):
            try:
                st = multi_live.run(b["id"], b["params"], b["title"], b["bt"], OUT)
                rows.append((b, st))
                print(f"{b['id']:<14} bakiye={multi_live.stats(st)['equity']:.2f}$ işlem={len(st['trades'])}")
            except Exception as e:  # noqa: BLE001  (coin botu hata verse de BTC botları çalışmaya devam etsin)
                print(f"{b['id']} hata: {e}")
                old = paper.load_json(os.path.join(OUT, b["id"], "state.json"))
                if old and old.get("start_price"):
                    rows.append((b, old))
    except Exception as e:  # noqa: BLE001
        print("30 coin bölümü hata:", e)

    with open(os.path.join(OUT, "RAPOR.md"), "w", encoding="utf-8") as f:
        f.write(combined_report(rows, tour))
    if all(st.get("finished") for _, st in rows):
        print("Tüm testler bitti. İstersen Actions'tan iş akışını kapatabilirsin.")


if __name__ == "__main__":
    sys.exit(main())
