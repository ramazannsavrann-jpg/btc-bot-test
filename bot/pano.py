"""
Sonuç panosu için sade veri dosyaları (results/pano/*.json). Her çalıştırmada yeniden yazılır.
Pano (Claude'daki sayfa) bu dosyaları 6 saatte bir okur.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from . import multi_live, paper, strategy as S


def iso(ms):
    return datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat(timespec="minutes").replace("+00:00", "Z")


def _durum(st):
    if st.get("finished"):
        return "Bitti"
    if st.get("halted"):
        return "Durdu (fren)"
    el = (min(st.get("last_run", st["test_start"]), st["test_end"]) - st["test_start"]) / S.HOUR_MS
    return f"Gün {min(7, int(el // 24) + 1)}/7"


def _acik(st, px):
    if st.get("multi"):
        from . import multi
        return multi.describe_open(st) or "Yok"
    from . import engines
    return engines.get(st["params"]).describe_open(st, px) or "Yok"


def write(out_dir, rows, tour, ctour):
    d = os.path.join(out_dir, "pano")
    os.makedirs(d, exist_ok=True)
    botlar, gecmis, olaylar = [], [], []
    for b, st in rows:
        multi = bool(st.get("multi"))
        if multi:
            s = multi_live.stats(st)
            px = st["last_price"]
        else:
            px = st.get("last_price") or st["last_close"]
            s = S.stats(st, px)
        bh = (px / st["start_price"] - 1) * 100 if st.get("start_price") else 0.0
        botlar.append({
            "bot": b["title"], "tur": "30 coin" if multi else "Sadece BTC",
            "bakiye": round(s["equity"], 2), "getiri_pct": round(s["return_pct"], 2),
            "btc_al_tut_pct": round(bh, 2), "islem": s["trades"], "kazanan": s["wins"],
            "basari_pct": round(s["win_rate"], 1), "durum": _durum(st), "acik_pozisyon": _acik(st, px),
            "baslangic": iso(st["test_start"]),
        })
        for sn in st.get("snapshots", []):
            gecmis.append({"zaman": iso(sn["ts"]), "bot": b["title"], "bakiye": sn["equity"]})
        for line in st.get("log", [])[-12:]:
            # "dd.mm HH:MM metin" biçimi
            olaylar.append({"bot": b["title"], "zaman": line[:11], "olay": line[12:]})
    olaylar.sort(key=lambda r: (r["zaman"][3:5], r["zaman"][:2], r["zaman"][6:]), reverse=True)

    turnuva = []
    for cat, t in (("Sadece BTC", tour), ("30 coin", ctour)):
        if not t:
            continue
        for k, r in enumerate(t["sonuclar"], 1):
            s = r["sinav"]
            turnuva.append({"sira": k, "kategori": cat, "bot": r["baslik"], "son_bakiye": s["son_bakiye"],
                            "iki_kat_maliyet": r["sinav_2x_maliyet"]["son_bakiye"],
                            "haftalik_islem": s["haftalik_islem"], "basari_pct": s["basari_pct"],
                            "max_dusus_pct": s["max_dusus_pct"], "btc_al_tut_pct": s["al_tut_pct"],
                            "yeterli_islem": "Evet" if r["uygun"] else "Hayır"})

    last = max((st.get("last_run", 0) for _, st in rows), default=0)
    btc_now = next((st.get("last_price") for _, st in rows if st.get("last_price")), None)
    first = min(rows, key=lambda r: r[1]["test_start"])[1] if rows else None
    ozet = [{
        "guncelleme": iso(last) if last else None,
        "guncelleme_tr": paper.tr_time(last) if last else "-",
        "btc_fiyat": round(btc_now, 0) if btc_now else None,
        "btc_degisim_pct": round((btc_now / first["start_price"] - 1) * 100, 2) if first and btc_now else None,
        "bot_sayisi": len(rows),
        "toplam_islem": sum(r["islem"] for r in botlar),
    }]
    for name, data in (("botlar", botlar), ("bakiye_gecmisi", gecmis), ("olaylar", olaylar[:30]),
                       ("turnuva", turnuva), ("ozet", ozet)):
        with open(os.path.join(d, f"{name}.json"), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=0)
