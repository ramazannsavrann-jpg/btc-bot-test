"""
Ön Kayıt v2 / v2.1 hesabı: VM-A varsayılan, Kırılım Ansamblı (ENS) ayı piyasası koruma kuralı.

Kurallar: docs/ON_KAYIT_v2.md ve docs/ON_KAYIT_v2_1.md (bu dosya onların uygulamasıdır; çelişkide belge geçerlidir).
Çalıştırma: python -m bot.onkayit_v2        (GitHub Actions: .github/workflows/onkayit_v2.yml)

Sıra:
  1) Doğrulama testleri (v1 yeniden üretimi, eşitlik, sızıntı, birim testler). Kritik test kalırsa
     geçmiş ve ileri sonuçlar YAYINLANMAZ, yalnızca test raporu yazılır.
  2) Geçmiş veri (2017-12-01 → 2026-10-31): keşifsel, geçici varsayılan.
  3) İleri (temiz) veri (2026-11-06 00:00 UTC'den sonra): yalnızca gözlem.
Her çalıştırma results/v2/<zaman>_<çalıştırma>/ klasörüne yazılır; önceki çalıştırmaların üzerine yazılmaz.
Mevcut motor dosyaları (strategy, ensemble, signals, validate …) DEĞİŞTİRİLMEZ, yalnızca çağrılır.
"""
from __future__ import annotations

import hashlib
import io
import json
import math
import os
import platform
import random
import subprocess
import sys
import time
import zipfile
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import numpy as np

from . import data as D, ensemble as E, external, research, signals, strategy as S, validate as V

H = S.HOUR_MS
DAY = 24 * H
BAR4 = 4 * H
UTC = timezone.utc

# ------------------------------------------------------------------ ön kayıtla sabitlenen değerler
DOCS = {
    "docs/ON_KAYIT_v2.md": "dd485f66656068e6ffe414391c8cd175b00dd79147fe0d033f2863d41b19343a",
    "docs/ON_KAYIT_v2_1.md": "4a194a3ab5c71ed84fbd2501e1a38971357526e6b20b58c4c5245ba57888e230",
}
V1_COMMIT = "b50bae221ec0e715dd6d50f26416fa38fd05efe5"      # v1 doğrulama sonucunu (results/dogrulama.json) üreten çalıştırmanın commit'i
ENGINE_FILES = ["bot/data.py", "bot/strategy.py", "bot/ensemble.py", "bot/signals.py", "bot/research.py",
                "bot/research_candidates.py", "bot/engines.py", "bot/external.py", "bot/validate.py"]
