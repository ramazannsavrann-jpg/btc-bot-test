"""
VM-A canlı KÂĞIT botu: bağımsız sanal 100$, gerçek BTC fiyatı. Gerçek emir yok, API anahtarı yok, gerçek para yok.

Kurallar ön kayıt v2 §2 / v2.1 §3'teki VM-A ile aynıdır:
  * σ = son 540 adet 4s mumun basit getirilerinin standart sapması (bölen n) × √2190  (ENS ile aynı tahminci)
  * Her UTC gününün son 4s kapanışında hedef ağırlık w* = min(0,99 ; 0,40 / σ)
  * |w* − gerçek ağırlık| > 0,05 ise işlem bir sonraki 4s mumun açılışında
  * Komisyon %0,10, kayma %0,05; kaldıraç yok; nakit getirisi %0; düşüş freni yok (v2.1)
Dolum fiyatı, mevcut canlı botlarla aynı gerçekçi dolum yöntemiyle (bot/live_fill.py) 1 dakikalık mumdan alınır.
Sinyal zamanı, karar anı, kayıt anı ve mum fiyatı ile 1 dk referans fiyatı arasındaki fark ayrı ayrı kaydedilir.

Mevcut 11 bottan bağımsızdır: ayrı klasör (results/vm_kagit/), ayrı iş akışı (.github/workflows/vm_kagit.yml).
Mevcut botların dosyaları yalnızca karşılaştırma için OKUNUR, değiştirilmez. Bitiş tarihi yoktur.
"""
from __future__ import annotations

import csv
import json
import math
import os
import time
from datetime import datetime, timezone

from . import data as D, live_fill, paper, signals, strategy as S

OUT = os.path.join(os.environ.get("BOT_OUT", "results"), "vm_kagit")
ENS_DIR = os.path.join(os.environ.get("BOT_OUT", "results"), "kirilim_ansambl")
H = S.HOUR_MS
DAY = 24 * H
BAR4 = 4 * H
FEE, SLIP = 0.001, 0.0005
VOL_TARGET, MAX_W, BAND, WIN = 0.40, 0.99, 0.05, 540
PREFER = "Binance (data-api.binance.vision)"


def value(st, px):
    return st["cash"] + st["qty"] * px * (1 - SLIP) * (1 - FEE)


def mark_w(st, px):
    m = st["cash"] + st["qty"] * px
    return st["qty"] * px / m if m > 0 else 0.0


def new_state(candles, now_ms, src):
    c = candles[-1]
    return {"title": "VM-A: Oynaklık Hedefli BTC (%40, 4s)", "cash": 100.0, "qty": 0.0, "pending": None,
            "last_ts": c[0], "last_close": c[4], "start_price": c[4], "test_start": now_ms, "source": src,
            "trades": [], "dolumlar": [], "kararlar": [],
            "log": [f"{paper.tr_time(now_ms)} Test başladı. BTC {c[4]:,.0f}$, sanal bakiye 100$. Geçmişte işlem yapılmaz."]}


def fill(st, hook, ts, o):
    """Bekleyen hedefe göre işlem; formüller motorla (strategy._open/_close_position) aynı."""
    p = st["pending"]
    st["pending"] = None
    tgt = p["hedef"]
    mark = st["cash"] + st["qty"] * o
    delta = tgt * mark - st["qty"] * o
    if abs(delta) < 1e-9:
        return
    ref = hook("vm_al" if delta > 0 else "vm_sat", ts, o, st) if hook else o
    if delta > 0:
        spend = min(delta, st["cash"])
        if spend <= 0:
            return
        n = spend / (1 + FEE)
        px = ref * (1 + SLIP)
        q = n / px
        st["qty"] += q
        st["cash"] -= n + n * FEE
        if -1e-9 < st["cash"] < 0:
            st["cash"] = 0.0
        side, fee = "ALIM", n * FEE
    else:
        q = min(-delta / ref, st["qty"])
        px = ref * (1 - SLIP)
        gross = q * px
        fee = gross * FEE
        st["cash"] += gross - fee
        st["qty"] -= q
        side = "SATIŞ"
    st["trades"].append({"yon": side, "sinyal_ts": p["sinyal_ts"], "dolum_mum_ts": ts, "mum_acilis": o,
                         "referans_fiyat": ref, "dolum_fiyati": px, "adet": q, "komisyon": fee, "hedef": tgt,
                         "agirlik_sonra": round(mark_w(st, ref), 4)})
    st["log"].append(f"{paper.tr_time(ts)} {side} {q:.6f} BTC @ {px:,.0f}$ (hedef ağırlık %{tgt * 100:.0f}, "
                     f"sinyal {paper.tr_time(p['sinyal_ts'])})")


