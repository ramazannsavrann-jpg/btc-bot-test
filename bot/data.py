"""
BTC/USDT 1 saatlik mum verisi. Sadece herkese açık fiyat verisi okunur:
API anahtarı yok, hesaba bağlanmak yok, gerçek emir yok.

GitHub sunucuları ABD'de olduğu için api.binance.com bazen engellenir; bu yüzden
sırayla birkaç kaynak denenir. Mum formatı: (açılış_ms, açılış, yüksek, düşük, kapanış, hacim)
"""
from __future__ import annotations

import io
import json
import time
import urllib.request
import zipfile
from datetime import datetime, timezone

HOUR_MS = 3_600_000
BAR_MS = {"1h": HOUR_MS, "15m": HOUR_MS // 4, "4h": 4 * HOUR_MS, "1m": 60_000}
OKX_BAR = {"1h": "1H", "15m": "15m", "4h": "4H"}
KRAKEN_MIN = {"1h": 60, "15m": 15, "4h": 240}
UA = {"User-Agent": "btc-bot-paper-test/1.0"}


def _get(url, timeout=30):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _norm_ts(ts):
    ts = int(ts)
    if ts > 10**14:   # 2025'ten beri Binance arşivi mikrosaniye kullanıyor
        ts //= 1000
    elif ts < 10**11:  # saniye
        ts *= 1000
    return ts


def _binance_rows(rows):
    return [(_norm_ts(r[0]), float(r[1]), float(r[2]), float(r[3]), float(r[4]), float(r[5]))
            for r in rows]


def _clean(candles, interval="1h", now_ms=None):
    """Sırala, tekrarları at, henüz kapanmamış son mumu çıkar."""
    now_ms = now_ms or int(time.time() * 1000)
    d = {}
    for c in candles:
        d[c[0]] = c
    out = [d[k] for k in sorted(d)]
    return [c for c in out if c[0] + BAR_MS[interval] <= now_ms]


# ------------------------------------------------------------ son mumlar (canlı)
def _recent_binance(base, limit, iv):
    url = f"{base}/api/v3/klines?symbol=BTCUSDT&interval={iv}&limit={limit}"
    return _binance_rows(json.loads(_get(url)))


def _recent_okx(limit, iv):
    out, after = [], ""
    while len(out) < limit:
        url = f"https://www.okx.com/api/v5/market/history-candles?instId=BTC-USDT&bar={OKX_BAR[iv]}&limit=100" + after
        rows = json.loads(_get(url))["data"]
        if not rows:
            break
        out += [(int(r[0]), float(r[1]), float(r[2]), float(r[3]), float(r[4]), float(r[5]))
                for r in rows]
        after = f"&after={rows[-1][0]}"
    return out


def _recent_kraken(limit, iv):
    data = json.loads(_get(f"https://api.kraken.com/0/public/OHLC?pair=XBTUSD&interval={KRAKEN_MIN[iv]}"))
    rows = next(v for k, v in data["result"].items() if k != "last")
    return [(int(r[0]) * 1000, float(r[1]), float(r[2]), float(r[3]), float(r[4]), float(r[6]))
            for r in rows][-limit:]


RECENT_SOURCES = [
    ("Binance (data-api.binance.vision)", lambda n, iv: _recent_binance("https://data-api.binance.vision", n, iv)),
    ("Binance (api.binance.com)", lambda n, iv: _recent_binance("https://api.binance.com", n, iv)),
    ("Binance US", lambda n, iv: _recent_binance("https://api.binance.us", n, iv)),
    ("OKX", _recent_okx),
    ("Kraken", _recent_kraken),
]


def recent(limit=1000, prefer=None, interval="1h"):
    """Son `limit` kapanmış 1s mum + kaynak adı. `prefer`: önce denenecek kaynak (test boyunca aynı kalsın)."""
    errors = []
    sources = sorted(RECENT_SOURCES, key=lambda s: s[0] != prefer)
    for name, fn in sources:
        try:
            c = _clean(fn(limit, interval), interval)
            if len(c) >= 300:
                return c, name
            errors.append(f"{name}: az veri ({len(c)})")
        except Exception as e:  # noqa: BLE001
            errors.append(f"{name}: {e}")
    raise RuntimeError("Fiyat verisi alınamadı: " + " | ".join(errors))


# ------------------------------------------------------------ geçmiş (2 yıl)
def _month_list(months):
    now = datetime.now(timezone.utc)
    y, m = now.year, now.month
    out = []
    for _ in range(months):
        m -= 1
        if m == 0:
            y, m = y - 1, 12
        out.append(f"{y}-{m:02d}")
    return list(reversed(out))


def _history_vision(months, iv):
    out = []
    for ym in _month_list(months):
        url = f"https://data.binance.vision/data/spot/monthly/klines/BTCUSDT/{iv}/BTCUSDT-{iv}-{ym}.zip"
        z = zipfile.ZipFile(io.BytesIO(_get(url, 60)))
        text = z.read(z.namelist()[0]).decode()
        for line in text.splitlines():
            parts = line.split(",")
            if not parts[0].strip().isdigit():
                continue  # başlık satırı
            out.append(parts)
    return _binance_rows(out)


def _history_paged(base, months, iv):
    start = int(time.time() * 1000) - months * 30 * 24 * HOUR_MS
    out = []
    while True:
        url = f"{base}/api/v3/klines?symbol=BTCUSDT&interval={iv}&limit=1000&startTime={start}"
        rows = _binance_rows(json.loads(_get(url)))
        if not rows:
            break
        out += rows
        start = rows[-1][0] + BAR_MS[iv]
        if len(rows) < 1000:
            break
        time.sleep(0.2)
    return out


HISTORY_SOURCES = [
    ("Binance arşivi (data.binance.vision)", _history_vision),
    ("Binance (data-api.binance.vision)", lambda m, iv: _history_paged("https://data-api.binance.vision", m, iv)),
    ("Binance (api.binance.com)", lambda m, iv: _history_paged("https://api.binance.com", m, iv)),
    ("Binance US", lambda m, iv: _history_paged("https://api.binance.us", m, iv)),
]


def history(months=24, interval="1h"):
    errors = []
    for name, fn in HISTORY_SOURCES:
        try:
            c = _clean(fn(months, interval), interval)
            if len(c) >= 24 * 30 * 3:
                return c, name
            errors.append(f"{name}: az veri ({len(c)})")
        except Exception as e:  # noqa: BLE001
            errors.append(f"{name}: {e}")
    raise RuntimeError("Geçmiş veri alınamadı: " + " | ".join(errors))


# ================================================================ çoklu coin
STABLE = {"USDC", "FDUSD", "TUSD", "USDP", "DAI", "BUSD", "EUR", "USD1", "XUSD", "RLUSD", "PYUSD", "U",
          "AEUR", "EURI", "USDE", "BFUSD", "PAXG", "WBTC", "WBETH", "BNSOL", "WSTETH", "RWUSD", "USDF"}
# kripto olmayan ürünler: tokenize altın/hisse/ETF
NON_CRYPTO = {"XAUT", "PAXG", "MUB", "SNDKB", "SOXLB", "SPCXB", "CRCLB", "GOOGLB", "MSTRB", "TSLAB", "NVDAB",
              "AAPLB", "COINB", "HOODB", "METAB", "AMZNB", "QQQB", "SPYB"}
CRYPTO_B = set()   # 'B' ile biten gerçek kripto çıkarsa buraya eklenir

# Geçmiş test için aday havuzu: Kasım 2024 civarında Binance'te en çok işlem gören coinler
# (bugünün listesi değil). İlk ayın hacmine göre içlerinden en büyük 30'u seçilir.
HIST_POOL = ["BTC", "ETH", "SOL", "XRP", "DOGE", "BNB", "ADA", "PEPE", "SHIB", "SUI", "AVAX", "LINK", "TRX",
             "LTC", "DOT", "NEAR", "WIF", "BONK", "FET", "TON", "APT", "ARB", "OP", "FLOKI", "HBAR", "BCH",
             "UNI", "ATOM", "FIL", "INJ", "SEI", "TIA", "RENDER", "WLD", "ORDI", "ENA", "PNUT", "NEIRO",
             "ACT", "TAO", "XLM", "ETC", "ICP", "AAVE", "JUP", "EIGEN", "BOME", "NOT", "PEOPLE", "CRV"]


def _sym_recent_binance(base, sym, limit, iv):
    url = f"{base}/api/v3/klines?symbol={sym}USDT&interval={iv}&limit={limit}"
    return _binance_rows(json.loads(_get(url)))


def recent_symbol(sym, limit=1000, interval="1h"):
    errors = []
    for base in ("https://data-api.binance.vision", "https://api.binance.com"):
        try:
            c = _clean(_sym_recent_binance(base, sym, limit, interval), interval)
            if c:
                return c
        except Exception as e:  # noqa: BLE001
            errors.append(f"{base}: {e}")
    raise RuntimeError(f"{sym} verisi alınamadı: " + " | ".join(errors))


def history_symbol(sym, months=24, interval="1h"):
    """Binance arşivinden coin geçmişi; listelenmeden önceki aylar atlanır."""
    out = []
    for ym in _month_list(months):
        url = (f"https://data.binance.vision/data/spot/monthly/klines/{sym}USDT/{interval}/"
               f"{sym}USDT-{interval}-{ym}.zip")
        try:
            z = zipfile.ZipFile(io.BytesIO(_get(url, 60)))
        except Exception:  # noqa: BLE001
            continue  # o ay listede değil
        for line in z.read(z.namelist()[0]).decode().splitlines():
            parts = line.split(",")
            if parts[0].strip().isdigit():
                out.append(parts)
    return _clean(_binance_rows(out), interval)


def top_symbols(n=30):
    """Şu anki 24 saatlik USDT hacmine göre en büyük n coin (stabil coin ve kaldıraçlı tokenler hariç)."""
    for base in ("https://data-api.binance.vision", "https://api.binance.com"):
        try:
            rows = json.loads(_get(f"{base}/api/v3/ticker/24hr", 60))
            break
        except Exception:  # noqa: BLE001
            rows = None
    if not rows:
        raise RuntimeError("Coin listesi alınamadı")
    cands = []
    for r in rows:
        s = r["symbol"]
        if not s.endswith("USDT"):
            continue
        base = s[:-4]
        if base in STABLE or base in NON_CRYPTO or base.endswith(("UP", "DOWN", "BULL", "BEAR")) or not base.isalnum():
            continue
        if len(base) >= 5 and base.endswith("B") and base[:-1].isalpha() and base not in CRYPTO_B:
            continue  # tokenize hisse/ETF (ör. GOOGLB, MSTRB)
        if float(r.get("lastPrice", 0)) <= 0 or int(r.get("count", 0)) == 0:
            continue
        cands.append((float(r["quoteVolume"]), base))
    cands.sort(reverse=True)
    return [b for _, b in cands[:n]]


def history_universe(months=24, n=30, interval="1h", log=print):
    """Havuzdaki her coinin geçmişini indirir; İLK AYIN hacmine göre en büyük n coini seçer."""
    data = {}
    for sym in HIST_POOL:
        try:
            c = history_symbol(sym, months, interval)
        except Exception as e:  # noqa: BLE001
            log(f"{sym}: {e}")
            continue
        if len(c) > 24 * 30:
            data[sym] = c
    if "BTC" not in data:
        raise RuntimeError("BTC geçmişi yok")
    t0 = data["BTC"][0][0]
    first_month = t0 + 30 * 24 * HOUR_MS
    vol = {}
    for sym, c in data.items():
        vol[sym] = sum(x[5] * x[4] for x in c if x[0] < first_month)   # yaklaşık USDT hacmi
    chosen = [s for s, v in sorted(vol.items(), key=lambda kv: -kv[1]) if v > 0][:n]
    if "BTC" not in chosen:
        chosen = ["BTC"] + chosen[:n - 1]
    log(f"Geçmiş evren ({len(chosen)} coin, ilk ay hacmine göre): {', '.join(chosen)}")
    return {s: data[s] for s in chosen}


def aggregate(candles, hours=4):
    """1 saatlik mumları N saatlik mumlara birleştirir (UTC hizalı, sadece tamamlanmış mumlar)."""
    step = hours * HOUR_MS
    out, cur = [], None
    for c in candles:
        k = c[0] // step * step
        if cur is None or cur[0] != k:
            if cur and cur[6] == hours:
                out.append(tuple(cur[:6]))
            cur = [k, c[1], c[2], c[3], c[4], c[5], 1]
        else:
            cur[2] = max(cur[2], c[2]); cur[3] = min(cur[3], c[3]); cur[4] = c[4]; cur[5] += c[5]; cur[6] += 1
    if cur and cur[6] == hours:
        out.append(tuple(cur[:6]))
    return out
