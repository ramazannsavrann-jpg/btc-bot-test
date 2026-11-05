"""
DOĞRULAMA PAKETİ — docs/ON_KAYIT_v1.md'deki ön kayıtlı planın uygulaması.
Kırılım Ansamblı'nın kuralları DEĞİŞTİRİLMEZ; sadece ölçülür.

Çalıştırma:  python -m bot.validate      (GitHub Actions, numpy gerekir)
Çıktı:       results/dogrulama.json, results/DOGRULAMA.md
"""
from __future__ import annotations

import array
import io
import json
import math
import multiprocessing as mp
import os
import statistics
import time
import zipfile
from datetime import datetime, timezone
from statistics import NormalDist

import numpy as np

from . import data as D, engines, ensemble, external, metrics as MX, overfit, research, strategy as S
from .research_candidates import RESEARCH

SEED = 20261105
H = S.HOUR_MS
DAY = 24 * H
BAR4 = 4 * H
OUT = os.environ.get("BOT_OUT", "results")
N01 = NormalDist()


def ts(s):
    return int(datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() * 1000)


def fmt(t):
    return datetime.fromtimestamp(t / 1000, timezone.utc).strftime("%Y-%m-%d")


SIM_START, MAIN_START, MAIN_END = ts("2022-11-01"), ts("2023-11-01"), ts("2026-11-01")
STRESS_START, STRESS_END = ts("2018-01-01"), ts("2022-11-01")
WARMUP_BARS = 600          # max(360, 540, 200) + 60
LOG = []


def log(*a):
    msg = " ".join(str(x) for x in a)
    LOG.append(msg)
    print(msg, flush=True)


# =============================================================== veri
def months_between(a, b):
    da = datetime.fromtimestamp(a / 1000, timezone.utc)
    now = datetime.now(timezone.utc)
    return (now.year - da.year) * 12 + now.month - da.month + 1