def step(st, candles, hook, now_ms, src):
    closes = [c[4] for c in candles]
    sig = signals.realized_vol(closes, WIN, 365 * 6) if len(closes) > WIN else [math.nan] * len(closes)
    for i, c in enumerate(candles):
        t, o, cl = c[0], c[1], c[4]
        if t <= st["last_ts"]:
            continue
        if st["pending"]:
            fill(st, hook, t, o)
        if (t + BAR4) % DAY == 0:
            s = sig[i]
            if s is None or math.isnan(s):
                st["log"].append(f"{paper.tr_time(t + BAR4)} Oynaklık hesaplanamadı (yetersiz veri), karar yok.")
            else:
                tgt = MAX_W if s <= 0 else min(MAX_W, VOL_TARGET / s)
                w = mark_w(st, cl)
                act = abs(tgt - w) > BAND
                st["kararlar"].append({"gun_sonu_ts": t + BAR4, "sigma": round(s, 4), "hedef": round(tgt, 4),
                                       "agirlik": round(w, 4), "islem": act})
                st["kararlar"] = st["kararlar"][-400:]
                if act:
                    st["pending"] = {"hedef": tgt, "sinyal_ts": t + BAR4}
        st["last_ts"], st["last_close"] = t, cl
    st["last_price"] = candles[-1][4]
    st["last_run"] = now_ms
    st["source"] = src
    st["log"] = st["log"][-80:]
    st["dolumlar"] = st.get("dolumlar", [])[-60:]


def _tr_ms(txt, ref_ms):
    """'dd.mm HH:MM' (İstanbul) → UTC ms; yıl, referans zamana en yakın olacak şekilde seçilir."""
    best = None
    y0 = datetime.fromtimestamp(ref_ms / 1000, paper.TR).year
    for y in (y0 - 1, y0, y0 + 1):
        try:
            ms = int(datetime.strptime(f"{y}.{txt}", "%Y.%d.%m %H:%M").replace(tzinfo=paper.TR).timestamp() * 1000)
        except ValueError:
            continue
        if best is None or abs(ms - ref_ms) < abs(best - ref_ms):
            best = ms
    return best


def ens_compare(vm_rows, now_ms):
    """Canlı ENS botunun kayıtları (salt okunur) ile aynı zaman damgalarında karşılaştırma:
    her VM-A kaydı, en fazla 20 dakika uzaktaki ENS kaydıyla eşleştirilir."""
    est = paper.load_json(os.path.join(ENS_DIR, "state.json"))
    path = os.path.join(ENS_DIR, "equity_history.csv")
    if not est or not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        ens = [(_tr_ms(r["zaman_istanbul"], now_ms), float(r["bakiye"])) for r in csv.DictReader(f)]
    ens = sorted(x for x in ens if x[0])
    pairs = []
    for r in vm_rows:
        t = int(r["utc_ms"])
        near = min(ens, key=lambda x: abs(x[0] - t), default=None)
        if near and abs(near[0] - t) <= 20 * 60_000:
            pairs.append((r, near))
    return {"ens": est, "ortak": pairs}


