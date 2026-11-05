"""
30 coin botunun CANLI kâğıt testi (sanal 100$, gerçek fiyatlar, gerçek emir yok).
Coin listesi test başında Binance'teki 24 saatlik hacme göre seçilir ve test boyunca sabit kalır.
"""
from __future__ import annotations

import os
import time

from . import data, multi as M, paper

TEST_DAYS = paper.TEST_DAYS
HOUR_MS = M.HOUR_MS


def fetch(universe, interval="1h"):
    out, bad = {}, []
    for s in universe:
        try:
            c = data.recent_symbol(s, 1000, interval)
            if len(c) >= 260:
                out[s] = c
        except Exception as e:  # noqa: BLE001
            bad.append(f"{s}: {e}")
    if "BTC" not in out:
        raise RuntimeError("BTC verisi alınamadı: " + " | ".join(bad[:3]))
    return out, bad


def start(params, title, now_ms):
    uni = data.top_symbols(30)
    if "BTC" not in uni:
        uni = ["BTC"] + uni[:29]
    p = dict(params)
    p["max_dd"] = 0.10
    st = M.new_state(100.0, p, uni)
    st.update({"title": title, "test_start": now_ms, "test_end": now_ms + TEST_DAYS * 24 * HOUR_MS,
               "finished": False, "log": [], "logged": []})
    return st


def step(st, now_ms):
    p = st["params"]
    dset, bad = fetch(st["universe"], p.get("interval", "1h"))
    ctx = M.prepare(dset, p, st["universe"])
    if not st.get("start_price"):
        st["start_price"] = dset["BTC"][-1][4]
        st["last_ts"] = ctx["times"][-1]           # geçmişte işlem yapma
        for s, c in dset.items():
            st["last_close"][s] = c[-1][4]
        st["snapshots"] = [{"ts": now_ms, "equity": 100.0, "price": st["start_price"], "trades": 0}]
        st["log"].append(f"{paper.tr_time(now_ms)} Test başladı. Takip edilen {len(dset)} coin: "
                         + ", ".join(st["universe"]))
    n_tr = len(st["trades"])
    for t in ctx["times"]:
        if t >= st["test_end"]:
            break
        before = set(st["pos"])
        M.process_time(st, ctx, t)
        for s in set(st["pos"]) - before:
            ps = st["pos"][s]
            st["log"].append(f"{paper.tr_time(ps['entry_ts'])} ALIM {s} {ps['entry_px']:.6g}$ "
                             f"({ps['cost']:.2f}$; {ps['why']})")
        for x in st["trades"][n_tr:]:
            st["log"].append(f"{paper.tr_time(x['exit_ts'])} SATIŞ {x['coin']} {x['exit_px']:.6g}$ "
                             f"({x['reason']}) → {x['pnl']:+.2f}$")
        n_tr = len(st["trades"])
    st["last_price"] = dset["BTC"][-1][4]
    st["last_run"] = now_ms
    st["source"] = "Binance"
    if bad:
        st["log"].append(f"{paper.tr_time(now_ms)} Veri alınamayan coin: {', '.join(b.split(':')[0] for b in bad)}")
    if not st["finished"] and now_ms >= st["test_end"]:
        k = len(st["trades"])
        M.close_all(st, st["test_end"], reason="test bitti")
        for x in st["trades"][k:]:
            st["log"].append(f"{paper.tr_time(st['test_end'])} SATIŞ {x['coin']} (test bitti) → {x['pnl']:+.2f}$")
        st["finished"] = True
        st["log"].append(f"{paper.tr_time(now_ms)} 7 günlük test bitti.")
    snaps = st["snapshots"]
    if now_ms - snaps[-1]["ts"] >= 6 * HOUR_MS or (st["finished"] and not snaps[-1].get("final")):
        snaps.append({"ts": now_ms, "equity": round(M.equity(st), 2), "price": st["last_price"],
                      "trades": len(st["trades"]), **({"final": True} if st["finished"] else {})})
    st["log"] = st["log"][-80:]


def stats(st):
    tr = st["trades"]
    wins = sum(x["pnl"] > 0 for x in tr)
    eq = M.equity(st)
    return {"equity": eq, "return_pct": eq - 100, "trades": len(tr), "wins": wins,
            "win_rate": wins / len(tr) * 100 if tr else 0.0}


def report(st, bt):
    s = stats(st)
    bh = (st["last_price"] / st["start_price"] - 1) * 100
    el = (min(st["last_run"], st["test_end"]) - st["test_start"]) / HOUR_MS
    durum = ("✅ TEST BİTTİ" if st["finished"] else f"⛔ DURDU: {st['halt_reason']}" if st["halted"]
             else f"🟢 Test sürüyor — gün {min(7, int(el // 24) + 1)}/7")
    L = [f"# {st['title']} — Canlı Kâğıt Test", "",
         f"**Son güncelleme:** {paper.tr_time(st['last_run'])} (İstanbul) · **Durum:** {durum}", "",
         f"## 💰 100$ → **{s['equity']:.2f}$** ({s['return_pct']:+.2f}%)", "",
         f"- Aynı sürede BTC al-tut: {bh:+.2f}%",
         f"- Biten işlem: **{s['trades']}** · Kazanan: {s['wins']} · Başarı: **%{s['win_rate']:.0f}**",
         f"- Açık pozisyonlar: {M.describe_open(st) or 'yok'}",
         f"- Takip edilen coinler: {', '.join(st['universe'])}", "",
         "## 🕕 6 saatlik özet", "", "| Zaman | Bakiye | Değişim | Toplam işlem |", "|---|---|---|---|"]
    prev = 100.0
    for sn in st["snapshots"]:
        L.append(f"| {paper.tr_time(sn['ts'])} | {sn['equity']:.2f}$ | {sn['equity'] - prev:+.2f}$ | {sn['trades']} |")
        prev = sn["equity"]
    L += ["", "## 📜 Ne oldu?", ""] + [f"- {x}" for x in reversed(st["log"][-25:])]
    if bt:
        o, w = bt["sinav"], bt["haftalik_100"]
        L += ["", "## 📊 Geçmiş test (30 coin turnuvası)", "",
              f"- Görülmemiş dönemde 100$ → {o['son_bakiye']}$ (BTC al-tut %{o['al_tut_pct']}), haftada "
              f"{o['haftalik_islem']} işlem, başarı %{o['basari_pct']}, en büyük düşüş %{o['max_dusus_pct']}",
              f"- 1 hafta 100$: tipik {w.get('ortanca')}$, en kötü {w.get('en_kotu')}$, en iyi {w.get('en_iyi')}$",
              "- Ayrıntı: [../COIN_TURNUVA.md](../COIN_TURNUVA.md)"]
    L += ["", "_Bu SANAL paradır; gerçek emir verilmez. Yatırım tavsiyesi değildir._", ""]
    return "\n".join(L)


def run(bot_id, params, title, bt, out_root, now_ms=None):
    now_ms = now_ms or int(time.time() * 1000)
    d = os.path.join(out_root, bot_id)
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, "state.json")
    st = paper.load_json(path) or start(params, title, now_ms)
    if not st["finished"]:
        step(st, now_ms)
    paper.save_json(path, st)
    with open(os.path.join(d, "RAPOR.md"), "w", encoding="utf-8") as f:
        f.write(report(st, bt))
    return st