def load_1h():
    c = D.history_symbol("BTC", months_between(ts("2017-08-01"), 0), "1h")
    c = [x for x in c if x[0] < MAIN_END]
    seen = len(c)
    gaps = sum(1 for i in range(1, len(c)) if c[i][0] - c[i - 1][0] > H)
    missing = sum((c[i][0] - c[i - 1][0]) // H - 1 for i in range(1, len(c)) if c[i][0] - c[i - 1][0] > H)
    return c, {"mum_1s": seen, "bosluk_sayisi": gaps, "eksik_1s_mum": int(missing),
               "ilk": fmt(c[0][0]), "son": fmt(c[-1][0])}


def load_minute_closes(t0, t1, interval="1m"):
    """t0..t1 arası dakikalık (veya 15dk) kapanışları, açılış zamanına göre indeksli diziye yükler."""
    step = 60_000 if interval == "1m" else 15 * 60_000
    n = (t1 - t0) // step
    arr = array.array("d", [math.nan]) * n
    d = datetime.fromtimestamp(t0 / 1000, timezone.utc)
    y, m = d.year, d.month
    loaded = 0
    while True:
        ym = f"{y}-{m:02d}"
        if ts(f"{ym}-01") >= t1:
            break
        url = f"https://data.binance.vision/data/spot/monthly/klines/BTCUSDT/{interval}/BTCUSDT-{interval}-{ym}.zip"
        try:
            z = zipfile.ZipFile(io.BytesIO(D._get(url, 120)))
            for line in z.read(z.namelist()[0]).decode().splitlines():
                p = line.split(",", 5)
                if not p[0].isdigit():
                    continue
                t = D._norm_ts(p[0])
                k = (t - t0) // step
                if 0 <= k < n:
                    arr[k] = float(p[4])
                    loaded += 1
        except Exception as e:  # noqa: BLE001
            log(f"{interval} {ym} alınamadı: {e}")
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return arr, step, loaded


# =============================================================== ölçümler (numpy)
def eq_metrics(eq):
    """eq: günlük özsermaye dizisi (başlangıç dahil)."""
    eq = np.asarray(eq, dtype=float)
    r = eq[1:] / eq[:-1] - 1
    days = len(eq) - 1
    cagr = (eq[-1] / eq[0]) ** (365 / days) - 1 if eq[-1] > 0 else -1.0
    peak = np.maximum.accumulate(eq)
    mdd = float(np.max(1 - eq / peak))
    sd = r.std()
    down = np.sqrt(np.mean(np.minimum(r, 0) ** 2))
    return {"getiri_pct": round((eq[-1] / eq[0] - 1) * 100, 2), "cagr_pct": round(cagr * 100, 2),
            "max_dusus_pct": round(mdd * 100, 2), "calmar": round(cagr / mdd, 3) if mdd > 0 else None,
            "sharpe": round(r.mean() / sd * math.sqrt(365), 3) if sd > 0 else 0.0,
            "sortino": round(r.mean() / down * math.sqrt(365), 3) if down > 0 else 0.0}


def batch_metrics(R):
    """R: (örnek, gün) getiri matrisi -> CAGR, Sharpe, Sortino, MDD, Calmar vektörleri."""
    eq = np.cumprod(1 + R, axis=1)
    eq = np.concatenate([np.ones((R.shape[0], 1)), eq], axis=1)
    days = R.shape[1]
    cagr = np.where(eq[:, -1] > 0, eq[:, -1] ** (365 / days) - 1, -1.0)
    peak = np.maximum.accumulate(eq, axis=1)
    mdd = np.max(1 - eq / peak, axis=1)
    sd = R.std(axis=1)
    down = np.sqrt(np.mean(np.minimum(R, 0) ** 2, axis=1))
    mu = R.mean(axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        sharpe = np.where(sd > 0, mu / sd * math.sqrt(365), 0.0)
        sortino = np.where(down > 0, mu / down * math.sqrt(365), 0.0)
        calmar = np.where(mdd > 0, cagr / mdd, np.nan)
    return {"cagr": cagr, "sharpe": sharpe, "sortino": sortino, "mdd": mdd, "calmar": calmar}


def dist(v):
    v = np.asarray(v, dtype=float)
    v = v[~np.isnan(v)]
    if not len(v):
        return {}
    return {"ortanca": round(float(np.median(v)), 4), "p5": round(float(np.percentile(v, 5)), 4),
            "p95": round(float(np.percentile(v, 95)), 4), "ortalama": round(float(v.mean()), 4)}


def prob(mask):
    m = np.asarray(mask, dtype=float)
    p = float(m.mean())
    return {"olasilik": round(p, 4), "mc_hata": round(math.sqrt(p * (1 - p) / len(m)), 4), "n": len(m)}


def lo_sharpe(r, lags=10):
    r = np.asarray(r)
    sd = r.std()
    if sd == 0:
        return 0.0
    sr = r.mean() / sd
    q = 365
    x = r - r.mean()
    rho = [float(np.dot(x[:-k], x[k:]) / np.dot(x, x)) for k in range(1, lags + 1)]
    s = q + 2 * sum((q - k) * rho[k - 1] for k in range(1, lags + 1))
    eta = q / math.sqrt(s) if s > 0 else math.sqrt(q)
    return round(sr * eta, 3), [round(x, 3) for x in rho]


def newey_west(r):
    r = np.asarray(r)
    T = len(r)
    L = int(4 * (T / 100) ** (2 / 9))
    x = r - r.mean()
    g0 = np.dot(x, x) / T
    s = g0
    for k in range(1, L + 1):
        s += 2 * (1 - k / (L + 1)) * np.dot(x[:-k], x[k:]) / T
    se = math.sqrt(max(s, 0) / T)
    m = float(r.mean())
    return {"gecikme": L, "ortalama_gunluk": round(m, 6), "hac_std_hata": round(se, 6),
            "t": round(m / se, 3) if se > 0 else None,
            "guven_95": [round(m - 1.96 * se, 6), round(m + 1.96 * se, 6)],
            "naif_std_hata": round(float(r.std() / math.sqrt(T)), 6)}


def psr(r, sr0=0.0):
    r = np.asarray(r)
    sd = r.std()
    if sd == 0:
        return None
    sr = r.mean() / sd
    skew = float(np.mean((r - r.mean()) ** 3) / sd ** 3)
    kurt = float(np.mean((r - r.mean()) ** 4) / sd ** 4)
    den = 1 - skew * sr + (kurt - 1) / 4 * sr * sr
    z = (sr - sr0) * math.sqrt(len(r) - 1) / math.sqrt(den) if den > 0 else 0
    return round(N01.cdf(z), 4)


# =============================================================== ansambl simülasyonu
def ens_params(vt=0.4):
    cand = next(c for c in RESEARCH if c["id"] == "kirilim_ansambl")
    return dict(research.base_params(cand), vol_target=vt)


def run_ens(c4, p, t_meas0, t_meas1):
    """Kesintisiz simülasyon (ilk mumdan), ölçüm aralığında günlük özsermaye + BTC ağırlığı + kapanış."""
    E = ensemble
    ind = E.indicators(c4, p)
    st = E.new_state(100.0, p)
    days, eqd, wd, cd, expo = [], [], [], [], []
    pre = []          # ölçüm öncesi günlük özsermaye (VM için geçmiş oynaklık)
    for i in range(len(c4)):
        if c4[i][0] >= t_meas1:
            break
        E.process_bar(st, c4, ind, i)
        px = c4[i][4]
        eq = research.exit_value(st, px)
        day = (c4[i][0] + BAR4) // DAY - 1 if (c4[i][0] + BAR4) % DAY == 0 else None
        if day is None:
            continue                       # sadece günün son 4s mumu (20:00 açılış -> 24:00 kapanış)
        w = st["qty"] * px / eq if eq > 0 else 0.0
        if c4[i][0] + BAR4 <= t_meas0:
            pre.append(eq)
            continue
        days.append(day); eqd.append(eq); wd.append(w); cd.append(px); expo.append(st["qty"] > 0)
    trades = [t for t in st["trades"] if t_meas0 <= t["exit_ts"] < t_meas1]
    start_eq = pre[-1] if pre else eqd[0]
    return {"days": days, "eq": [start_eq] + eqd, "w": wd, "close": cd, "expo": expo, "pre": pre,
            "trades": trades, "all_trades": st["trades"]}


def daily_closes(c4, t0, t1):
    out = {}
    for c in c4:
        if t0 - 400 * DAY <= c[0] < t1:
            out[(c[0] + BAR4 - 1) // DAY] = c[4]
    return out


# =============================================================== benchmark'lar
def bench(closes, weights, fee=0.001, slip=0.0005, rebalance="none", band=0.0, start_close=None):
    """closes: ölçüm günleri kapanışları; weights: her gün hedef ağırlık (liste) veya sabit sayı.
    Gün 0 kapanışında (veya start_close'da) alım. Maliyet = işlem tutarı × (fee+slip)."""
    cost = fee + slip
    eq = 100.0
    p0 = start_close if start_close else closes[0]
    w0 = weights[0] if isinstance(weights, list) else weights
    btc = eq * w0 * (1 - cost) / p0
    cash = eq * (1 - w0)
    out = [100.0]
    prev_month = None
    for d, px in enumerate(closes):
        eq = cash + btc * px
        tw = weights[d] if isinstance(weights, list) else weights
        do = False
        if rebalance == "monthly":
            mon = datetime.fromtimestamp(DAYS_REF[d] * DAY / 1000, timezone.utc).month if DAYS_REF else d // 30
            do = prev_month is not None and mon != prev_month
            prev_month = mon
        elif rebalance == "band":
            cur = btc * px / eq if eq > 0 else 0
            do = abs(cur - tw) > band
        if do:
            target_btc_val = eq * tw
            delta = target_btc_val - btc * px
            fee_amt = abs(delta) * cost
            btc += delta / px
            cash -= delta + fee_amt
            eq = cash + btc * px
        out.append(eq)
    return out


DAYS_REF: list = []


def vm_weights(ens_rets_full, btc_rets_full, n_pre, n_days, fallback):
    """Her gün d için: min(1, σ_ens / σ_btc), son 90 günün (d−1'e kadar) getirileriyle."""
    w = []
    for d in range(n_days):
        k = n_pre + d                          # tam dizideki indeks (bugün)
        a = ens_rets_full[max(0, k - 90):k]
        b = btc_rets_full[max(0, k - 90):k]
        active = sum(1 for x in a if x != 0)
        if active < 30 or len(b) < 30:
            w.append(fallback)
            continue
        sa, sb = statistics.pstdev(a), statistics.pstdev(b)
        w.append(min(1.0, sa / sb) if sb > 0 else 1.0)
    return w


def benchmarks_for(run, btc_daily_full_days, btc_daily):
    """run: run_ens çıktısı; btc_daily: {gün: kapanış}."""
    global DAYS_REF
    days = run["days"]
    DAYS_REF = days
    closes = [btc_daily[d] for d in days]
    start_close = btc_daily.get(days[0] - 1, closes[0])
    avg_w = float(np.mean(run["w"]))
    out = {"B100": bench(closes, 1.0, start_close=start_close)}
    for w in (0.25, 0.5, 0.75):
        out[f"S{int(w * 100)}"] = bench(closes, w, start_close=start_close)
        out[f"M{int(w * 100)}"] = bench(closes, w, rebalance="monthly", start_close=start_close)
    out["WM"] = bench(closes, avg_w, rebalance="monthly", start_close=start_close)
    # VM: ansamblın ve BTC'nin günlük getirileri (ölçüm öncesi dahil)
    pre = run["pre"]
    ens_full = pre + run["eq"][1:]
    ens_r = [ens_full[i] / ens_full[i - 1] - 1 for i in range(1, len(ens_full))]
    pre_days = list(range(days[0] - len(pre), days[0]))
    all_days = pre_days + days
    bc = [btc_daily.get(d) for d in all_days]
    btc_r = [bc[i] / bc[i - 1] - 1 if bc[i] and bc[i - 1] else 0.0 for i in range(1, len(bc))]
    n_pre = len(pre) - 1 if pre else 0
    vw = vm_weights(ens_r, btc_r, max(0, n_pre), len(days), avg_w)
    out["VM"] = bench(closes, vw, rebalance="band", band=0.05, start_close=start_close)
    return out, avg_w, vw


# =============================================================== bootstrap
def stationary_idx(rng, n, mean_block, R):
    p = 1.0 / mean_block
    idx = np.empty((R, n), dtype=np.int64)
    idx[:, 0] = rng.integers(0, n, R)
    for t in range(1, n):
        new = rng.random(R) < p
        idx[:, t] = np.where(new, rng.integers(0, n, R), (idx[:, t - 1] + 1) % n)
    return idx


def bootstrap_A(series, R=10000):
    rng = np.random.default_rng(SEED)
    names = list(series)
    M = np.array([np.asarray(series[k][1:]) / np.asarray(series[k][:-1]) - 1 for k in names])
    n = M.shape[1]
    out = {}
    for b in (7, 14, 30):
        idx = stationary_idx(rng, n, b, R)
        res = {k: batch_metrics(M[j][idx]) for j, k in enumerate(names)}
        e = res["ENS"]
        out[f"{b}g"] = {
            "ENS_sharpe": dist(e["sharpe"]), "ENS_cagr": dist(e["cagr"]), "ENS_mdd": dist(e["mdd"]),
            "ENS_calmar": dist(e["calmar"]), "ENS_sortino": dist(e["sortino"]),
            "sharpe_fark_B100": dist(e["sharpe"] - res["B100"]["sharpe"]),
            "P_sharpe_gt_B100": prob(e["sharpe"] > res["B100"]["sharpe"]),
            "calmar_fark_VM": dist(e["calmar"] - res["VM"]["calmar"]),
            "P_calmar_gt_VM": prob(e["calmar"] > res["VM"]["calmar"]),
            "sharpe_fark_WM": dist(e["sharpe"] - res["WM"]["sharpe"]),
            "P_sharpe_gt_WM": prob(e["sharpe"] > res["WM"]["sharpe"]),
            "P_mdd_lt_B100": prob(e["mdd"] < res["B100"]["mdd"]),
            "cagr_fark_VM": dist(e["cagr"] - res["VM"]["cagr"]),
            "P_negatif_getiri": prob(e["cagr"] < 0),
        }
    return out


_BDATA = {}


def _synthetic_path(args):
    """Bir sentetik 4s fiyat yolu üret, ansambl + benchmark'ları çalıştır, ölçümleri döndür."""
    seed, k, mean_block, vt = args
    warm, pool_rel, pool_ts = _BDATA["warm"], _BDATA["rel"], _BDATA["ts"]
    rng = np.random.default_rng([seed, k, mean_block, int(vt * 100)])
    n = len(pool_rel)
    p = 1.0 / mean_block
    idx = np.empty(n, dtype=np.int64)
    idx[0] = rng.integers(0, n)
    starts = 1
    for t in range(1, n):
        if rng.random() < p:
            idx[t] = rng.integers(0, n)
            starts += 1
        else:
            idx[t] = (idx[t - 1] + 1) % n
    candles = list(warm)
    pc = warm[-1][4]
    bad = 0
    gaps_b, gaps_all = [], []
    for t in range(n):
        o, h, l, c = pool_rel[idx[t]]
        bar = (pool_ts[t], pc * o, pc * h, pc * l, pc * c, 1.0)
        if not (bar[2] >= max(bar[1], bar[4]) - 1e-9 and bar[3] <= min(bar[1], bar[4]) + 1e-9):
            bad += 1
        g = o - 1
        gaps_all.append(g)
        if t == 0 or idx[t] != (idx[t - 1] + 1) % n:
            gaps_b.append(g)
        candles.append(bar)
        pc = bar[4]
    pr = ens_params(vt)
    run = run_ens(candles, pr, pool_ts[0], pool_ts[-1] + BAR4)
    btc_daily = daily_closes(candles, candles[0][0], pool_ts[-1] + BAR4)
    bm, avg_w, _ = benchmarks_for(run, None, btc_daily)
    me = eq_metrics(run["eq"])
    res = {"ENS": me, "B100": eq_metrics(bm["B100"]), "VM": eq_metrics(bm["VM"]), "WM": eq_metrics(bm["WM"]),
           "avg_w": avg_w, "bad_bars": bad, "blocks": starts,
           "gap_boundary_abs_mean": float(np.mean(np.abs(gaps_b))) if gaps_b else 0.0,
           "gap_all_abs_mean": float(np.mean(np.abs(gaps_all)))}
    # sentetik yol istatistikleri (gerçekle karşılaştırma için)
    cl = np.array([c[4] for c in candles[len(warm):]])
    lr = np.diff(np.log(cl))
    a = np.abs(lr - lr.mean())
    res["acf_abs"] = float(np.mean([np.corrcoef(a[:-j], a[j:])[0, 1] for j in range(1, 11)]))
    dcl = np.array([btc_daily[d] for d in sorted(btc_daily) if d >= pool_ts[0] // DAY])
    r20 = np.sign(dcl[20:] / dcl[:-20] - 1)
    runs, cur = [], 1
    for j in range(1, len(r20)):
        if r20[j] == r20[j - 1]:
            cur += 1
        else:
            runs.append(cur); cur = 1
    runs.append(cur)
    res["trend_run"] = float(np.mean(runs))
    return res


def path_stats_real(c4_meas, daily):
    cl = np.array([c[4] for c in c4_meas])
    lr = np.diff(np.log(cl))
    a = np.abs(lr - lr.mean())
    acf = float(np.mean([np.corrcoef(a[:-j], a[j:])[0, 1] for j in range(1, 11)]))
    dcl = np.array([daily[d] for d in sorted(daily) if d >= c4_meas[0][0] // DAY])
    r20 = np.sign(dcl[20:] / dcl[:-20] - 1)
    runs, cur = [], 1
    for j in range(1, len(r20)):
        if r20[j] == r20[j - 1]:
            cur += 1
        else:
            runs.append(cur); cur = 1
    runs.append(cur)
    gaps = [c4_meas[i][1] / c4_meas[i - 1][4] - 1 for i in range(1, len(c4_meas))]
    peak = np.maximum.accumulate(dcl)
    return {"acf_abs": round(acf, 4), "trend_run": round(float(np.mean(runs)), 2),
            "gap_abs_mean": round(float(np.mean(np.abs(gaps))), 6),
            "btc_mdd": round(float(np.max(1 - dcl / peak)) * 100, 2)}


def bootstrap_B(c4, n_paths=2000, blocks=(180, 360, 540), vts=(0.4,), extra_vt_block=360):
    i0 = next(i for i, c in enumerate(c4) if c[0] >= MAIN_START)
    i1 = next((i for i, c in enumerate(c4) if c[0] >= MAIN_END), len(c4))
    meas = c4[i0:i1]
    warm = c4[i0 - WARMUP_BARS:i0]
    rel = [(meas[0][1] / c4[i0 - 1][4], meas[0][2] / c4[i0 - 1][4], meas[0][3] / c4[i0 - 1][4], meas[0][4] / c4[i0 - 1][4])]
    rel += [(m[1] / p[4], m[2] / p[4], m[3] / p[4], m[4] / p[4]) for p, m in zip(meas[:-1], meas[1:])]
    pool_ts = [m[0] for m in meas]
    jobs = []
    for vt in vts:
        for b in (blocks if vt == 0.4 else (extra_vt_block,)):
            jobs.append((vt, b))
    out = {}
    workers = max(1, os.cpu_count() or 1)
    _BDATA.update({"warm": warm, "rel": rel, "ts": pool_ts})
    with mp.get_context("fork").Pool(workers) as pool:
        for vt, b in jobs:
            t = time.time()
            args = [(SEED, k, b, vt) for k in range(n_paths)]
            res = pool.map(_synthetic_path, args, chunksize=8)
            out[f"vt{int(vt * 100)}_blok{b}"] = summarize_B(res)
            log(f"Bootstrap B vt={vt} blok={b}: {n_paths} yol, {time.time() - t:.0f} sn")
    return out, meas


def summarize_B(res):
    def g(k, m):
        return np.array([r[k][m] if r[k][m] is not None else np.nan for r in res], dtype=float)

    def block(sub):
        es, bs = g("ENS", "sharpe")[sub], g("B100", "sharpe")[sub]
        ec, vc = g("ENS", "calmar")[sub], g("VM", "calmar")[sub]
        ws = g("WM", "sharpe")[sub]
        em, bm = g("ENS", "max_dusus_pct")[sub], g("B100", "max_dusus_pct")[sub]
        return {
            "P1_sharpe_gt_B100": prob(es > bs), "sharpe_fark_B100": dist(es - bs),
            "P2_calmar_gt_VM": prob(np.nan_to_num(ec, nan=-9) > np.nan_to_num(vc, nan=-9)),
            "calmar_fark_VM": dist(ec - vc),
            "P3_sharpe_gt_WM": prob(es > ws), "sharpe_fark_WM": dist(es - ws),
            "P4_mdd_lt_B100": prob(em < bm), "mdd_fark_B100": dist(em - bm),
            "ENS_cagr": dist(g("ENS", "cagr_pct")[sub]), "ENS_mdd": dist(em), "ENS_sharpe": dist(es),
            "ENS_calmar": dist(ec), "B100_cagr": dist(g("B100", "cagr_pct")[sub]), "B100_mdd": dist(bm),
            "VM_cagr": dist(g("VM", "cagr_pct")[sub]), "VM_mdd": dist(g("VM", "max_dusus_pct")[sub]),
            "P_ens_negatif": prob(g("ENS", "getiri_pct")[sub] < 0),
        }
    n = len(res)
    out = {"n": n, "tum": block(slice(0, n)), "ilk_1000": block(slice(0, min(1000, n)))}
    out["kontrol"] = {
        "tutarsiz_mum": int(sum(r["bad_bars"] for r in res)),
        "ortalama_blok_sayisi": round(float(np.mean([r["blocks"] for r in res])), 1),
        "blok_siniri_acilis_boslugu_ort": round(float(np.mean([r["gap_boundary_abs_mean"] for r in res])), 6),
        "tum_acilis_boslugu_ort": round(float(np.mean([r["gap_all_abs_mean"] for r in res])), 6),
        "acf_abs": dist([r["acf_abs"] for r in res]), "trend_run": dist([r["trend_run"] for r in res]),
        "btc_mdd": dist([r["B100"]["max_dusus_pct"] for r in res]),
        "ens_ort_btc_agirligi": dist([r["avg_w"] for r in res]),
    }
    return out


# =============================================================== gecikmeli dolum
def delayed_runs(c4, minute, mstep, label, t0_arr):
    out = {}
    for delay_min in (15, 30, 60):
        stats = {"n": 0, "fark_bp": [], "eksik": 0}

        def hook(kind, t_event, px, state, d=delay_min * 60_000):
            k = (t_event + d - t0_arr) // mstep - 1          # bu anda KAPANAN mumun indeksi
            v = minute[k] if 0 <= k < len(minute) else math.nan
            if math.isnan(v):
                stats["eksik"] += 1
                return px
            stats["n"] += 1
            diff = (v / px - 1) * 1e4
            stats["fark_bp"].append(diff if kind == "giris" else -diff)   # + = aleyhimize
            return v
        S.FILL_HOOK = hook
        try:
            run = run_ens(c4, ens_params(0.4), MAIN_START, MAIN_END)
        finally:
            S.FILL_HOOK = None
        m = eq_metrics(run["eq"])
        fb = stats["fark_bp"]
        out[f"+{delay_min}dk"] = {**m, "dolum": stats["n"], "eksik_veri": stats["eksik"],
                                   "ort_fark_bp_aleyhte": round(float(np.mean(fb)), 2) if fb else None,
                                   "islem": len(run["trades"])}
    return {label: out}


# =============================================================== rejim
def daily_regimes(daily):
    keys = sorted(daily)
    cl = [daily[k] for k in keys]
    e200, e50 = S.ema(cl, 200), S.ema(cl, 50)
    r = [0.0] + [cl[i] / cl[i - 1] - 1 for i in range(1, len(cl))]
    vol30 = [statistics.pstdev(r[i - 30:i]) if i >= 31 else math.nan for i in range(len(cl))]
    lab = {}
    for i in range(1, len(cl)):
        j = i - 1                                   # sadece dünkü veriye kadar
        if j < 211 or math.isnan(e200[j]):
            continue
        slope = e50[j] - e50[j - 10]
        up = cl[j] > e200[j]
        yon = "Yükseliş" if up and slope > 0 else "Düşüş" if (not up and slope < 0) else "Yatay/kararsız"
        hist = [vol30[x] for x in range(max(31, j - 365), j + 1) if not math.isnan(vol30[x])]
        v = vol30[j]
        if len(hist) < 60 or math.isnan(v):
            vl = "?"
        else:
            med = statistics.median(hist)
            vl = "yüksek" if v > 1.25 * med else "düşük" if v < 0.8 * med else "normal"
        lab[keys[i]] = (yon, vl)
    return lab


def regime_table(run, daily, lab):
    days = run["days"]
    eq = run["eq"]
    r = [eq[i + 1] / eq[i] - 1 for i in range(len(days))]
    br = [daily[d] / daily[d - 1] - 1 if d - 1 in daily else 0.0 for d in days]
    entries = {}
    for t in run["trades"]:
        entries[t["entry_ts"] // DAY] = entries.get(t["entry_ts"] // DAY, 0) + 1
    out = {}
    for axis, pos in (("yon", 0), ("oynaklik", 1)):
        groups = {}
        for i, d in enumerate(days):
            if d not in lab:
                continue
            groups.setdefault(lab[d][pos], []).append(i)
        res = {}
        for g, ix in groups.items():
            rr = np.array([r[i] for i in ix])
            bb = np.array([br[i] for i in ix])
            episodes = 1 + sum(1 for a, b in zip(ix, ix[1:]) if b != a + 1)
            eqc = np.concatenate([[1.0], np.cumprod(1 + rr)])
            beq = np.concatenate([[1.0], np.cumprod(1 + bb)])
            res[g] = {"gun": len(ix), "ayri_donem": episodes,
                      "ens_log_getiri_pct": round(float(np.sum(np.log1p(rr))) * 100, 2),
                      "btc_log_getiri_pct": round(float(np.sum(np.log1p(bb))) * 100, 2),
                      "ens_sharpe": round(float(rr.mean() / rr.std() * math.sqrt(365)), 3) if rr.std() > 0 else 0.0,
                      "btc_sharpe": round(float(bb.mean() / bb.std() * math.sqrt(365)), 3) if bb.std() > 0 else 0.0,
                      "ens_mdd_pct": round(float(np.max(1 - eqc / np.maximum.accumulate(eqc))) * 100, 2),
                      "btc_mdd_pct": round(float(np.max(1 - beq / np.maximum.accumulate(beq))) * 100, 2),
                      "islem_acilisi": sum(entries.get(days[i], 0) for i in ix),
                      "piyasada_pct": round(100 * float(np.mean([run["expo"][i] for i in ix])), 1),
                      "ort_btc_agirligi": round(float(np.mean([run["w"][i] for i in ix])), 3)}
        out[axis] = res
    return out


# =============================================================== pozisyon taşıma (A/B)
def wf_carry(cand, data, wins, carry):
    iv = cand["params"].get("interval", "1h")
    candles = data[iv]
    tsl = [c[0] for c in candles]
    base = research.base_params(cand)
    keys = list(cand.get("grid", {}))
    import itertools
    combos = list(itertools.product(*cand["grid"].values())) if keys else [()]
    cfgs = []
    for vals in combos:
        p = dict(base, **dict(zip(keys, vals)))
        E = engines.get(p)
        cfgs.append((p, E, E.indicators(candles, p)))
    import bisect
    eq_pts, trades = [], []
    active, legacy = None, []
    cash0 = 100.0
    for (tr_s, tr_e, te_e) in wins:
        best, bsc = None, -math.inf
        for p, E, ind in cfgs:
            st, pts, _, _ = research.sim(E, candles, tsl, ind, p, tr_s, tr_e)
            sc = MX.sharpe(MX.returns(MX.daily(pts))) if len(st["trades"]) >= 4 else -math.inf
            if sc > bsc or best is None:
                best, bsc = (p, E, ind), sc
        p, E, ind = best
        i0, i1 = bisect.bisect_left(tsl, tr_e), bisect.bisect_left(tsl, te_e)
        new = E.new_state(cash0, p)
        new["last_ts"] = candles[i0 - 1][0]
        if active is not None:
            if carry and active["qty"] > 0:
                new["cash"] = active["cash"]
                active["cash"] = 0.0
                active["pause_until"] = 10 ** 15
                legacy.append((active, aE, aind))
            else:
                if active["qty"] > 0:
                    aE.close_all(active, candles[i0 - 1][0], candles[i0 - 1][4], "pencere sonu")
                new["cash"] = active["cash"]
                trades += active["trades"]
        active, aE, aind = new, E, ind
        for i in range(i0, i1):
            for lg in list(legacy):
                st, E2, ind2 = lg
                E2.process_bar(st, candles, ind2, i)
                if st["qty"] <= 0 and st.get("position") is None and not st.get("lots"):
                    active["cash"] += st["cash"]
                    trades += st["trades"]
                    legacy.remove(lg)
            E.process_bar(active, candles, ind, i)
            px = candles[i][4]
            eq = research.exit_value(active, px) + sum(research.exit_value(s, px) for s, _, _ in legacy)
            eq_pts.append((candles[i][0], eq))
        cash0 = active["cash"]
    if active is not None:
        last = candles[min(len(candles), bisect.bisect_left(tsl, wins[-1][2])) - 1]
        for s, E2, _ in legacy:
            E2.close_all(s, last[0], last[4], "son")
            trades += s["trades"]
        aE.close_all(active, last[0], last[4], "son")
        trades += active["trades"]
    m = MX.full(eq_pts, trades, 0, 1)
    return {k: m[k] for k in ("getiri_pct", "cagr_pct", "sharpe", "max_dusus_pct", "calmar", "islem")}


# =============================================================== DSR / N_eff
def all_trial_returns(data, d15):
    """Bütün BTC deneme ayarlarının (başarısızlar dahil) ölçüm dönemindeki sabit-ayar günlük getirileri."""
    import itertools
    from .candidates import CANDIDATES
    from .backtest import GRID as TGRID
    from .grid import DEFAULT_PARAMS as GDEF
    trials = []
    for c in RESEARCH:
        trials.append(("arastirma", c, research.base_params(c)))
    for c in CANDIDATES:
        b = dict(GDEF, **c["params"]) if c["params"].get("engine") == "grid" else dict(S.DEFAULT_PARAMS, **c["params"])
        trials.append(("btc_2y", c, b))
    trials.append(("temkinli_tablo", {"id": "temkinli_bt", "grid": TGRID}, dict(S.DEFAULT_PARAMS)))
    series = {}
    dd = dict(data, **{"15m": d15})
    for src, c, base in trials:
        keys = list(c.get("grid", {}))
        combos = list(itertools.product(*c["grid"].values())) if keys else [()]
        iv = base.get("interval", "1h")
        cs = dd[iv]
        tsl = [x[0] for x in cs]
        for vals in combos:
            p = dict(base, **dict(zip(keys, vals)))
            E = engines.get(p)
            _, pts, _, _ = research.sim(E, cs, tsl, E.indicators(cs, p), p, MAIN_START, MAIN_END)
            d = MX.daily(pts)
            series[f"{src}|{c['id']}|{vals}"] = [d[i] / d[i - 1] - 1 for i in range(1, len(d))]
    return series


def n_eff_estimates(series):
    T = min(len(v) for v in series.values())
    X = np.array([v[:T] for v in series.values()])
    sd = X.std(axis=1)
    live = sd > 0
    Xl = X[live]
    C = np.corrcoef(Xl)
    C = np.nan_to_num(C)
    lam = np.linalg.eigvalsh(C)
    lam = np.clip(lam, 0, None)
    pr = float(lam.sum() ** 2 / (lam ** 2).sum())
    n = C.shape[0]
    rho = float((C.sum() - n) / (n * (n - 1)))
    avg = n / (1 + (n - 1) * max(rho, 0.0))
    # hiyerarşik kümeleme (ortalama bağlantı, Lance–Williams), ρ > 0.7 -> aynı küme (uzaklık < 0.3)
    Dm = 1 - C
    np.fill_diagonal(Dm, np.inf)
    size = np.ones(n)
    alive = np.ones(n, dtype=bool)
    while alive.sum() > 1:
        sub = np.where(alive[:, None] & alive[None, :], Dm, np.inf)
        k = int(np.argmin(sub))
        i, j = divmod(k, n)
        if sub[i, j] > 0.3:
            break
        newrow = (size[i] * Dm[i] + size[j] * Dm[j]) / (size[i] + size[j])
        Dm[i, :] = newrow
        Dm[:, i] = newrow
        Dm[i, i] = np.inf
        size[i] += size[j]
        alive[j] = False
        Dm[j, :] = np.inf
        Dm[:, j] = np.inf
    clusters = [0] * int(alive.sum())
    return {"seri": len(series), "degisken_seri": int(n), "sabit_seri": int((~live).sum()),
            "N_eff_katilim_orani": round(pr, 1), "N_eff_ort_korelasyon": round(avg, 1),
            "ort_korelasyon": round(rho, 3), "N_eff_kume": len(clusters)}


def dsr_table(r_ens, series, Ns):
    sh = [statistics.mean(v) / statistics.pstdev(v) if statistics.pstdev(v) > 0 else 0.0 for v in series.values()]
    out = {}
    for name, N in Ns.items():
        out[name] = overfit.deflated_sharpe(r_ens, sh, n_trials=max(2, int(round(N))))
    return out


# =============================================================== ana akış
def main():
    t_all = time.time()
    os.makedirs(OUT, exist_ok=True)
    res = {"on_kayit": "docs/ON_KAYIT_v1.md", "tohum": SEED,
           "olusturma": datetime.now(timezone.utc).isoformat(timespec="minutes")}
    log("Veri yükleniyor...")
    c1, q = load_1h()
    res["veri"] = q
    log("1s veri:", q)
    c4 = D.aggregate(c1, 4)
    res["veri"]["mum_4s"] = len(c4)
    daily_all = daily_closes(c4, c4[0][0] + 400 * DAY, MAIN_END)
    if not external.FG:
        external.load_fear_greed(0)

    # ---- 1) ana dönem: ansambl kesintisiz + benchmark'lar
    c4_main = [c for c in c4 if c[0] >= SIM_START - WARMUP_BARS * BAR4 and c[0] < MAIN_END]
    run = run_ens(c4_main, ens_params(0.4), MAIN_START, MAIN_END)
    bm, avg_w, vw = benchmarks_for(run, None, daily_all)
    tab = {"ENS (vt %40)": eq_metrics(run["eq"])}
    for k, v in bm.items():
        tab[k] = eq_metrics(v)
    ens_r = [run["eq"][i + 1] / run["eq"][i] - 1 for i in range(len(run["days"]))]
    tab["ENS (vt %40)"].update({"islem": len(run["trades"]),
                                "piyasada_pct": round(100 * float(np.mean(run["expo"])), 1),
                                "ort_btc_agirligi": round(avg_w, 3)})
    res["ana_donem"] = {"olcum": f"{fmt(MAIN_START)} → {fmt(MAIN_END - DAY)}", "tablo": tab,
                        "vm_ortalama_agirlik": round(float(np.mean(vw)), 3)}
    lo, rho = lo_sharpe(ens_r)
    res["sharpe_duzeltme"] = {"standart": tab["ENS (vt %40)"]["sharpe"], "lo_2002": lo, "otokorelasyon_1_10": rho,
                              "newey_west": newey_west(ens_r), "psr_gt_0": psr(ens_r),
                              "btc_standart": tab["B100"]["sharpe"]}
    log("Ana dönem tamam")

    # ---- 2) 2× maliyet (eşik 5)
    p2 = dict(ens_params(0.4), fee=0.002, slip=0.001)
    r2 = run_ens(c4_main, p2, MAIN_START, MAIN_END)
    res["maliyet_2x"] = eq_metrics(r2["eq"])

    # ---- 3) vol hedefleri (gerçek yol)
    res["vol_hedefleri_gercek"] = {}
    for vt in (0.2, 0.3, 0.4):
        rv = run_ens(c4_main, ens_params(vt), MAIN_START, MAIN_END)
        m = eq_metrics(rv["eq"])
        m.update({"islem": len(rv["trades"]), "ort_btc_agirligi": round(float(np.mean(rv["w"])), 3)})
        res["vol_hedefleri_gercek"][f"%{int(vt * 100)}"] = m

    # ---- 4) günlük rejim
    lab = daily_regimes(daily_all)
    res["rejim"] = regime_table(run, daily_all, lab)
    log("Rejim tamam")

    # ---- 5) 2018–2022 stres
    c4_s = [c for c in c4 if c[0] < STRESS_END]
    rs = run_ens(c4_s, ens_params(0.4), STRESS_START, STRESS_END)
    bms, avg_ws, _ = benchmarks_for(rs, None, daily_all)
    eqs = np.array(rs["eq"])
    res["stres_2018_2022"] = {"olcum": f"{fmt(STRESS_START)} → {fmt(STRESS_END - DAY)}",
                              "ENS": {**eq_metrics(rs["eq"]), "islem": len(rs["trades"]),
                                      "en_dusuk_ozsermaye_pct": round(float(eqs.min() / eqs[0] * 100), 2),
                                      "ort_btc_agirligi": round(avg_ws, 3)},
                              "B100": eq_metrics(bms["B100"]), "VM": eq_metrics(bms["VM"]),
                              "WM": eq_metrics(bms["WM"]), "M50": eq_metrics(bms["M50"]),
                              "not": "Binance BTCUSDT verisi 2017-08-17'de başlar; 2017–2019 likiditesi ve piyasa "
                                     "yapısı bugünden farklıdır. Bu dönem parametre seçiminde kullanılmadı."}
    log("Stres testi tamam")

    # ---- 6) bootstrap A
    series = {"ENS": run["eq"], "B100": bm["B100"], "VM": bm["VM"], "WM": bm["WM"]}
    res["bootstrap_A"] = bootstrap_A(series, 10000)
    log("Bootstrap A tamam")

    # ---- 7) gecikmeli dolum (1 dk ana, 15 dk kontrol)
    try:
        t0m = SIM_START - WARMUP_BARS * BAR4
        m1, st1, n1 = load_minute_closes(t0m, MAIN_END, "1m")
        log(f"1 dk veri: {n1} mum")
        res["gecikmeli_dolum"] = delayed_runs(c4_main, m1, st1, "1dk_veri", t0m)
        del m1
        m15, st15, n15 = load_minute_closes(t0m, MAIN_END, "15m")
        res["gecikmeli_dolum"].update(delayed_runs(c4_main, m15, st15, "15dk_kontrol", t0m))
        res["gecikmeli_dolum"]["temel_gecikmesiz"] = tab["ENS (vt %40)"]
    except Exception as e:  # noqa: BLE001
        res["gecikmeli_dolum"] = {"hata": str(e)}
    log("Gecikmeli dolum tamam")

    # ---- 8) taşıma A/B
    data = {"1h": [c for c in c1 if c[0] < MAIN_END and c[0] >= SIM_START - 30 * DAY], "4h": c4_main}
    wins = research.windows(data["1h"][0][0] + 30 * DAY, MAIN_END)
    carry = {}
    for cand in RESEARCH:
        if not cand.get("grid"):
            continue
        try:
            a = wf_carry(cand, data, wins, False)
            b = wf_carry(cand, data, wins, True)
            carry[cand["id"]] = {"A_kapat": a, "B_tasi": b}
        except Exception as e:  # noqa: BLE001
            carry[cand["id"]] = {"hata": str(e)}
    res["tasima_testi"] = {"pencere": len(wins), "sonuc": carry}
    log("Taşıma testi tamam")

    # ---- 9) DSR / N_eff / PBO
    try:
        d15 = D.history_symbol("BTC", months_between(SIM_START - 30 * DAY, 0), "15m")
        d15 = [c for c in d15 if SIM_START - 30 * DAY <= c[0] < MAIN_END]
        ser = all_trial_returns(data, d15)
        T = min(len(v) for v in ser.values())
        ser = {k: v[:T] for k, v in ser.items()}
        ne = n_eff_estimates(ser)
        r_e = ens_r[:T]
        n_total = len(ser) + 14
        Ns = {"N=10": 10, "N=20": 20, "N=40": 40, "N=69": 69, "N_eff_katilim": ne["N_eff_katilim_orani"],
              "N_eff_ort_korelasyon": ne["N_eff_ort_korelasyon"], "N_eff_kume": ne["N_eff_kume"],
              f"N_toplam={n_total}": n_total}
        res["ezber"] = {"etkin_boyut": ne, "dsr": dsr_table(r_e, ser, Ns), "n_toplam": n_total,
                        "pbo_tum_denemeler": overfit.pbo(ser),
                        "not": "30 coin turnuvasının 14 ayarı çok varlıklı olduğu için korelasyona giremedi; "
                               "sadece N_toplam'a eklendi."}
    except Exception as e:  # noqa: BLE001
        res["ezber"] = {"hata": str(e)}
    log("Ezber ölçümleri tamam")

    # ---- 10) bootstrap B (karar)
    c4_B = [c for c in c4 if c[0] < MAIN_END]
    n_paths = int(os.environ.get("BOOT_PATHS", "2000"))
    bB, meas = bootstrap_B(c4_B, n_paths=n_paths, vts=(0.4, 0.3, 0.2))
    res["bootstrap_B"] = bB
    res["bootstrap_B_gercek_yol"] = path_stats_real(meas, daily_all)

    # ---- 11) ön kayıtlı eşikler
    main_B = bB["vt40_blok360"]["tum"]
    res["esikler"] = verdict(main_B, res)
    res["sure_sn"] = round(time.time() - t_all)
    res["gunluk"] = LOG
    with open(os.path.join(OUT, "dogrulama.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1, default=str)
    from .validate_report import markdown
    with open(os.path.join(OUT, "DOGRULAMA.md"), "w", encoding="utf-8") as f:
        f.write(markdown(res))
    log(f"Bitti ({res['sure_sn']} sn)")


def verdict(B, res):
    s = res["stres_2018_2022"]["ENS"]
    rows = [
        ("1", "P(Sharpe ansambl > Sharpe B100)", B["P1_sharpe_gt_B100"]["olasilik"], ">= 0.90",
         B["P1_sharpe_gt_B100"]["olasilik"] >= 0.90),
        ("2", "P(Calmar ansambl > Calmar VM)", B["P2_calmar_gt_VM"]["olasilik"], ">= 0.90",
         B["P2_calmar_gt_VM"]["olasilik"] >= 0.90),
        ("3", "P(Sharpe ansambl > Sharpe WM)", B["P3_sharpe_gt_WM"]["olasilik"], ">= 0.90",
         B["P3_sharpe_gt_WM"]["olasilik"] >= 0.90),
        ("4", "P(MDD ansambl < MDD B100)", B["P4_mdd_lt_B100"]["olasilik"], ">= 0.90",
         B["P4_mdd_lt_B100"]["olasilik"] >= 0.90),
        ("5", "2× maliyetle toplam net getiri (%)", res["maliyet_2x"]["getiri_pct"], "> 0",
         res["maliyet_2x"]["getiri_pct"] > 0),
        ("6", "2018–2022 MDD (%) / en düşük özsermaye (%)", f"{s['max_dusus_pct']} / {s['en_dusuk_ozsermaye_pct']}",
         "MDD <= 40 ve en düşük >= 50", s["max_dusus_pct"] <= 40 and s["en_dusuk_ozsermaye_pct"] >= 50),
        ("7", "Canlı kâğıt test ≥ 12 ay ve ≥ 20 işlem", "henüz başladı (5 Kasım 2026)", "12 ay + 20 işlem", False),
        ("8", "Operasyonel doğruluk testleri", "kısmen (motor eşdeğerliği ve look-ahead testi geçti)",
         "tüm senaryolar", False),
    ]
    return [{"no": a, "sart": b, "sonuc": c, "esik": d, "gecti": bool(e)} for a, b, c, d, e in rows]


if __name__ == "__main__":
    main()