def write_report(st, rows):
    px = st.get("last_price") or st["last_close"]
    eq = value(st, px)
    bh = (px / st["start_price"] - 1) * 100
    L = ["# VM-A Canlı Kâğıt Test (oynaklık hedefli BTC)", "",
         "_SANAL paradır; gerçek emir verilmez. Yatırım tavsiyesi değildir. Kurallar: ön kayıt v2/v2.1 VM-A._", "",
         f"- Başlangıç: {paper.tr_time(st['test_start'])}, BTC {st['start_price']:,.0f}$ · son çalıştırma {paper.tr_time(st['last_run'])}",
         f"- Bakiye: **{eq:.2f}$** ({eq - 100:+.2f}%) · aynı sürede BTC al-tut {bh:+.2f}% · BTC ağırlığı %{mark_w(st, px) * 100:.1f}",
         f"- İşlem sayısı: {len(st['trades'])} · bekleyen emir: "
         + (f"hedef %{st['pending']['hedef'] * 100:.0f} (sinyal {paper.tr_time(st['pending']['sinyal_ts'])})" if st["pending"] else "yok"),
         f"- Veri: {st['source']}", ""]
    k = st["kararlar"][-1] if st["kararlar"] else None
    if k:
        L += [f"Son gün sonu kararı ({paper.tr_time(k['gun_sonu_ts'])}): σ %{k['sigma'] * 100:.1f}, hedef %{k['hedef'] * 100:.1f}, "
              f"mevcut ağırlık %{k['agirlik'] * 100:.1f} → {'işlem' if k['islem'] else 'bant içinde, işlem yok'}", ""]
    c = ens_compare(rows, st["last_run"])
    L += ["## ENS ile karşılaştırma (aynı zaman damgaları)", ""]
    if c:
        e = c["ens"]
        L += [f"Canlı ENS botu (Kırılım Ansamblı) {paper.tr_time(e['test_start'])} başladı; 7 günlük testi "
              f"{paper.tr_time(e['test_end'])} tarihinde biter (mevcut bot değiştirilmedi). ENS'de canlı %10 düşüş freni açık, "
              "VM-A'da yok (v2.1). Asıl ileri karşılaştırma, aynı kurallarla hesaplanan ön kayıt v2 hesabıdır.", ""]
        if len(c["ortak"]) >= 2:
            (a, ea), (b, eb) = c["ortak"][0], c["ortak"][-1]
            ve0, ve1 = float(a["bakiye"]), float(b["bakiye"])
            L += [f"Ortak dönem {a['zaman_istanbul']} → {b['zaman_istanbul']} ({len(c['ortak'])} eşleşen kayıt, en fazla 20 dk fark):", "",
                  "| Bot | Başlangıç | Son | Getiri |", "|---|---|---|---|",
                  f"| VM-A | {ve0:.2f}$ | {ve1:.2f}$ | {(ve1 / ve0 - 1) * 100:+.2f}% |",
                  f"| ENS | {ea[1]:.2f}$ | {eb[1]:.2f}$ | {(eb[1] / ea[1] - 1) * 100:+.2f}% |",
                  f"| BTC | {float(a['btc_fiyat']):,.0f}$ | {float(b['btc_fiyat']):,.0f}$ | "
                  f"{(float(b['btc_fiyat']) / float(a['btc_fiyat']) - 1) * 100:+.2f}% |", ""]
        else:
            L += ["Henüz yeterli ortak kayıt yok.", ""]
    else:
        L += ["ENS kayıtları okunamadı.", ""]
    L += ["## İşlemler (son 20)", "", "| Yön | Sinyal | Dolum mumu | Mum açılışı | 1 dk referans | Fark | Dolum (kayma dahil) | Adet | Hedef |",
          "|---|---|---|---|---|---|---|---|---|"]
    for t in st["trades"][-20:]:
        L.append(f"| {t['yon']} | {paper.tr_time(t['sinyal_ts'])} | {paper.tr_time(t['dolum_mum_ts'])} | {t['mum_acilis']:,.2f} | "
                 f"{t['referans_fiyat']:,.2f} | {(t['referans_fiyat'] / t['mum_acilis'] - 1) * 100:+.3f}% | {t['dolum_fiyati']:,.2f} | "
                 f"{t['adet']:.6f} | %{t['hedef'] * 100:.0f} |")
    L += ["", "## Dolum kayıtları (gerçekçi dolum, son 10)", "", "| Olay | Sinyal | Karar anı | Kayıt anı | Gecikme (dk) | 1 dk mum | Mum fiyatı | Referans | Fark % |",
          "|---|---|---|---|---|---|---|---|---|"]
    for d in st.get("dolumlar", [])[-10:]:
        L.append(f"| {d['olay']} | {d['sinyal_ts']} | {d['karar_ani_ts']} | {d['kayit_calismasi_ts']} | {d['gecikme_dk']} | "
                 f"{d['dakika_mumu_ts'] or '—'} | {d['mum_fiyati']} | {d['referans_fiyat'] or '—'} | {d['fark_pct'] if d['fark_pct'] is not None else '—'} |")
    L += ["", "1 dakikalık mum kapanışı gerçek işlem fiyatı değildir; bu bir simülasyondur.", "", "## Günlük", ""]
    L += [f"- {x}" for x in reversed(st["log"][-15:])]
    return "\n".join(L) + "\n"


# =================================================================== yalnızca raporlama (işlem mantığına dokunmaz)
def _mark_from_exit(exit_v, w):
    """Tasfiye değeri ve piyasa ağırlığından piyasa değeri (ENS raporlarıyla aynı esas: nakit + adet × fiyat)."""
    k = (1 - SLIP) * (1 - FEE)
    return exit_v / (1 - w + w * k)


