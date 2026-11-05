"""
Ezber (overfitting) ölçümleri — çok sayıda strateji/ayar denemenin yarattığı "şanslı kazanan" riskini ölçer.

PBO (Probability of Backtest Overfitting), Bailey, Borwein, López de Prado & Zhu (2015), CSCV yöntemi:
  Günlük getiriler S eşit bloğa bölünür. Blokların her yarı-yarı ayrımında, ilk yarıda en iyi Sharpe'ı
  veren ayar seçilir ve ikinci yarıdaki sırasına bakılır. Seçilen ayarın ikinci yarıda ortancanın
  altında kaldığı ayrımların oranı = PBO. %50 civarı: seçim yazı-turadan farksız.

Deflated Sharpe Ratio, Bailey & López de Prado (2014):
  Kazananın Sharpe'ını, deneme sayısı ve getirilerin çarpıklık/basıklığına göre düzeltir.
  DSR = gerçek Sharpe'ın 0'dan büyük olma olasılığı (deneme sayısı hesaba katılarak). %95 üstü güçlü kanıt.
"""
from __future__ import annotations

import itertools
import math
import statistics
from statistics import NormalDist

N01 = NormalDist()


def _block_stats(r, S):
    T = len(r)
    size = T // S
    out = []
    for b in range(S):
        seg = r[b * size:(b + 1) * size] if b < S - 1 else r[b * size:]
        out.append((len(seg), sum(seg), sum(x * x for x in seg)))
    return out


def _sharpe_from(stats, blocks):
    n = s = q = 0.0
    for b in blocks:
        bn, bs, bq = stats[b]
        n += bn; s += bs; q += bq
    if n < 2:
        return 0.0
    m = s / n
    var = q / n - m * m
    return m / math.sqrt(var) if var > 1e-18 else 0.0


def pbo(series, S=16):
    """series: {ad: [günlük getiri]} (hepsi aynı uzunlukta). PBO ve ayrım sayısı döner."""
    names = list(series)
    if len(names) < 2:
        return None
    T = min(len(v) for v in series.values())
    if T < S * 5:
        return None
    stats = {k: _block_stats(series[k][:T], S) for k in names}
    N = len(names)
    below = total = 0
    logits = []
    for is_b in itertools.combinations(range(S), S // 2):
        if 0 not in is_b:          # simetri: her ayrımı bir kez say
            continue
        oos_b = [b for b in range(S) if b not in is_b]
        is_sr = [(_sharpe_from(stats[k], is_b), k) for k in names]
        best = max(is_sr)[1]
        oos = sorted(_sharpe_from(stats[k], oos_b) for k in names)
        val = _sharpe_from(stats[best], oos_b)
        rank = sum(1 for x in oos if x <= val)          # 1..N
        w = rank / (N + 1)
        lg = math.log(w / (1 - w))
        logits.append(lg)
        below += lg <= 0
        total += 1
    return {"pbo": round(below / total, 3), "ayrim": total, "deneme": N,
            "logit_ortanca": round(statistics.median(logits), 3)}


def deflated_sharpe(r_best, all_sharpes, n_trials=None):
    """r_best: kazananın günlük getirileri; all_sharpes: tüm denemelerin günlük (yıllıklanmamış) Sharpe'ları."""
    T = len(r_best)
    if T < 30 or len(all_sharpes) < 2:
        return None
    m = statistics.mean(r_best)
    sd = statistics.pstdev(r_best)
    if sd == 0:
        return None
    sr = m / sd
    skew = sum((x - m) ** 3 for x in r_best) / T / sd ** 3
    kurt = sum((x - m) ** 4 for x in r_best) / T / sd ** 4
    N = n_trials or len(all_sharpes)
    v = statistics.pvariance(all_sharpes)
    g = 0.5772156649
    sr0 = math.sqrt(v) * ((1 - g) * N01.inv_cdf(1 - 1 / N) + g * N01.inv_cdf(1 - 1 / (N * math.e)))
    den = 1 - skew * sr + (kurt - 1) / 4 * sr * sr
    if den <= 0:
        return None
    z = (sr - sr0) * math.sqrt(T - 1) / math.sqrt(den)
    return {"dsr": round(N01.cdf(z), 3), "sharpe_yillik": round(sr * math.sqrt(365), 2),
            "beklenen_en_iyi_sans_sharpe_yillik": round(sr0 * math.sqrt(365), 2), "deneme": N}
