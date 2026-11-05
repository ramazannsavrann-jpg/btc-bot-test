"""
Canlı kâğıt testte gerçekçi dolum (ön kayıt v1, madde 7) — 5 Kasım 2026'dan itibaren YENİ işlemler için.

Bot, sinyal mumu kapandıktan sonra GitHub Actions çalıştığında devreye girer. Motor, dolumu bir sonraki mum
kapandığında kaydeder; fiyat ise kararın verilebileceği andan alınır (karar_ani_ts). Dolum referansı:
  olay anı + gerçek gecikme (çalışma anı − son kapanan mumun kapanışı) anında KAPANMIŞ 1 dakikalık mumun kapanışı.
Normal durumda bu, çalışma anındaki son kapanmış 1 dakikalık mumdur. Kayma ve komisyon bunun üstüne BİR KEZ uygulanır.
Bu bir simülasyondur: 1 dakikalık mum kapanışı gerçek işlem fiyatı değildir.
Stoplar (borsada bekleyen emir) ve grid kademe emirleri (limit emir) gecikmesizdir.
30 coin botlarında henüz uygulanmadı (her coin için 1 dk veri gerekir) — raporda belirtilir.
"""
from __future__ import annotations

from . import data, paper, strategy as S

MIN = 60_000


def fetch_minutes():
    try:
        rows = data.recent_symbol("BTC", 1000, "1m")
        return {c[0]: c[4] for c in rows}, (rows[-1][0] if rows else None)
    except Exception as e:  # noqa: BLE001
        print("1 dk veri alınamadı:", e)
        return {}, None


def make_hook(minutes, last_min_open, candles, bar_ms, now_ms):
    data_close = candles[-1][0] + bar_ms            # son kapanmış mumun kapanış anı
    delay = max(0, now_ms - data_close)

    def hook(kind, t_event, px, state):
        target = t_event + delay
        k = (target // MIN) * MIN - MIN               # target anında kapanan dakikanın açılışı
        if last_min_open is not None:
            k = min(k, last_min_open)
        v = minutes.get(k)
        rec = {"olay": kind, "sinyal_ts": paper.tr_time(t_event),
               "karar_ani_ts": paper.tr_time(t_event + delay),      # sinyal + gerçek çalışma gecikmesi
               "kayit_calismasi_ts": paper.tr_time(now_ms), "veri_ts": paper.tr_time(data_close),
               "gecikme_dk": round(delay / MIN, 1),
               "dakika_mumu_ts": paper.tr_time(k + MIN) if v else None,
               "mum_fiyati": round(px, 2), "referans_fiyat": round(v, 2) if v else None,
               "fark_pct": round((v / px - 1) * 100, 4) if v else None,
               "not": "simülasyon; 1 dk mum kapanışı gerçek işlem fiyatı değildir" if v else "1 dk veri yok, mum fiyatı kullanıldı"}
        state.setdefault("dolumlar", []).append(rec)
        state["dolumlar"] = state["dolumlar"][-40:]
        return v if v else px
    return hook


def run_with_hook(fn, minutes, last_min, candles, bar_ms, now_ms):
    S.FILL_HOOK = make_hook(minutes, last_min, candles, bar_ms, now_ms) if minutes else None
    try:
        return fn()
    finally:
        S.FILL_HOOK = None
