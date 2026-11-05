"""
Dış veri: (1) ABD ekonomik olay takvimi (FOMC faiz kararı, CPI enflasyon), (2) Kripto Korku & Açgözlülük Endeksi.

Haberlerle YÖN tahmini yapılmaz; bunlar RİSK FİLTRESİ olarak kullanılır:
  * event_pause: büyük açıklamadan önce/sonra yeni pozisyon açılmaz.
  * fg_max     : endeks bu değerin üstündeyse (aşırı açgözlülük) alım yapılmaz.
  * fear_dip   : endeks çok düşükken (aşırı korku) dip alımı yapan ayrı strateji.
Geleceği görmemek için endeksin bir ÖNCEKİ günkü değeri kullanılır.
"""
from __future__ import annotations

import json
import urllib.request
from datetime import datetime, timezone

HOUR_MS = 3_600_000
DAY_MS = 24 * HOUR_MS

# Kaynak: federalreserve.gov FOMC takvimi (2022–2026).
FOMC_DATES = [
    "2022-11-02", "2022-12-14",
    "2023-02-01", "2023-03-22", "2023-05-03", "2023-06-14", "2023-07-26", "2023-09-20", "2023-11-01", "2023-12-13",
    "2024-01-31", "2024-03-20", "2024-05-01", "2024-06-12", "2024-07-31", "2024-09-18", "2024-11-07", "2024-12-18",
    "2025-01-29", "2025-03-19", "2025-05-07", "2025-06-18", "2025-07-30", "2025-09-17", "2025-10-29", "2025-12-10",
    "2026-01-28", "2026-03-18", "2026-04-29", "2026-06-17", "2026-07-29", "2026-09-16", "2026-10-28", "2026-12-09",
]
# Kaynak: BLS takvimi. Ekim 2025 CPI iptal edildi (kapanma), Kasım 2025 CPI 18 Aralık'a ertelendi,
# Eylül 2025 CPI 24 Ekim'e ertelendi.
CPI_DATES = [
    "2022-11-10", "2022-12-13",
    "2023-01-12", "2023-02-14", "2023-03-14", "2023-04-12", "2023-05-10", "2023-06-13", "2023-07-12",
    "2023-08-10", "2023-09-13", "2023-10-12", "2023-11-14", "2023-12-12",
    "2024-01-11", "2024-02-13", "2024-03-12", "2024-04-10", "2024-05-15", "2024-06-12", "2024-07-11",
    "2024-08-14", "2024-09-11", "2024-10-10", "2024-11-13", "2024-12-11",
    "2025-01-15", "2025-02-12", "2025-03-12", "2025-04-10", "2025-05-13", "2025-06-11", "2025-07-15",
    "2025-08-12", "2025-09-11", "2025-10-24", "2025-12-18",
    "2026-01-13", "2026-02-13", "2026-03-11", "2026-04-10", "2026-05-12", "2026-06-10", "2026-07-14",
    "2026-08-12", "2026-09-11", "2026-10-14", "2026-11-10", "2026-12-10",
]
# ABD yaz saati (EDT) aralıkları: bu aralıkta ET = UTC-4, dışında UTC-5
DST = [("2022-03-13", "2022-11-06"), ("2023-03-12", "2023-11-05"), ("2024-03-10", "2024-11-03"),
       ("2025-03-09", "2025-11-02"), ("2026-03-08", "2026-11-01")]


def _utc_ms(day, et_hour, et_min):
    edt = any(a <= day < b for a, b in DST)
    h = et_hour + (4 if edt else 5)
    d = datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return int(d.timestamp() * 1000) + h * HOUR_MS + et_min * 60_000


EVENTS = sorted([(_utc_ms(d, 14, 0), "FOMC faiz kararı") for d in FOMC_DATES]
                + [(_utc_ms(d, 8, 30), "CPI enflasyon") for d in CPI_DATES])

FG: dict[int, int] = {}   # gün_indeksi (UTC) -> değer


def event_near(ts, before_h=4, after_h=4):
    """ts anında [olay-before, olay+after] penceresinde miyiz? Olay adını döndürür."""
    for ets, name in EVENTS:
        if ets - before_h * HOUR_MS <= ts <= ets + after_h * HOUR_MS:
            return name
    return None


def fg_value(ts):
    """ts gününden BİR ÖNCEKİ günün endeks değeri (yoksa None)."""
    return FG.get(ts // DAY_MS - 1)


def load_fear_greed(limit=0):
    """alternative.me'den endeksi yükler. limit=0 tüm geçmiş. Hata olursa False döner."""
    try:
        url = f"https://api.alternative.me/fng/?limit={limit}&format=json"
        req = urllib.request.Request(url, headers={"User-Agent": "btc-bot-paper-test/1.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            rows = json.loads(r.read())["data"]
        for row in rows:
            FG[int(row["timestamp"]) * 1000 // DAY_MS] = int(row["value"])
        return len(rows) > 0
    except Exception as e:  # noqa: BLE001
        print("Korku & Açgözlülük verisi alınamadı:", e)
        return False


def entry_blocked(p, ts):
    """Filtreler alıma izin vermiyorsa sebebi döndürür."""
    if p.get("event_pause"):
        name = event_near(ts, p.get("event_before", 4), p.get("event_after", 4))
        if name:
            return name
    m = p.get("fg_max")
    if m:
        v = fg_value(ts)
        if v is not None and v >= m:
            return "aşırı açgözlülük"
    return None