T_KAYIT = int(datetime(2026, 11, 5, 12, 35, 2, tzinfo=UTC).timestamp() * 1000)   # v2.1 push (geç olan)
PERF_START = -(-T_KAYIT // DAY) * DAY             # kayıttan sonraki ilk tam UTC günü = 2026-11-06
HIST_START, HIST_END = V.ts("2017-12-01"), V.ts("2026-11-01")
DROP_RATIO = Decimal("0.60")                        # C_t1 <= 0,60 × C_t0  ⇔  düşüş >= %40
THR_PP, THR_REL, THR_CAGR = 0.10, 0.25, 0.02
VOL_TARGET, MAX_W, BAND = 0.40, 0.99, 0.05
VM_WIN = {"VM-A": 540, "VM-B": 180}                 # 4s getiri sayısı (90 / 30 gün)
COSTS = {"1x": (0.001, 0.0005), "2x": (0.002, 0.001)}   # (komisyon, kayma)
N_TOTAL = 266                                       # 263 (v1) + VM-A, VM-B, VM-ref
SEED = 20261105
ARCH = "https://data.binance.vision/data/spot"

# v1 doğrulamasının kayıtlı özetleri (results/dogrulama.json, 2026-11-05) — yeniden üretim hedefi
V1_REF_FILE = "results/dogrulama.json"

LOG: list[str] = []


def log(*a):
    s = " ".join(str(x) for x in a)
    LOG.append(s)
    print(s, flush=True)


def iso(ms):
    return datetime.fromtimestamp(ms / 1000, UTC).strftime("%Y-%m-%d %H:%M UTC")


def dstr(day):
    return datetime.fromtimestamp(day * DAY / 1000, UTC).strftime("%Y-%m-%d")


def sha256_file(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


# =================================================================== veri (ücretsiz Binance arşivi)
def _fetch_zip(url):
    raw = D._get(url, 90)
    sha = hashlib.sha256(raw).hexdigest()
    try:
        ck = D._get(url + ".CHECKSUM", 30).decode().split()[0].strip().lower()
        ok = ck == sha
    except Exception:  # noqa: BLE001
        ok = None
    z = zipfile.ZipFile(io.BytesIO(raw))
    rows = []
    for line in z.read(z.namelist()[0]).decode().splitlines():
        parts = line.split(",")
        if parts[0].strip().isdigit():
            rows.append(parts)
    return rows, sha, ok


def load_1h(now_ms):
    """BTCUSDT 1s mumları: tamamlanmış aylar aylık dosyadan, son aylar günlük dosyalardan.
    Her dosyanın SHA-256'sı kaydedilir ve Binance .CHECKSUM ile karşılaştırılır."""
    today = datetime.fromtimestamp(now_ms / 1000, UTC).date()
    last_full_day = today - timedelta(days=1)
    files, rows, problems, notes = [], [], [], []
    y, m = 2017, 8
    while (y, m) <= (today.year, today.month):
        ym = f"{y}-{m:02d}"
        url = f"{ARCH}/monthly/klines/BTCUSDT/1h/BTCUSDT-1h-{ym}.zip"
        try:
            r, sha, ok = _fetch_zip(url)
            rows += r
            files.append({"dosya": url.rsplit("/", 1)[1], "sha256": sha, "checksum_ok": ok, "satir": len(r)})
        except Exception as e:  # noqa: BLE001
            recent = (today.year * 12 + today.month) - (y * 12 + m) <= 1
            if not recent:
                problems.append(f"aylık dosya alınamadı: {ym} ({e})")
            else:
                d = date(y, m, 1)
                while d.month == m and d <= last_full_day:
                    du = f"{ARCH}/daily/klines/BTCUSDT/1h/BTCUSDT-1h-{d.isoformat()}.zip"
                    try:
                        r, sha, ok = _fetch_zip(du)
                        rows += r
                        files.append({"dosya": du.rsplit("/", 1)[1], "sha256": sha, "checksum_ok": ok,
                                      "satir": len(r)})
                    except Exception as e2:  # noqa: BLE001
                        if d == last_full_day:
                            notes.append(f"{d} günlük dosyası henüz yayınlanmamış (Binance ertesi gün yayınlar)")
                        else:
                            problems.append(f"günlük dosya alınamadı: {d} ({e2})")
                    d += timedelta(days=1)
        m += 1
        if m > 12:
            y, m = y + 1, 1
    c1 = D._clean(D._binance_rows(rows), "1h", now_ms)
    return c1, files, problems, notes


def dataset_hash(c):
    h = hashlib.sha256()
    for x in c:
        h.update((",".join(repr(v) for v in x) + "\n").encode())
    return h.hexdigest()


def data_stats(c1):
    gaps = sum(1 for i in range(1, len(c1)) if c1[i][0] - c1[i - 1][0] > H)
    missing = sum((c1[i][0] - c1[i - 1][0]) // H - 1 for i in range(1, len(c1)) if c1[i][0] - c1[i - 1][0] > H)
    return {"mum_1s": len(c1), "bosluk_sayisi": gaps, "eksik_1s_mum": int(missing),
            "ilk": V.fmt(c1[0][0]), "son": V.fmt(c1[-1][0])}


def daily_close(c1):
    """v2.1 §2: günlük kapanış = açılışı 23:00 UTC olan 1s mumun kapanışı, kesin ondalık.
    Arşivdeki metin en fazla 8 ondalıklı olduğundan float'ın en kısa gösterimi (repr) metni birebir verir."""
    return {c[0] // DAY: Decimal(repr(c[4])) for c in c1 if c[0] % DAY == 23 * H}


# =================================================================== ayı dönemleri (v2 §4, v2.1 §2)
def find_spells(dc, day_to):
    """dc: {gün: kapanış (Decimal)}; 2017-08-17'den day_to'ya kadar (dahil) bütün geçmiş.
    Su altı dönemleri ayrık olur: dönem ancak kapanış zirveye eşit/üstüne çıkınca biter, yeni zirveden önce
    tekrar düşüş aynı dönemin parçasıdır (dip = dönemin en düşük kapanışı, eşitlikte en erken gün)."""
    spells, P, t0, cur = [], None, None, None
    for d in sorted(k for k in dc if k <= day_to):
        C = dc[d]
        if P is None or C >= P:
            if cur is not None:
                cur["t2"] = d
                spells.append(cur)
                cur = None
            P, t0 = max(P, C) if P is not None else C, d     # C = P olan son gün t0 olur
            continue
        if cur is None:
            cur = {"t0": t0, "P": P, "t1": d, "C1": C, "t2": None}
        elif C < cur["C1"]:
            cur["t1"], cur["C1"] = d, C
    if cur is not None:
        spells.append(cur)
    for s in spells:
        s["big"] = s["C1"] <= s["P"] * DROP_RATIO
        s["complete"] = s["t2"] is not None
        s["depth"] = float(s["C1"] / s["P"] - 1)
    return spells


def test_spells():
    """Belirleyici birim testleri: eşitlik, tam %40, çift dip, eşit dip, eksik gün, tamamlanmamış dönem."""
    def run(vals, day_to=None):
        dc = {i: Decimal(str(v)) for i, v in vals.items()} if isinstance(vals, dict) else \
            {i: Decimal(str(v)) for i, v in enumerate(vals)}
        return find_spells(dc, max(dc) if day_to is None else day_to)
    cases = []
    s = run([100, 90, 50, 70, 100])
    cases.append(("basit dönem", len(s) == 1 and (s[0]["t0"], s[0]["t1"], s[0]["t2"]) == (0, 2, 4) and s[0]["big"]))
    s = run([100, 100, 80, 100, "59.99", 101])
    cases.append(("eşit zirve: t0 = C=P olan son gün; eşitlikte toparlanma",
                  len(s) == 2 and (s[0]["t0"], s[0]["t2"], s[0]["big"]) == (1, 3, False)
                  and (s[1]["t0"], s[1]["t1"], s[1]["t2"], s[1]["big"]) == (3, 4, 5, True)))
    cases.append(("tam %40 düşüş büyük sayılır", run([100, 60, 100])[0]["big"] is True))
    cases.append(("%39,99 düşüş büyük sayılmaz", run([100, "60.01", 100])[0]["big"] is False))
    s = run([100, 50, 90, 55, 40, 100])
    cases.append(("yeni zirvesiz ikinci düşüş aynı dönem", len(s) == 1 and s[0]["t1"] == 4))
    s = run([100, 50, 70, 50, 100])
    cases.append(("eşit dipte en erken gün", s[0]["t1"] == 1))
    s = run([100, 50, 70])
    cases.append(("tamamlanmamış dönem", s[0]["t2"] is None and not s[0]["complete"]))
    s = run({0: 100, 2: 50, 3: 100})
    cases.append(("eksik gün atlanır, doldurulmaz", (s[0]["t0"], s[0]["t1"], s[0]["t2"]) == (0, 2, 3)))
    s = run([100, 50, 100, 120, 70, 130])
    cases.append(("ardışık dönemler çakışmaz", len(s) == 2 and s[0]["t2"] <= s[1]["t0"]))
    return cases


# =================================================================== VM (oynaklık hedefli BTC)
class VM:
    """v2 §2 / v2.1 §3. Karar günün son 4s kapanışında, işlem bir sonraki 4s açılışında.
    Maliyet formülleri motorla (strategy._open_position/_close_position) birebir aynıdır."""

    def __init__(self, fee, slip, eq0=100.0):
        self.fee, self.slip = fee, slip
        self.cash, self.qty = eq0, 0.0
        self.pending = None
        self.trades = []
        self.max_trade_w = 0.0

    def mark_w(self, px):
        m = self.cash + self.qty * px
        return self.qty * px / m if m > 0 else 0.0

    def on_open(self, ts, o):
        if self.pending is None:
            return
        tgt, self.pending = self.pending, None
        mark = self.cash + self.qty * o
        delta = tgt * mark - self.qty * o
        if delta > 0:
            spend = min(delta, self.cash)
            if spend <= 0:
                return
            n = spend / (1 + self.fee)
            px = o * (1 + self.slip)
            q = n / px
            self.qty += q
            self.cash -= n + n * self.fee
            if self.cash < 0 and self.cash > -1e-9:
                self.cash = 0.0
            self.trades.append({"ts": ts, "yon": "al", "adet": q, "fiyat": px, "komisyon": n * self.fee,
                                "hedef": tgt})
        elif delta < 0:
            q = min(-delta / o, self.qty)
            px = o * (1 - self.slip)
            gross = q * px
            f = gross * self.fee
            self.cash += gross - f
            self.qty -= q
            self.trades.append({"ts": ts, "yon": "sat", "adet": q, "fiyat": px, "komisyon": f, "hedef": tgt})
        self.max_trade_w = max(self.max_trade_w, self.mark_w(o))

    def on_day_close(self, c, sigma):
        if sigma is None or (isinstance(sigma, float) and math.isnan(sigma)):
            return                                    # σ yok: pozisyon açılmaz
        tgt = MAX_W if sigma <= 0 else min(MAX_W, VOL_TARGET / sigma)
        if abs(tgt - self.mark_w(c)) > BAND:
            self.pending = tgt

    def value(self, px):                              # ENS ile aynı: tasfiye değeri (research.exit_value)
        return self.cash + self.qty * px * (1 - self.slip) * (1 - self.fee)


# =================================================================== ortak simülasyon
def simulate(c4, fee, slip, t_end=None, start_idx=0):
    """ENS, VM-A ve VM-B aynı mum listesi, aynı başlangıç sermayesi (100) ve aynı maliyetle,
    tek döngüde. Günlük kayıt: günün son 4s mumunun kapanışı (v1 ile aynı)."""
    p = dict(V.ens_params(VOL_TARGET), fee=fee, slip=slip)
    ind = E.indicators(c4, p)
    closes = [c[4] for c in c4]
    sig = {k: signals.realized_vol(closes, n, 365 * 6) for k, n in VM_WIN.items()}
    ens = E.new_state(100.0, p)
    vms = {k: VM(fee, slip) for k in VM_WIN}
    names = ["ENS"] + list(VM_WIN)
    out = {"days": [], "close": [], "eq": {k: [] for k in names}, "w": {k: [] for k in names},
           "expo": {k: [] for k in names}, "perf_base": None, "first_ts": c4[start_idx][0]}
    for i in range(start_idx, len(c4)):
        t, o, _, _, cl = c4[i][:5]
        if t_end is not None and t >= t_end:
            break
        if t == PERF_START:                           # v2.1 §1: başlangıç, ilk temiz günün ilk 4s açılışında
            out["perf_base"] = {"ENS": research.exit_value(ens, o), **{k: v.value(o) for k, v in vms.items()},
                                "B100": o}
        for v in vms.values():
            v.on_open(t, o)
        E.process_bar(ens, c4, ind, i)
        if (t + BAR4) % DAY != 0:
            continue
        for k, v in vms.items():
            v.on_day_close(cl, sig[k][i])
        out["days"].append((t + BAR4) // DAY - 1)
        out["close"].append(cl)
        e = research.exit_value(ens, cl)
        out["eq"]["ENS"].append(e)
        out["w"]["ENS"].append(ens["qty"] * cl / e if e > 0 else 0.0)
        out["expo"]["ENS"].append(ens["qty"] > 0)
        for k, v in vms.items():
            val = v.value(cl)
            out["eq"][k].append(val)
            out["w"][k].append(v.qty * cl / val if val > 0 else 0.0)
            out["expo"][k].append(v.qty > 0)
    out["ens_trades"] = ens["trades"]
    out["ens_open"] = ens["qty"] > 0
    out["vm_trades"] = {k: v.trades for k, v in vms.items()}
    out["vm_cash_min"] = min(v.cash for v in vms.values())
    out["vm_max_trade_w"] = {k: v.max_trade_w for k, v in vms.items()}
    out["params"] = {"ENS": {"fee": p["fee"], "slip": p["slip"]},
                     **{k: {"fee": v.fee, "slip": v.slip} for k, v in vms.items()}}
    out["sigma_same"] = all(
        np.allclose(np.nan_to_num(np.array(ind[j]["rvol"], dtype=float), nan=-1.0),
                    np.nan_to_num(np.array(sig["VM-A"], dtype=float), nan=-1.0), rtol=0, atol=0)
        for j in range(len(ind)))
    return out


def day_series(run, key):
    if key == "B100":
        return dict(zip(run["days"], run["close"]))
    return dict(zip(run["days"], run["eq"][key]))


def _val_at(ser, days_sorted, d):
    """d günündeki değer; o gün kaydı yoksa d'den önceki son kayıt."""
    import bisect
    j = bisect.bisect_right(days_sorted, d) - 1
    return (days_sorted[j], ser[days_sorted[j]]) if j >= 0 else (None, None)


def window(run, key, a, b):
    ser = day_series(run, key)
    ds = sorted(ser)
    da, va = _val_at(ser, ds, a)
    if va is None or va <= 0:
        return None
    vals = [va] + [ser[d] for d in ds if a < d <= b]
    eq = np.array(vals) / va
    peak = np.maximum.accumulate(eq)
    return {"getiri": float(eq[-1] - 1), "mdd": float(np.max(1 - eq / peak)), "baz_gunu": dstr(da)}


def window_activity(run, key, a, b):
    idx = [i for i, d in enumerate(run["days"]) if a <= d <= b]
    if not idx:
        return {}
    w = [run["w"][key][i] for i in idx] if key != "B100" else [1.0] * len(idx)
    ex = [run["expo"][key][i] for i in idx] if key != "B100" else [True] * len(idx)
    lo, hi = a * DAY, (b + 1) * DAY
    if key == "ENS":
        n = sum(1 for t in run["ens_trades"] if lo <= t["entry_ts"] < hi)
    elif key == "B100":
        n = 0
    else:
        n = sum(1 for t in run["vm_trades"][key] if lo <= t["ts"] < hi)
    return {"islem": n, "piyasada_pct": round(100 * sum(ex) / len(ex), 1), "ort_agirlik": round(float(np.mean(w)), 3)}


def period_metrics(run, key, d0, d1):
    """d0 (dahil) .. d1 (hariç) ölçüm; baz = d0'dan önceki son günlük değer. CAGR = (son/ilk)^(365,25/gün) − 1."""
    ser = day_series(run, key)
    ds = sorted(ser)
    db, vb = _val_at(ser, ds, d0 - 1)
    pts = [(d, ser[d]) for d in ds if d0 <= d < d1]
    if vb is None or not pts:
        return None
    eq = np.array([vb] + [v for _, v in pts]) / vb
    days = pts[-1][0] - db
    peak = np.maximum.accumulate(eq)
    cagr = eq[-1] ** (365.25 / days) - 1 if days > 0 and eq[-1] > 0 else None
    return {"getiri": float(eq[-1] - 1), "cagr": float(cagr) if cagr is not None else None,
            "mdd": float(np.max(1 - eq / peak)), "gun": int(days)}


# =================================================================== doğrulama testleri
class Tests:
    def __init__(self):
        self.rows = []

    def add(self, name, ok, detail="", critical=True):
        self.rows.append({"test": name, "gecti": bool(ok) if ok is not None else None, "ayrinti": detail,
                          "kritik": critical})
        log(("GEÇTİ " if ok else ("ÇALIŞMADI " if ok is None else "KALDI ")) + name + (f" — {detail}" if detail else ""))

    @property
    def critical_ok(self):
        return all(r["gecti"] is True for r in self.rows if r["kritik"])


def git_show(rev_path):
    return subprocess.run(["git", "show", rev_path], capture_output=True, check=True).stdout


def test_engine_identity(T):
    diffs, err = [], None
    try:
        for f in ENGINE_FILES:
            old = git_show(f"{V1_COMMIT}:{f}")
            with open(f, "rb") as fh:
                if fh.read() != old:
                    diffs.append(f)
    except Exception as e:  # noqa: BLE001
        err = str(e)
    if err:
        T.add("Motor dosyaları v1 doğrulamasını üreten kodla aynı", None, f"git ile karşılaştırılamadı: {err}")
    else:
        T.add("Motor dosyaları v1 doğrulamasını üreten kodla aynı", not diffs,
              "farklı: " + ", ".join(diffs) if diffs else f"{len(ENGINE_FILES)} dosya birebir (v1 sonuç commit'i {V1_COMMIT[:7]})")


def test_cost_formula(T):
    fee, slip, o = 0.001, 0.0005, 50_000.0
    v = VM(fee, slip)
    v.pending = 0.5
    v.on_open(0, o)
    n = 50.0 / (1 + fee)
    ok_buy = math.isclose(v.qty, n / (o * (1 + slip)), rel_tol=1e-15) and math.isclose(v.cash, 50.0, rel_tol=1e-15)
    q = v.qty
    v.pending = 0.0
    v.on_open(1, o)
    gross = q * o * (1 - slip)
    ok_sell = math.isclose(v.cash, 50.0 + gross - gross * fee, rel_tol=1e-15) and v.qty == 0.0
    # motorun kendi formülüyle karşılaştırma (strategy._open_position / _close_position)
    p = dict(S.DEFAULT_PARAMS, fee=fee, slip=slip, vol_target=0.5, max_alloc=0.99, stop_atr=6.0)
    st = S.new_state(100.0, p)
    S._open_position(st, 0, o, atr_val=1000.0, rvol=1.0)        # hedef tutar = 100 × 0,5 / 1 = 50
    ok_engine = math.isclose(st["qty"], n / (o * (1 + slip)), rel_tol=1e-12)
    T.add("Maliyet formülü motorla aynı (alış ve satış)", ok_buy and ok_sell and ok_engine,
          f"alış {ok_buy}, satış {ok_sell}, motor eşleşmesi {ok_engine}")


def test_constant_price(T):
    c4 = [(i * BAR4, 100.0, 100.0, 100.0, 100.0, 1.0) for i in range(6 * 200)]
    v = VM(0.0, 0.0)
    v2 = VM(0.001, 0.0005)
    for i, c in enumerate(c4):
        for x in (v, v2):
            x.on_open(c[0], c[1])
        if (c[0] + BAR4) % DAY == 0:
            for x in (v, v2):
                x.on_day_close(c[4], 0.0)
    ok = math.isclose(v.value(100.0), 100.0, rel_tol=1e-12) and v2.value(100.0) < 100.0 and len(v.trades) == 1
    T.add("Sabit fiyatta maliyetsiz VM değer kaybetmez, maliyetli VM yalnızca maliyet kadar kaybeder", ok,
          f"maliyetsiz {v.value(100.0):.6f}, maliyetli {v2.value(100.0):.6f}, işlem {len(v.trades)}")


def test_clean_start(T):
    opens = [V.ts("2026-11-05") + k * BAR4 for k in range(12)]
    straddle = V.ts("2026-11-05") + 12 * H
    clean = [t for t in opens if t >= T_KAYIT]
    ok = (straddle not in clean and clean[0] == V.ts("2026-11-05") + 16 * H
          and PERF_START == V.ts("2026-11-06") and PERF_START >= T_KAYIT and PERF_START - DAY < T_KAYIT)
    T.add("Temiz başlangıç: kayıt saatini kesen mum dışarıda, performans 2026-11-06 00:00 UTC", ok,
          f"T_kayıt {iso(T_KAYIT)}, ilk temiz 4s mum {iso(clean[0])}, performans başlangıcı {iso(PERF_START)}")


def compare_trades(a, b):
    if len(a) != len(b):
        return False, f"işlem sayısı {len(a)} ≠ {len(b)}"
    keys = ["entry_ts", "exit_ts", "entry_px", "exit_px", "qty", "pnl", "reason"]
    for i, (x, y) in enumerate(zip(a, b)):
        for k in keys:
            if x.get(k) != y.get(k):
                return False, f"{i}. işlemde {k}: {x.get(k)} ≠ {y.get(k)}"
    return True, f"{len(a)} işlem; giriş/çıkış zamanı, fiyat, adet, kâr ve çıkış sebebi birebir"


def v1_reproduction(T, c1_all, ref):
    """v1 doğrulamasını aynı veri ve değişmemiş v1 koduyla yeniden üretir; kayıtlı özetlerle ve
    v2 sarmalayıcısının işlem/özsermaye kayıtlarıyla karşılaştırır."""
    out = {}
    c1 = [x for x in c1_all if x[0] < V.MAIN_END]
    st = data_stats(c1)
    c4 = D.aggregate(c1, 4)
    st["mum_4s"] = len(c4)
    rv = ref.get("veri", {})
    keys = ["mum_1s", "bosluk_sayisi", "eksik_1s_mum", "ilk", "son", "mum_4s"]
    T.add("v1 veri özeti aynı (mum sayısı, boşluk, eksik, ilk/son)", all(st[k] == rv.get(k) for k in keys),
          ", ".join(f"{k} {st[k]}/{rv.get(k)}" for k in keys))
    daily_all = V.daily_closes(c4, c4[0][0] + 400 * DAY, V.MAIN_END)
    c4_main = [c for c in c4 if V.SIM_START - V.WARMUP_BARS * BAR4 <= c[0] < V.MAIN_END]
    run = V.run_ens(c4_main, V.ens_params(0.4), V.MAIN_START, V.MAIN_END)
    m = V.eq_metrics(run["eq"])
    m.update({"islem": len(run["trades"]), "piyasada_pct": round(100 * float(np.mean(run["expo"])), 1),
              "ort_btc_agirligi": round(float(np.mean(run["w"])), 3)})
    r = ref["ana_donem"]["tablo"]["ENS (vt %40)"]
    ks = ["getiri_pct", "cagr_pct", "max_dusus_pct", "calmar", "sharpe", "sortino", "islem", "piyasada_pct",
          "ort_btc_agirligi"]
    T.add("v1 ana dönem ENS özetleri aynı", all(m[k] == r[k] for k in ks),
          ", ".join(f"{k} {m[k]}/{r[k]}" for k in ks))
    out["ana"] = m
    p2 = dict(V.ens_params(0.4), fee=0.002, slip=0.001)
    m2 = V.eq_metrics(V.run_ens(c4_main, p2, V.MAIN_START, V.MAIN_END)["eq"])
    k2 = ["getiri_pct", "max_dusus_pct", "sharpe"]
    T.add("v1 2× maliyet özetleri aynı", all(m2[k] == ref["maliyet_2x"][k] for k in k2),
          ", ".join(f"{k} {m2[k]}/{ref['maliyet_2x'][k]}" for k in k2))
    bm, _, _ = V.benchmarks_for(run, None, daily_all)
    ok_b = True
    det = []
    for name in ("B100", "VM"):
        mb = V.eq_metrics(bm[name])
        rb = ref["ana_donem"]["tablo"][name]
        for k in ("getiri_pct", "max_dusus_pct", "sharpe"):
            ok_b &= mb[k] == rb[k]
            det.append(f"{name} {k} {mb[k]}/{rb[k]}")
    T.add("v1 B100 ve VM özetleri aynı", ok_b, ", ".join(det))
    c4_s = [c for c in c4 if c[0] < V.STRESS_END]
    rs = V.run_ens(c4_s, V.ens_params(0.4), V.STRESS_START, V.STRESS_END)
    eqs = np.array(rs["eq"])
    ms = V.eq_metrics(rs["eq"])
    ms.update({"islem": len(rs["trades"]), "en_dusuk_ozsermaye_pct": round(float(eqs.min() / eqs[0] * 100), 2),
               "ort_btc_agirligi": round(float(np.mean(rs["w"])), 3)})
    rsr = ref["stres_2018_2022"]["ENS"]
    k3 = ["getiri_pct", "max_dusus_pct", "sharpe", "islem", "en_dusuk_ozsermaye_pct", "ort_btc_agirligi"]
    T.add("v1 2018–2022 stres testi özetleri aynı", all(ms[k] == rsr[k] for k in k3),
          ", ".join(f"{k} {ms[k]}/{rsr[k]}" for k in k3))
    # v2 sarmalayıcısı ↔ v1 kodu: işlem listesi ve günlük özsermaye birebir (v1 penceresi)
    mine = simulate(c4_main, 0.001, 0.0005, t_end=V.MAIN_END)
    ok_t, det_t = compare_trades(mine["ens_trades"], run["all_trades"])
    T.add("v2 sarmalayıcısı ↔ v1 kodu: işlem sayısı, zamanları ve büyüklükleri aynı (v1 penceresi)", ok_t, det_t)
    my_eq = [e for d, e in zip(mine["days"], mine["eq"]["ENS"]) if d * DAY >= V.MAIN_START]
    my_w = [w for d, w in zip(mine["days"], mine["w"]["ENS"]) if d * DAY >= V.MAIN_START]
    ok_e = my_eq == run["eq"][1:] and my_w == run["w"]
    T.add("v2 sarmalayıcısı ↔ v1 kodu: günlük portföy değeri ve pozisyon ağırlığı aynı (v1 penceresi)", ok_e,
          f"{len(my_eq)} gün karşılaştırıldı")
    out["c4_main"] = c4_main
    out["v1_run"] = run
    out["daily_all"] = daily_all
    out["v1_vm_returns"] = [bm["VM"][i + 1] / bm["VM"][i] - 1 for i in range(len(bm["VM"]) - 1)]
    return out


def truncation_test(T, c4, full):
    rng = random.Random(SEED)
    lo = 900
    cuts = sorted(rng.sample(range(lo, len(c4) - 10), 4))
    bad = []
    for cut in cuts:
        part = simulate(c4[:cut], 0.001, 0.0005)
        n = len(part["days"])
        same = (part["days"] == full["days"][:n]
                and all(part["eq"][k] == full["eq"][k][:n] for k in part["eq"])
                and all(part["w"][k] == full["w"][k][:n] for k in part["w"]))
        tcut = c4[cut][0]
        ens_full = [t for t in full["ens_trades"] if t["exit_ts"] < tcut]
        ens_part = [t for t in part["ens_trades"] if t["exit_ts"] < tcut]
        same &= compare_trades(ens_part, ens_full)[0]
        for k in VM_WIN:
            same &= [t for t in part["vm_trades"][k] if t["ts"] < tcut] == \
                    [t for t in full["vm_trades"][k] if t["ts"] < tcut]
        if not same:
            bad.append(iso(tcut))
    T.add("Geleceği görme testi: veri 4 rastgele noktada kesildiğinde önceki kararlar değişmiyor", not bad,
          "kesim: " + ", ".join(iso(c4[c][0]) for c in cuts) + (f"; FARKLI: {bad}" if bad else ""))


# =================================================================== geçmiş (keşifsel) değerlendirme
STRATS = ["ENS", "VM-A", "VM-B", "B100"]


def episode_table(run, e):
    a, b, c = e["t0"], e["t1"], e["t2"]
    rows = {}
    for k in STRATS:
        bear = window(run, k, a, b)
        rec = window(run, k, b, c) if c is not None else None
        full = window(run, k, a, c) if c is not None else None
        rows[k] = {"ayi_mdd": bear and bear["mdd"], "ayi_getiri": bear and bear["getiri"],
                   "toparlanma_getiri": rec and rec["getiri"], "tam_getiri": full and full["getiri"],
                   "tam_mdd": full and full["mdd"], **window_activity(run, k, a, c if c is not None else b)}
    if rows["ENS"]["toparlanma_getiri"] is not None:
        ra, re_ = rows["VM-A"]["toparlanma_getiri"], rows["ENS"]["toparlanma_getiri"]
        rb = rows["B100"]["toparlanma_getiri"]
        rows["kacirilan"] = {"vs_VM-A_puan": ra - re_, "katilim_vs_VM-A": (1 + re_) / (1 + ra),
                             "vs_B100_puan": rb - re_, "katilim_vs_B100": (1 + re_) / (1 + rb)}
    m_vm, m_en = rows["VM-A"]["ayi_mdd"], rows["ENS"]["ayi_mdd"]
    diff = m_vm - m_en
    rel = diff / m_vm if m_vm > 0 else None
    rows["koruma"] = {"fark_puan": diff, "goreli": rel,
                      "a": diff >= THR_PP, "b": rel is not None and rel >= THR_REL,
                      "gecti": diff >= THR_PP and rel is not None and rel >= THR_REL}
    return rows


def evaluate(runs, eps):
    n = len(eps)
    need = math.ceil(2 * n / 3) if n else 0
    res = {"n": n, "gereken": need, "maliyet": {}}
    passes_both = 0
    per_ep = []
    for e in eps:
        r = {lvl: episode_table(runs[lvl], e) for lvl in COSTS}
        both = all(r[lvl]["koruma"]["gecti"] for lvl in COSTS)
        passes_both += both
        per_ep.append({"t0": dstr(e["t0"]), "t1": dstr(e["t1"]), "t2": dstr(e["t2"]), "derinlik": e["depth"],
                       "olcum": r, "iki_maliyette_gecti": both})
    for lvl in COSTS:
        pm = {k: period_metrics(runs[lvl], k, HIST_START // DAY, HIST_END // DAY) for k in STRATS}
        gap = pm["VM-A"]["cagr"] - pm["ENS"]["cagr"]
        res["maliyet"][lvl] = {"tum_donem": pm, "cagr_farki_VM-A_eksi_ENS": gap, "cagr_sarti": gap <= THR_CAGR}
    s1 = n >= 3
    s2 = passes_both >= need and n > 0
    s3 = all(res["maliyet"][lvl]["cagr_sarti"] for lvl in COSTS)
    res.update({"donemler": per_ep, "koruma_gecen_iki_maliyette": passes_both,
                "sartlar": {"1_n_en_az_3": s1, "2_koruma_en_az_2_3": s2, "3_cagr_farki_en_fazla_2_puan": s3,
                            "4_iki_maliyette": s2 and s3}})
    if not s1:
        res["sonuc"] = ("Yetersiz kanıt (tamamlanmış büyük ayı dönemi < 3). Geçici varsayılan: VM-A.")
    elif s1 and s2 and s3:
        res["sonuc"] = ("Bütün şartlar sağlandı: ENS ayı piyasası koruma alternatifi olarak GEÇİCİ tercih edilir "
                        "(keşifsel; nihai karar değil).")
    else:
        res["sonuc"] = "Şartlardan en az biri sağlanmadı. Geçici varsayılan: VM-A."
    return res


# =================================================================== DSR (bilgi amaçlı; v1 yöntemi sabit)
def dsr_block(v1o, c1_all, long_run):
    data = {"1h": [c for c in c1_all if V.SIM_START - 30 * DAY <= c[0] < V.MAIN_END], "4h": v1o["c4_main"]}
    d15 = D.history_symbol("BTC", V.months_between(V.SIM_START - 30 * DAY, 0), "15m")
    d15 = [c for c in d15 if V.SIM_START - 30 * DAY <= c[0] < V.MAIN_END]
    ser = V.all_trial_returns(data, d15)
    n_v1 = len(ser)
    T0 = min(len(v) for v in ser.values())
    ne_v1 = V.n_eff_estimates({k: v[:T0] for k, v in ser.items()})

    def rets(key):
        ser_d = day_series(long_run, key)
        ds = sorted(ser_d)
        base = _val_at(ser_d, ds, V.MAIN_START // DAY - 1)[1]
        vals = [base] + [ser_d[d] for d in ds if V.MAIN_START // DAY <= d < V.MAIN_END // DAY]
        return [vals[i + 1] / vals[i] - 1 for i in range(len(vals) - 1)]

    r_ens, r_vma, r_vmb = rets("ENS"), rets("VM-A"), rets("VM-B")
    ser["v2|VM-A"], ser["v2|VM-B"], ser["v2|VM-ref"] = r_vma, r_vmb, v1o["v1_vm_returns"]
    T_ = min(len(v) for v in ser.values())
    ser = {k: v[:T_] for k, v in ser.items()}
    ne = V.n_eff_estimates(ser)
    Ns = {f"N_toplam={N_TOTAL}": N_TOTAL, "N_eff_katilim": ne["N_eff_katilim_orani"],
          "N_eff_ort_korelasyon": ne["N_eff_ort_korelasyon"], "N_eff_kume": ne["N_eff_kume"]}
    return {"yontem": "v1 ile aynı: Bailey & López de Prado (2014) DSR (bot/overfit.deflated_sharpe); günlük getiriler, "
                      "ölçüm 2023-11-01 → 2026-10-31; deneme Sharpe dağılımı = v1'in 249 serisi + VM-A, VM-B, VM-ref; "
                      "N_eff = v1'in üç yöntemi, VM serileri eklenmiş korelasyon matrisinden.",
            "v1_seri_sayisi": n_v1, "v1_etkin_boyut_yeniden": ne_v1, "seri_sayisi": len(ser), "gun": T_, "etkin_boyut": ne,
            "ENS": V.dsr_table(r_ens[:T_], ser, Ns), "VM-A": V.dsr_table(r_vma[:T_], ser, Ns)}


# =================================================================== ileri (temiz) gözlem
def forward_block(run_flat_by_lvl, runs, spells_all, last_day):
    out = {"performans_baslangici": iso(PERF_START), "son_tam_gun": dstr(last_day) if last_day else None}
    first_day = PERF_START // DAY
    if last_day is None or last_day < first_day or runs["1x"]["perf_base"] is None:
        out["durum"] = "Henüz temiz veri yok (ilk temiz gün tamamlanmadı)."
        return out
    for lvl in COSTS:
        run = runs[lvl]
        base = run["perf_base"]
        tab = {}
        for k in STRATS:
            ser = day_series(run, k)
            pts = [(d, ser[d]) for d in sorted(ser) if first_day <= d <= last_day]
            assert all(d * DAY >= PERF_START >= T_KAYIT for d, _ in pts), "temiz dönem ihlali"
            if not pts:
                continue
            eq = np.array([base[k]] + [v for _, v in pts]) / base[k]
            peak = np.maximum.accumulate(eq)
            gun = pts[-1][0] - first_day + 1
            tab[k] = {"getiri": float(eq[-1] - 1), "mdd": float(np.max(1 - eq / peak)), "gun": gun,
                      "cagr": float(eq[-1] ** (365.25 / gun) - 1) if gun >= 365 else None}
        out[lvl] = {"devreden_durum": tab}
        rf = run_flat_by_lvl.get(lvl)
        if rf and rf["perf_base"]:
            tf = {}
            for k in STRATS:
                ser = day_series(rf, k)
                pts = [v for d, v in sorted(ser.items()) if first_day <= d <= last_day]
                if pts:
                    eq = np.array([rf["perf_base"][k]] + pts) / rf["perf_base"][k]
                    tf[k] = {"getiri": float(eq[-1] - 1), "mdd": float(np.max(1 - eq / np.maximum.accumulate(eq)))}
            out[lvl]["nakitten_baslangic_bilgi"] = tf
    fwd = [s for s in spells_all if s["t0"] >= first_day and s["big"]]
    out["ileri_buyuk_donem"] = [{"t0": dstr(s["t0"]), "t1": dstr(s["t1"]), "t2": dstr(s["t2"]) if s["t2"] else None,
                                 "derinlik": s["depth"], "tamamlandi": s["complete"]} for s in fwd]
    done = [s for s in fwd if s["complete"]]
    out["tamamlanmis_ileri_donem"] = len(done)
    if len(done) >= 3:
        out["ileri_karar"] = evaluate(runs, done)
    out["durum"] = (f"{len(done)} tamamlanmış ileri büyük ayı dönemi. "
                    + ("Nihai karar hesaplandı (v2.1 §4)." if len(done) >= 3 else
                       "3'e ulaşmadan bütün sonuçlar yalnızca gözlemdir; nihai kararı ve geçici varsayılanı değiştirmez."))
    kday = T_KAYIT // DAY
    ongoing = [s for s in spells_all if s["t0"] < first_day and (s["t2"] is None or s["t2"] >= kday)
               and s["t0"] <= kday]
    if ongoing:
        s = ongoing[-1]
        out["kayit_aninda_suren_donem"] = {"t0": dstr(s["t0"]), "su_ana_kadar_dip": dstr(s["t1"]),
                                           "derinlik": s["depth"], "t2": dstr(s["t2"]) if s["t2"] else None,
                                           "not": "Kayıt anında sürüyordu; −%40'ı geçse bile ileri karara girmez."}
    return out


# =================================================================== rapor
def pct(x, nd=1):
    if x is None:
        return "—"
    return f"-%{abs(x) * 100:.{nd}f}" if x < 0 else f"%{x * 100:.{nd}f}"


def pp(x):
    return "—" if x is None else f"{x * 100:+.1f} puan"


def yesno(b):
    return "✅ geçti" if b is True else ("⚪ çalışmadı" if b is None else "❌ kaldı")


def markdown(res):
    L = ["# Ön Kayıt v2 / v2.1 — Sonuç", "",
         "> **Bu bir istatistiksel üstünlük kanıtı değil, önceden belirlenmiş operasyonel tercih kuralının sonucudur. "
         "Geçmiş veri sonucu keşifseldir.**",
         "> Bu çalıştırmanın sonucu **nihai karar değildir**. Nihai karar yalnızca temiz (ileri) veride 3 tamamlanmış "
         "büyük ayı dönemi oluştuğunda verilir (v2.1 §4). Gerçek paraya geçiş v1 §11 ve güvenlik kapılarına bağlıdır.", ""]
    i = res["calistirma"]
    L += ["## Çalıştırma bilgisi", "",
          f"- Zaman: {i['zaman']} · çalıştırma: {i['calistirma_id']} · commit: `{i['commit']}`",
          f"- Python {i['python']} · numpy {i['numpy']} · {i['platform']}",
          f"- Belgeler: " + ", ".join(f"`{k}` {v[:12]}…" for k, v in i["belge_ozetleri"].items()),
          f"- Veri: Binance spot BTCUSDT 1s, {res['veri']['mum_1s']} mum ({res['veri']['ilk']} → {res['veri']['son']}), "
          f"{res['veri']['dosya_sayisi']} arşiv dosyası, CHECKSUM doğrulanan {res['veri']['checksum_ok']}, "
          f"veri özeti `{res['veri']['veri_sha256'][:16]}…`", ""]
    t = res["testler"]
    n_ok = sum(1 for r in t if r["gecti"] is True)
    L += ["## 1. Doğrulama testleri", "", f"**{n_ok}/{len(t)} test geçti.** "
          + ("Bütün kritik testler geçti." if res["kritik_testler_gecti"] else
             "**Kritik testlerden en az biri geçmedi: geçmiş ve ileri sonuçlar yayınlanmadı.**"), "",
          "| # | Test | Sonuç | Ayrıntı |", "|---|---|---|---|"]
    for k, r in enumerate(t, 1):
        L.append(f"| {k} | {r['test']}{'' if r['kritik'] else ' (bilgi)'} | {yesno(r['gecti'])} | {r['ayrinti']} |")
    L.append("")
    if not res["kritik_testler_gecti"]:
        L += ["Farklar açıklanmadan sonuçlar yorumlanmayacak.", ""]
        return "\n".join(L)

    g = res["gecmis"]
    L += ["## 2. Geçmiş veri: keşifsel, geçici varsayılan", "",
          f"Ölçüm: {V.fmt(HIST_START)} → {V.fmt(HIST_END - DAY)}. Ayı dönemi tanımı v2 §4 / v2.1 §2.", "",
          "### 2.1 Su altı dönemleri (zirveden en az %20 düşüş olanlar; tamamı JSON'da)", "",
          "| Zirve (t0) | Dip (t1) | Toparlanma (t2) | Derinlik | Büyük (≤ −%40) | Tamamlandı | Sayıldı |",
          "|---|---|---|---|---|---|---|"]
    for s in g["su_alti"]:
        if s["derinlik"] <= -0.20:
            L.append(f"| {s['t0']} | {s['t1']} | {s['t2'] or '—'} | {pct(s['derinlik'])} | "
                     f"{'evet' if s['buyuk'] else 'hayır'} | {'evet' if s['tamamlandi'] else 'hayır'} | "
                     f"{'evet' if s['sayildi'] else 'hayır'} |")
    L += ["", f"Toplam su altı dönemi: {g['su_alti_sayisi']}; sayılan tamamlanmış büyük ayı dönemi: **{g['karar']['n']}**.", ""]
    for e in g["karar"]["donemler"]:
        L += [f"### Dönem {e['t0']} → dip {e['t1']} → toparlanma {e['t2']} (BTC {pct(e['derinlik'])})", "",
              "| Maliyet | Strateji | Ayı MDD | Ayı getirisi | Toparlanma getirisi | Tam döngü getirisi | Tam döngü MDD | İşlem | Piyasada | Ort. ağırlık |",
              "|---|---|---|---|---|---|---|---|---|---|"]
        for lvl in COSTS:
            o = e["olcum"][lvl]
            for k in STRATS:
                r = o[k]
                L.append(f"| {lvl} | {k} | {pct(r['ayi_mdd'])} | {pct(r['ayi_getiri'])} | {pct(r['toparlanma_getiri'])} | "
                         f"{pct(r['tam_getiri'])} | {pct(r['tam_mdd'])} | {r.get('islem', '—')} | "
                         f"%{r.get('piyasada_pct', '—')} | {r.get('ort_agirlik', '—')} |")
        L += ["", "| Maliyet | ENS'nin VM-A'ya göre ayı MDD avantajı | Göreli | ≥10 puan | ≥%25 | Koruma şartı | Kaçırılan toparlanma (VM-A − ENS) | Katılım oranı |",
              "|---|---|---|---|---|---|---|---|"]
        for lvl in COSTS:
            kq, kc = e["olcum"][lvl]["koruma"], e["olcum"][lvl].get("kacirilan", {})
            L.append(f"| {lvl} | {pp(kq['fark_puan'])} | {pct(kq['goreli'])} | {yesno(kq['a'])} | {yesno(kq['b'])} | "
                     f"{yesno(kq['gecti'])} | {pp(kc.get('vs_VM-A_puan'))} | "
                     f"{('%.3f' % kc['katilim_vs_VM-A']) if kc else '—'} |")
        L.append("")
    L += ["### 2.2 Tüm ölçüm dönemi", "", "| Maliyet | Strateji | Toplam getiri | CAGR | MDD |", "|---|---|---|---|---|"]
    for lvl in COSTS:
        for k in STRATS:
            m = g["karar"]["maliyet"][lvl]["tum_donem"][k]
            L.append(f"| {lvl} | {k} | {pct(m['getiri'])} | {pct(m['cagr'], 2)} | {pct(m['mdd'])} |")
    L += ["", "### 2.3 Karar şartları (v2 §6)", "", "| # | Şart | Sonuç |", "|---|---|---|"]
    k = g["karar"]
    cg = {lvl: k["maliyet"][lvl]["cagr_farki_VM-A_eksi_ENS"] for lvl in COSTS}
    L += [f"| 1 | Tamamlanmış büyük ayı dönemi ≥ 3 (n = {k['n']}) | {yesno(k['sartlar']['1_n_en_az_3'])} |",
          f"| 2 | Koruma şartını iki maliyette de geçen dönem ≥ {k['gereken']} (geçen: {k['koruma_gecen_iki_maliyette']}) | "
          f"{yesno(k['sartlar']['2_koruma_en_az_2_3'])} |",
          f"| 3 | CAGR(VM-A) − CAGR(ENS) ≤ 2 puan (1×: {pp(cg['1x'])}, 2×: {pp(cg['2x'])}) | "
          f"{yesno(k['sartlar']['3_cagr_farki_en_fazla_2_puan'])} |",
          f"| 4 | 1–3 her iki maliyette | {yesno(k['sartlar']['4_iki_maliyette'] and k['sartlar']['1_n_en_az_3'])} |", "",
          f"**Geçmiş veri sonucu (keşifsel, geçici):** {k['sonuc']}", ""]
    d = res.get("dsr", {})
    L += ["### 2.4 DSR (bilgi amaçlı, karara girmez)", ""]
    if "hata" in d:
        L += [f"Hesaplanamadı: {d['hata']}", ""]
    else:
        L += [d["yontem"], "", f"Etkin boyut: {d['etkin_boyut']}", "", "| Deneme sayısı | ENS DSR | VM-A DSR |", "|---|---|---|"]
        for n_ in d["ENS"]:
            a, b = d["ENS"][n_], d["VM-A"][n_]
            L.append(f"| {n_} | {a['dsr'] if a else '—'} | {b['dsr'] if b else '—'} |")
        L.append("")
    f = res["ileri"]
    L += ["## 3. İleri (temiz) veri: yalnızca gözlem", "", f"Performans başlangıcı: {f['performans_baslangici']}. "
          f"Son tam gün: {f.get('son_tam_gun') or '—'}.", "", f"**Durum:** {f['durum']}", ""]
    for lvl in COSTS:
        if lvl in f:
            L += [f"| {lvl} | Strateji | Getiri | MDD | Gün | CAGR |", "|---|---|---|---|---|---|"]
            for kk, m in f[lvl]["devreden_durum"].items():
                L.append(f"| {lvl} | {kk} | {pct(m['getiri'], 2)} | {pct(m['mdd'], 2)} | {m['gun']} | "
                         f"{pct(m['cagr'], 2) if m['cagr'] is not None else '1 yıldan kısa'} |")
            L.append("")
    if f.get("kayit_aninda_suren_donem"):
        s = f["kayit_aninda_suren_donem"]
        L += [f"Kayıt anında süren düşüş dönemi: zirve {s['t0']}, şu ana kadarki dip {s['su_ana_kadar_dip']} "
              f"({pct(s['derinlik'])}). {s['not']}", ""]
    L += ["## 4. Notlar", ""] + [f"- {x}" for x in res["notlar"]]
    return "\n".join(L)


# =================================================================== ana akış
def main():
    t_all = time.time()
    now = datetime.now(UTC)
    now_ms = int(now.timestamp() * 1000)
    run_id = f"{os.environ.get('GITHUB_RUN_ID', 'yerel')}-{os.environ.get('GITHUB_RUN_ATTEMPT', '1')}"
    stamp = now.strftime("%Y%m%dT%H%M%SZ")
    out_dir = os.path.join("results", "v2", f"{stamp}_{run_id}")
    if os.path.exists(out_dir):
        raise SystemExit(f"{out_dir} zaten var; önceki sonuçların üzerine yazılmaz.")
    commit = os.environ.get("GITHUB_SHA") or subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                                                            text=True).stdout.strip()
    res = {"calistirma": {"zaman": now.isoformat(timespec="seconds"), "calistirma_id": run_id, "commit": commit,
                          "python": sys.version.split()[0], "numpy": np.__version__,
                          "platform": platform.platform(), "belge_ozetleri": {}},
           "notlar": []}
    T = Tests()

    # --- belgeler
    ok_docs = True
    for pth, exp in DOCS.items():
        got = sha256_file(pth)
        res["calistirma"]["belge_ozetleri"][pth] = got
        ok_docs &= got == exp
    T.add("Ön kayıt belgeleri değişmemiş (SHA-256)", ok_docs, "v2 ve v2.1 özetleri kayıtlı değerlerle karşılaştırıldı")
    test_engine_identity(T)

    # --- veri
    log("Veri indiriliyor…")
    c1, files, problems, notes = load_1h(now_ms)
    st = data_stats(c1)
    ck_ok = sum(1 for f in files if f["checksum_ok"] is True)
    ck_bad = [f["dosya"] for f in files if f["checksum_ok"] is False]
    ck_na = [f["dosya"] for f in files if f["checksum_ok"] is None]
    res["veri"] = {**st, "dosya_sayisi": len(files), "checksum_ok": ck_ok, "checksum_uyusmayan": ck_bad,
                   "checksum_alinamayan": ck_na, "sorunlar": problems, "notlar": notes,
                   "veri_sha256": dataset_hash(c1), "dosyalar": files}
    T.add("Arşiv dosyaları eksiksiz ve CHECKSUM uyuşmazlığı yok", not problems and not ck_bad,
          f"{len(files)} dosya, CHECKSUM doğrulanan {ck_ok}, uyuşmayan {len(ck_bad)}, alınamayan {len(ck_na)}"
          + (f"; sorun: {problems[:3]}" if problems else ""))
    res["notlar"] += notes

    # --- birim testleri
    for name, ok in test_spells():
        T.add(f"Ayı dönemi birim testi: {name}", ok)
    test_cost_formula(T)
    test_constant_price(T)
    test_clean_start(T)

    # --- v1 yeniden üretimi
    with open(V1_REF_FILE, encoding="utf-8") as fh:
        ref = json.load(fh)
    if not external.FG:                            # v1 ile aynı: korku-açgözlülük verisi (filtreli denemeler için)
        try:
            external.load_fear_greed(0)
        except Exception as e:  # noqa: BLE001
            res["notlar"].append(f"Korku-açgözlülük verisi alınamadı: {e}")
    try:
        v1o = v1_reproduction(T, c1, ref)
    except Exception as e:  # noqa: BLE001
        T.add("v1 yeniden üretimi", None, f"hata: {e}")
        v1o = None

    # --- uzun simülasyon (tek ve kesintisiz)
    c4 = D.aggregate(c1, 4)
    runs = {lvl: simulate(c4, fee, slip) for lvl, (fee, slip) in COSTS.items()}
    r1 = runs["1x"]
    same_universe = (r1["first_ts"] == c4[0][0]
                     and all(r1["params"][k] == r1["params"]["ENS"] for k in r1["params"])
                     and runs["2x"]["params"]["ENS"] == {"fee": 0.002, "slip": 0.001}
                     and all(runs["2x"]["params"][k] == runs["2x"]["params"]["ENS"] for k in runs["2x"]["params"]))
    T.add("Aynı evren, sermaye, başlangıç ve maliyet (ENS ve VM-A)", same_universe,
          f"evren BTCUSDT 4s (aynı {len(c4)} mum), başlangıç sermayesi 100/100, ikisi de nakitte başlar "
          f"({iso(c4[0][0])}), nakit getirisi %0, maliyet 1× {r1['params']['ENS']} / 2× {runs['2x']['params']['ENS']}; "
          "ENS sermayeyi kendi içinde 3 alt sisteme böler (toplam sermaye aynı)")
    T.add("Oynaklık tahmincisi ENS ile aynı (540 adet 4s basit getiri, bölen n, ×√2190)", r1["sigma_same"],
          "VM-A σ dizisi ENS'nin rvol dizisiyle birebir")
    w_ok = all(v <= MAX_W + 1e-12 for v in r1["vm_max_trade_w"].values()) and r1["vm_cash_min"] >= -1e-9
    T.add("VM tutarlılığı: nakit ≥ 0, işlem anındaki ağırlık ≤ %99", w_ok,
          f"en düşük nakit {r1['vm_cash_min']:.6f}, işlem anı en yüksek ağırlık "
          + ", ".join(f"{k} {v:.4f}" for k, v in r1["vm_max_trade_w"].items()))
    try:
        cmp_run = V.run_ens(c4, V.ens_params(0.4), HIST_START, HIST_END)
        mine = [e for d, e in zip(r1["days"], r1["eq"]["ENS"]) if HIST_START <= d * DAY < HIST_END]
        ok_l, det_l = compare_trades([t for t in r1["ens_trades"] if t["exit_ts"] < HIST_END], cmp_run["all_trades"])
        T.add("Uzun dönem: v2 sarmalayıcısı ↔ v1 kodu, işlemler ve günlük portföy değeri aynı",
              ok_l and mine == cmp_run["eq"][1:], det_l + f"; {len(mine)} gün")
    except Exception as e:  # noqa: BLE001
        T.add("Uzun dönem: v2 sarmalayıcısı ↔ v1 kodu", None, f"hata: {e}")
    truncation_test(T, c4, r1)

    res["testler"] = T.rows
    res["kritik_testler_gecti"] = T.critical_ok
    res["notlar"] += [
        "‘Ağırlık ≤ %99’ işlem anındaki hedeftir. Fiyat yükselince her iki stratejide de gerçek ağırlık %99'un "
        "biraz üstüne kayabilir (ENS'de pozisyon adedi sabit, VM'de 0,05 bant). Bu, v2.1 §3'ün yorumudur, kural değişikliği değildir.",
        "Pencere başında veya sonunda strateji günlük kaydı yoksa (eksik 4s mum) önceki son kayıt kullanılır.",
        "VM-ref ve B100 v1 tanımıyla yalnızca bilgi amaçlıdır; karar ENS ile VM-A arasındadır.",
        "MDD karşılaştırmaları float64 ile, eşiklerde kesin ≥ / ≤ ile yapılır; sınırdaki değer şartı sağlamamış sayılır.",
        "v1 doğrulaması işlem listesi saklamadığı için işlem düzeyindeki karşılaştırma, v1 commit'iyle birebir aynı "
        "olduğu doğrulanan v1 koduyla yapıldı. Bu çalıştırma tam işlem listelerini ve günlük değerleri saklar; sonraki "
        "çalıştırmalar bununla işlem işlem karşılaştırılabilir.",
    ]

    if T.critical_ok:
        last_day = max(daily_close(c1)) if c1 else None
        dc = daily_close(c1)
        spells = find_spells(dc, max(dc))
        hist_spells = find_spells(dc, HIST_END // DAY - 1)
        counted = [s for s in hist_spells if s["big"] and s["complete"] and s["t0"] >= HIST_START // DAY]
        missing_days = [dstr(d) for d in range(min(dc), max(dc) + 1) if d not in dc]
        res["gecmis"] = {
            "su_alti_sayisi": len(hist_spells),
            "su_alti": [{"t0": dstr(s["t0"]), "t1": dstr(s["t1"]), "t2": dstr(s["t2"]) if s["t2"] else None,
                         "zirve": str(s["P"]), "dip": str(s["C1"]), "derinlik": s["depth"], "buyuk": s["big"],
                         "tamamlandi": s["complete"], "sayildi": s in counted} for s in hist_spells],
            "kapanisi_olmayan_gunler": missing_days,
            "karar": evaluate(runs, counted)}
        try:
            res["dsr"] = dsr_block(v1o, c1, r1) if v1o else {"hata": "v1 yeniden üretimi yok"}
        except Exception as e:  # noqa: BLE001
            res["dsr"] = {"hata": str(e)}
        if "v1_etkin_boyut_yeniden" in res.get("dsr", {}):
            a, b = res["dsr"]["v1_etkin_boyut_yeniden"], ref.get("ezber", {}).get("etkin_boyut", {})
            ks = ["seri", "N_eff_katilim_orani", "N_eff_ort_korelasyon", "N_eff_kume"]
            T.add("v1 etkin deneme sayısı (N_eff) yeniden üretildi", all(a.get(k) == b.get(k) for k in ks),
                  ", ".join(f"{k} {a.get(k)}/{b.get(k)}" for k in ks), critical=False)
            res["testler"] = T.rows
        flat = {}
        if any(c[0] == PERF_START for c in c4):
            k0 = next(j for j, c in enumerate(c4) if c[0] == PERF_START)
            flat = {lvl: simulate(c4, fee, slip, start_idx=k0) for lvl, (fee, slip) in COSTS.items()}
            for lvl in flat:                       # nakitten başlangıç: baz = 100 (state yeni)
                flat[lvl]["perf_base"] = {"ENS": 100.0, "VM-A": 100.0, "VM-B": 100.0, "B100": c4[k0][1]}
        res["ileri"] = forward_block(flat, runs, spells, last_day)
        res["kayitlar"] = {lvl: {"gunler": [dstr(d) for d in runs[lvl]["days"]],
                                 "ozsermaye": {k: [round(x, 6) for x in runs[lvl]["eq"][k]] for k in runs[lvl]["eq"]},
                                 "ens_islemler": runs[lvl]["ens_trades"],
                                 "vm_islemler": runs[lvl]["vm_trades"]} for lvl in runs}
    res["sure_sn"] = round(time.time() - t_all)
    res["gunluk"] = LOG

    os.makedirs(out_dir)
    with open(os.path.join(out_dir, "sonuc.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1, default=str)
    md = markdown(res)
    with open(os.path.join(out_dir, "SONUC.md"), "w", encoding="utf-8") as fh:
        fh.write(md)
    idx = os.path.join("results", "ON_KAYIT_v2_SONUC.md")
    if not os.path.exists(idx):
        with open(idx, "w", encoding="utf-8") as fh:
            fh.write("# Ön Kayıt v2 — Çalıştırmalar\n\nHer satır ayrı ve değiştirilmeyen bir çalıştırmadır. "
                     "Bu tablo yalnızca sona ekleme ile büyür.\n\n"
                     "| Zaman (UTC) | Commit | Kritik testler | Geçmiş sonuç (keşifsel) | İleri durum | Rapor |\n"
                     "|---|---|---|---|---|---|\n")
    gsum = res.get("gecmis", {}).get("karar", {}).get("sonuc", "yayınlanmadı")
    fsum = res.get("ileri", {}).get("durum", "yayınlanmadı")
    with open(idx, "a", encoding="utf-8") as fh:
        fh.write(f"| {stamp} | `{commit[:7]}` | {'geçti' if T.critical_ok else 'KALDI'} | {gsum} | {fsum} | "
                 f"[SONUC.md](v2/{stamp}_{run_id}/SONUC.md) |\n")
    log(f"Bitti ({res['sure_sn']} sn) → {out_dir}")


if __name__ == "__main__":
    main()