def build_summary(st, rows):
    """6 saatlik rapor için ENS ve VM-A özeti + aynı başlangıç koşullarıyla günlük karşılaştırma.
    Eksik veri tahmin edilmez; 'yok' olarak yazılır."""
    px = st.get("last_price") or st["last_close"]
    mark = st["cash"] + st["qty"] * px
    k = st["kararlar"][-1] if st["kararlar"] else None
    lt = st["trades"][-1] if st["trades"] else None
    vm = {"bakiye_piyasa": round(mark, 4), "bakiye_tasfiye": round(value(st, px), 4),
          "toplam_getiri_pct": round(mark - 100, 3), "btc_ayni_surede_pct": round((px / st["start_price"] - 1) * 100, 3),
          "acik_pozisyon": (f"{st['qty']:.6f} BTC (≈{st['qty'] * px:.2f}$)" if st["qty"] > 0 else "yok"),
          "nakit_orani_pct": round(st["cash"] / mark * 100, 2) if mark > 0 else None,
          "son_karar": (f"{paper.tr_time(k['gun_sonu_ts'])} (hedef %{k['hedef'] * 100:.1f}, "
                        f"{'işlem' if k['islem'] else 'bant içinde, işlem yok'})") if k else "henüz gün sonu kararı yok",
          "son_islenen_mum_kapanisi": paper.tr_time(st["last_ts"] + BAR4),
          "son_dolum": (f"{lt['yon']} {lt['adet']:.6f} BTC @ {lt['dolum_fiyati']:,.2f}$ (dolum mumu "
                        f"{paper.tr_time(lt['dolum_mum_ts'])}, 1 dk referans {lt['referans_fiyat']:,.2f}$, "
                        f"mum açılışına göre {(lt['referans_fiyat'] / lt['mum_acilis'] - 1) * 100:+.3f}%)") if lt else "henüz dolum yok",
          "bekleyen": (f"hedef %{st['pending']['hedef'] * 100:.1f} (sinyal {paper.tr_time(st['pending']['sinyal_ts'])})"
                       if st["pending"] else "yok"),
          "baslangic": paper.tr_time(st["test_start"]), "son_calisma": paper.tr_time(st["last_run"])}
    est = paper.load_json(os.path.join(ENS_DIR, "state.json"))
    ens = None
    if est:
        epx = est.get("last_price") or est["last_close"]
        eq = S.equity(est, epx)
        subs = [x for x in est.get("subs", []) if x.get("position")]
        ld = (est.get("dolumlar") or [None])[-1]
        tr = est["trades"][-1] if est.get("trades") else None
        ens = {"bakiye_piyasa": round(eq, 4), "toplam_getiri_pct": round(eq - 100, 3),
               "btc_ayni_surede_pct": round((epx / est["start_price"] - 1) * 100, 3),
               "acik_pozisyon": (f"{len(subs)}/3 alt sistem pozisyonda, {est['qty']:.6f} BTC" if subs else "yok"),
               "nakit_orani_pct": round(est["cash"] / eq * 100, 2) if eq > 0 else None,
               "son_karar": f"{paper.tr_time(est['last_ts'] + BAR4)} (son değerlendirilen 4s mum kapanışı)",
               "son_dolum": (f"{ld['olay']} sinyal {ld['sinyal_ts']}, 1 dk referans {ld['referans_fiyat']}, mum fiyatı "
                             f"{ld['mum_fiyati']}, fark %{ld['fark_pct']}") if ld else
                            (f"son işlem: giriş {paper.tr_time(tr['entry_ts'])}, çıkış {paper.tr_time(tr['exit_ts'])}" if tr
                             else "henüz dolum yok"),
               "durum": "test bitti" if est.get("finished") else ("durdu (düşüş freni)" if est.get("halted") else "çalışıyor"),
               "baslangic": paper.tr_time(est["test_start"]), "bitis": paper.tr_time(est["test_end"]),
               "son_calisma": paper.tr_time(est.get("last_run", 0))}
    gunluk, eksik, temel = [], [], None
    c = ens_compare(rows, st["last_run"]) if est else None
    if c and c["ortak"]:
        def vm_mark(r):
            return _mark_from_exit(float(r["bakiye"]), float(r.get("btc_agirligi") or 0))
        r0, e0 = c["ortak"][0]
        temel = {"zaman": r0["zaman_istanbul"], "vm": vm_mark(r0), "ens": e0[1], "btc": float(r0["btc_fiyat"])}
        by_day = {}
        for r, e in c["ortak"]:
            day = datetime.fromtimestamp(int(r["utc_ms"]) / 1000, paper.TR).strftime("%Y-%m-%d")
            by_day[day] = (r, e)
        d0 = datetime.fromtimestamp(int(r0["utc_ms"]) / 1000, paper.TR).date()
        d1 = datetime.fromtimestamp(st["last_run"] / 1000, paper.TR).date()
        d = d0
        from datetime import timedelta
        end_d = datetime.fromtimestamp(est["test_end"] / 1000, paper.TR).date()
        while d <= d1:
            if est.get("finished") and d > end_d:
                break                                   # ENS testi bitti: sonraki günler eksik sayılmaz
            key = d.isoformat()
            if key in by_day:
                r, e = by_day[key]
                gunluk.append({"gun": key, "kayit": r["zaman_istanbul"],
                               "VM-A": round(vm_mark(r) / temel["vm"] * 100, 2),
                               "ENS": round(e[1] / temel["ens"] * 100, 2),
                               "BTC": round(float(r["btc_fiyat"]) / temel["btc"] * 100, 2)})
            else:
                eksik.append(key)
            d += timedelta(days=1)
    out = {"olusturma": paper.tr_time(st["last_run"]), "VM-A": vm, "ENS": ens,
           "karsilastirma": {"yontem": "İkisi de ortak ilk kayıtta 100'e eşitlenir; her gün, iki botun en fazla 20 dk arayla "
                                       "eşleşen son kaydı kullanılır. Değerler piyasa değeri esasındadır (nakit + adet × fiyat). "
                                       "Eşleşen kayıt olmayan gün tahmin edilmez, 'eksik' yazılır.",
                             "temel": temel, "gunluk": gunluk, "eksik_gunler": eksik,
                             "not": "ENS canlı testi 12.11'de biter; sonrasında ENS sütunu güncellenmez. ENS'de canlı %10 düşüş "
                                    "freni açık, VM-A'da yok. Asıl ileri karşılaştırma ön kayıt v2 hesabıdır."}}
    paper.save_json(os.path.join(OUT, "ozet.json"), out)
    L = ["", "## Günlük karşılaştırma (aynı başlangıç: ortak ilk kayıtta ikisi de 100)", "", out["karsilastirma"]["yontem"], ""]
    if gunluk:
        L += ["| Gün | Kayıt | VM-A | ENS | BTC |", "|---|---|---|---|---|"]
        L += [f"| {g['gun']} | {g['kayit']} | {g['VM-A']:.2f} | {g['ENS']:.2f} | {g['BTC']:.2f} |" for g in gunluk]
    else:
        L.append("Henüz eşleşen ortak kayıt yok.")
    if eksik:
        L += ["", "Eşleşen kayıt olmayan günler (tahmin edilmedi): " + ", ".join(eksik)]
    return "\n".join(L) + "\n"


def main():
    os.makedirs(OUT, exist_ok=True)
    now_ms = int(time.time() * 1000)
    sp = os.path.join(OUT, "state.json")
    st = paper.load_json(sp)
    candles, src = D.recent(1000, prefer=(st or {}).get("source", PREFER), interval="4h")
    if st is None:
        st = new_state(candles, now_ms, src)
    minutes, last_min = live_fill.fetch_minutes()
    hook = live_fill.make_hook(minutes, last_min, candles, BAR4, now_ms) if minutes else None
    step(st, candles, hook, now_ms, src)
    paper.save_json(sp, st)
    hp = os.path.join(OUT, "equity_history.csv")
    new = not os.path.exists(hp)
    px = st["last_price"]
    with open(hp, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["zaman_istanbul", "btc_fiyat", "bakiye", "islem_sayisi", "btc_agirligi", "utc_ms"])
        w.writerow([paper.tr_time(now_ms), round(px, 2), round(value(st, px), 4), len(st["trades"]),
                    round(mark_w(st, px), 4), now_ms])
    with open(hp, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    with open(os.path.join(OUT, "RAPOR.md"), "w", encoding="utf-8") as f:
        f.write(write_report(st, rows) + build_summary(st, rows))
    print(f"VM-A bakiye={value(st, px):.2f}$ işlem={len(st['trades'])} ağırlık={mark_w(st, px):.3f}")


if __name__ == "__main__":
    main()
