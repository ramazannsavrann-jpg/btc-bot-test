"""
ÖN KAYIT DIŞI — KEŞİFSEL ANALİZ, KARAR DEĞİŞTİRMEZ.

v2/v2.1 sonucuna ek duyarlılık analizleri (kullanıcı ve ChatGPT denetimi, 2026-11-05):
  1) Çıkış mutabakatı (stop + orta nokta + hedef = toplam) ve hedefle kapanan işlemler
  2) Hedefsiz ENS: tüm portföy baştan simüle edilir (docs/ON_KAYIT_v1_DUZELTME_1.md)
  3) Kötümser stop stres testi (stop mumun en düşüğünden dolar) + 1 dakikalık veriyle stop doğrulaması
  4) 2018–2020 (1. ayı dönemi) hariç sonuçlar
  5) Parametre varyantları: 15/30/45, 25/50/75, 30/60/90 gün (+ hedefsiz) — en iyisi SEÇİLMEZ
  6) Yeni denemeler dahil DSR (N = 266 + 4 = 270)
Çalıştırma: python -m bot.v2_ek   (GitHub Actions: .github/workflows/v2_ek.yml)
Ön kayıt belgeleri, motor dosyaları, onkayit_v2.py ve canlı botlar değiştirilmez; yalnızca çağrılır.
Her çalıştırma results/v2_ek/<zaman>_<çalıştırma>/ klasörüne yazılır, önceki sonuçların üzerine yazılmaz.
"""
from __future__ import annotations

import collections
import hashlib
import io
import json
import math
import os
import platform
import subprocess
import sys
import time
import zipfile
from datetime import datetime, timezone

import numpy as np

from . import data as D, ensemble as E, external, onkayit_v2 as O, research, strategy as S, validate as V

UTC = timezone.utc
H, DAY, BAR4 = O.H, O.DAY, O.BAR4
LABEL = "ÖN KAYIT DIŞI — KEŞİFSEL ANALİZ, KARAR DEĞİŞTİRMEZ"
DOCS = {**O.DOCS,
        "docs/ON_KAYIT_v1.md": "e6b23406a5397c7d4d77004b5d52d9e79a8ce0cf89038288e5ae9411d3745b2f",
        "docs/ON_KAYIT_v1_DUZELTME_1.md": "3b6bfb4843ec28c2ff53ef0190f96e4054bf05233f88804a29fb4a9bf3c10647"}
BASE_RUN = "results/v2/20261105T124818Z_42030216089-1/sonuc.json"     # v2 ilk çalıştırması (referans)
STOP_REASONS = ("stop", "kâr koruma stopu")
VARIANTS = {                                   # ENS'ye göre değişen parametreler
    "Hedefsiz": {"tp_atr": 1e12},
    "15/30/45 gün": {"subs": [{"bo_len": 90}, {"bo_len": 180}, {"bo_len": 270}]},
    "25/50/75 gün": {"subs": [{"bo_len": 150}, {"bo_len": 300}, {"bo_len": 450}]},
    "30/60/90 gün": {"subs": [{"bo_len": 180}, {"bo_len": 360}, {"bo_len": 540}]},
}
N_TOTAL = O.N_TOTAL + len(VARIANTS)            # 270
LOG: list[str] = []


def log(*a):
    s = " ".join(str(x) for x in a)
    LOG.append(s)
    print(s, flush=True)


# =================================================================== ENS simülasyonu (varyant / kötümser stop)
_CUR = {"low": None, "on": False}
_ORIG_CLOSE = S._close_position


def _pess_close(state, ts, px, reason):
    """Kötümser stres: stop çıkışları o mumun en düşük fiyatından (kayma bunun üstüne yine uygulanır)."""
    if _CUR["on"] and reason in STOP_REASONS and _CUR["low"] is not None:
        px = min(px, _CUR["low"])
    return _ORIG_CLOSE(state, ts, px, reason)


def ens_params(fee, slip, over=None):
    p = dict(V.ens_params(O.VOL_TARGET), fee=fee, slip=slip)
    p.update(over or {})
    return p


def sim_ens(c4, p, pessimistic=False):
    ind = E.indicators(c4, p)
    st = E.new_state(100.0, p)
    out = {"days": [], "eq": [], "w": [], "expo": [], "stops": {}}
    S._close_position = _pess_close
    _CUR["on"] = pessimistic
    try:
        for i, c in enumerate(c4):
            _CUR["low"] = c[3]
            E.process_bar(st, c4, ind, i)
            for s in st["subs"]:
                pos = s["position"]
                if pos:
                    out["stops"][(pos["entry_ts"], pos["qty"])] = pos["stop"]
            if (c[0] + BAR4) % DAY != 0:
                continue
            e = research.exit_value(st, c[4])
            out["days"].append((c[0] + BAR4) // DAY - 1)
            out["eq"].append(e)
            out["w"].append(st["qty"] * c[4] / e if e > 0 else 0.0)
            out["expo"].append(st["qty"] > 0)
    finally:
        S._close_position = _ORIG_CLOSE
        _CUR["on"] = False
    out["trades"] = st["trades"]
    out["subs_bo_len"] = [x.get("bo_len") for x in E.sub_params(p)]
    out["tp_atr"] = E.sub_params(p)[0].get("tp_atr")
    return out


def as_run(base, ens):
    """v2 değerlendirme fonksiyonlarının beklediği biçim: VM-A/VM-B/B100 temel çalıştırmadan, ENS varyanttan."""
    r = dict(base)
    r["eq"] = dict(base["eq"], ENS=ens["eq"])
    r["w"] = dict(base["w"], ENS=ens["w"])
    r["expo"] = dict(base["expo"], ENS=ens["expo"])
    r["ens_trades"] = ens["trades"]
    return r


def stats(run, key, d0, d1):
    m = O.period_metrics(run, key, d0, d1)
    if m is None:
        return None
    ser = O.day_series(run, key)
    ds = sorted(ser)
    base = O._val_at(ser, ds, d0 - 1)[1]
    v = np.array([base] + [ser[d] for d in ds if d0 <= d < d1])
    r = v[1:] / v[:-1] - 1
    m["sharpe"] = float(r.mean() / r.std() * math.sqrt(365)) if r.std() > 0 else None
    m["calmar"] = m["cagr"] / m["mdd"] if m["cagr"] is not None and m["mdd"] > 0 else None
    return m


# =================================================================== 1 dakikalık veri (stop doğrulaması)
def load_1m_month(ym):
    url = f"{O.ARCH}/monthly/klines/BTCUSDT/1m/BTCUSDT-1m-{ym}.zip"
    raw = D._get(url, 120)
    sha = hashlib.sha256(raw).hexdigest()
    try:
        ok = D._get(url + ".CHECKSUM", 30).decode().split()[0].strip().lower() == sha
    except Exception:  # noqa: BLE001
        ok = None
    z = zipfile.ZipFile(io.BytesIO(raw))
    rows = [ln.split(",") for ln in z.read(z.namelist()[0]).decode().splitlines() if ln.split(",")[0].strip().isdigit()]
    return D._binance_rows(rows), {"dosya": url.rsplit("/", 1)[1], "sha256": sha, "checksum_ok": ok, "satir": len(rows)}


def stop_check_1m(trades, stops, c4):
    bar = {c[0]: c for c in c4}
    ev = [(k, t) for k, t in enumerate(trades) if t["reason"] in STOP_REASONS]
    months = sorted({datetime.fromtimestamp(t["exit_ts"] / 1000, UTC).strftime("%Y-%m") for _, t in ev})
    m1, files, errs = {}, [], []
    for ym in months:
        try:
            rows, info = load_1m_month(ym)
            files.append(info)
            for r in rows:
                m1[r[0]] = r
        except Exception as e:  # noqa: BLE001
            errs.append(f"{ym}: {e}")
    out = []
    for k, t in ev:
        stp = stops.get((t["entry_ts"], t["qty"]))
        c = bar.get(t["exit_ts"])
        row = {"kimlik": f"ENS-1x-{k}", "cikis_mumu": O.iso(t["exit_ts"]), "stop": stp,
               "ayni_mumda_giris": t["entry_ts"] == t["exit_ts"]}
        if stp is None or c is None:
            row["durum"] = "stop seviyesi veya mum bulunamadı"
            out.append(row)
            continue
        eng = min(c[1], stp)
        mins = [m1[x] for x in range(t["exit_ts"], t["exit_ts"] + BAR4, 60_000) if x in m1]
        row.update({"motor_dolum": eng, "kotumser_dolum": min(c[1], c[3]), "mum_acilis": c[1], "mum_dip": c[3],
                    "dakika_sayisi": len(mins)})
        hit = next((m for m in mins if m[3] <= stp), None)
        if hit is None:
            row["durum"] = "1 dk veride stop'a değen dakika yok" if mins else "1 dk veri yok"
        else:
            f1 = min(hit[1], stp)
            row.update({"ilk_degen_dakika": O.iso(hit[0]) + f" +{(hit[0] - t['exit_ts']) // 60_000} dk",
                        "dakika_dolum": f1, "fark_bp_motor": (f1 / eng - 1) * 1e4,
                        "fark_bp_kotumser": (row["kotumser_dolum"] / eng - 1) * 1e4,
                        "acilista_bosluk": c[1] <= stp,
                        "dip_tutarli": abs(min(m[3] for m in mins) - c[3]) < 1e-9 if len(mins) == 240 else None,
                        "durum": "doğrulandı"})
        out.append(row)
    return out, files, errs


# =================================================================== yardımcılar
def ep_summary(run, eps):
    """Her dönem için ENS ve VM-A ayı MDD'leri, koruma şartı ve toparlanma (v2 §5–6 ölçümleri)."""
    res = []
    for e in eps:
        t = O.episode_table(run, e)
        res.append({"t0": O.dstr(e["t0"]), "t1": O.dstr(e["t1"]), "t2": O.dstr(e["t2"]),
                    "ENS_ayi_mdd": t["ENS"]["ayi_mdd"], "VM-A_ayi_mdd": t["VM-A"]["ayi_mdd"],
                    "fark_puan": t["koruma"]["fark_puan"], "goreli": t["koruma"]["goreli"],
                    "koruma_gecti": t["koruma"]["gecti"],
                    "ENS_toparlanma": t["ENS"]["toparlanma_getiri"], "VM-A_toparlanma": t["VM-A"]["toparlanma_getiri"],
                    "ENS_islem": t["ENS"].get("islem")})
    return res


def returns_main(run, key):
    ser = O.day_series(run, key)
    ds = sorted(ser)
    base = O._val_at(ser, ds, V.MAIN_START // DAY - 1)[1]
    v = [base] + [ser[d] for d in ds if V.MAIN_START // DAY <= d < V.MAIN_END // DAY]
    return [v[i + 1] / v[i] - 1 for i in range(len(v) - 1)]


# =================================================================== rapor
P = O.pct
PP = O.pp


def f2(x, nd=2):
    return "—" if x is None else f"{x:.{nd}f}"


def markdown(res):
    L = [f"# {LABEL}", "",
         "> Bu analizler v2/v2.1 ön kayıt sonucunu **değiştirmez**. Varyantlar arasından en iyi parametre **seçilmez** ve "
         "ana stratejiye dönüştürülmez. Yeni varyantlar deneme sayısına eklenmiştir "
         f"(N = {O.N_TOTAL} + {len(VARIANTS)} = {N_TOTAL}). Bütün sonuçlar spot BTCUSDT içindir; futures için geçerli değildir.", ""]
    i = res["calistirma"]
    L += ["## Çalıştırma bilgisi", "",
          f"- Zaman {i['zaman']} · çalıştırma {i['calistirma_id']} · commit `{i['commit']}` · Python {i['python']} · numpy {i['numpy']}",
          "- Belgeler (SHA-256): " + ", ".join(f"`{k}` {v[:12]}…" for k, v in i["belge_ozetleri"].items()),
          f"- Veri: {res['veri']['mum_1s']} adet 1s mum ({res['veri']['ilk']} → {res['veri']['son']}), "
          f"{res['veri']['dosya_sayisi']} dosya, CHECKSUM doğrulanan {res['veri']['checksum_ok']}, "
          f"veri özeti `{res['veri']['veri_sha256'][:16]}…` (tam dosya listesi ve SHA-256'lar JSON'da)", ""]
    t = res["testler"]
    ok = sum(1 for r in t if r["gecti"] is True)
    L += ["## 1. Doğrulama testleri", "", f"**{ok}/{len(t)} test geçti.**"
          + ("" if res["kritik_testler_gecti"] else " **Kritik test kaldı: analiz sonuçları yayınlanmadı.**"), "",
          "| # | Test | Sonuç | Ayrıntı |", "|---|---|---|---|"]
    for k, r in enumerate(t, 1):
        L.append(f"| {k} | {r['test']} | {O.yesno(r['gecti'])} | {r['ayrinti']} |")
    L.append("")
    if not res["kritik_testler_gecti"]:
        return "\n".join(L)

    m = res["mutabakat"]
    L += ["## 2. Çıkış mutabakatı (ENS temel, 1×, tüm veri)", "", "| Çıkış sebebi | Sayı |", "|---|---|"]
    L += [f"| {k} | {v} |" for k, v in m["sebepler"].items()]
    L += [f"| **Toplam** | **{m['toplam']}** (işlem listesi: {m['islem_sayisi']}) |", "",
          "Hedefle kapanan işlemler (kimlik = v2 ilk çalıştırmasındaki ve bu çalıştırmadaki işlem sırası):", "",
          "| Kimlik | Giriş | Çıkış | Net kâr ($) | Kâr % |", "|---|---|---|---|---|"]
    for r in m["hedef_islemleri"]:
        L.append(f"| {r['kimlik']} | {r['giris']} | {r['cikis']} | {r['pnl']:.2f} | {r['pnl_pct']:.1f} |")
    L += ["", f"Bu işlemlerin net kâr toplamı {m['hedef_pnl']:.1f} $; tüm işlemlerin {m['toplam_pnl']:.1f} $. "
          "Gerçek etki için aşağıdaki baştan simülasyona bakın.", ""]

    def period_table(title, rows):
        out = [title, "", "| Maliyet | Strateji | Getiri | CAGR | MDD | Sharpe | Calmar | İşlem |", "|---|---|---|---|---|---|---|---|"]
        for r in rows:
            s = r["m"]
            out.append(f"| {r['lvl']} | {r['ad']} | {P(s['getiri'])} | {P(s['cagr'], 2)} | {P(s['mdd'])} | "
                       f"{f2(s['sharpe'])} | {f2(s['calmar'])} | {r.get('islem', '—')} |")
        return out + [""]

    def ep_table(rows_by_name):
        out = ["| Strateji | Maliyet | Dönem (zirve → dip) | ENS ayı MDD | VM-A ayı MDD | Avantaj | Göreli | Koruma şartı | ENS toparlanma | VM-A toparlanma |",
               "|---|---|---|---|---|---|---|---|---|---|"]
        for name, by in rows_by_name.items():
            for lvl, eps in by.items():
                for e in eps:
                    out.append(f"| {name} | {lvl} | {e['t0']} → {e['t1']} | {P(e['ENS_ayi_mdd'])} | {P(e['VM-A_ayi_mdd'])} | "
                               f"{PP(e['fark_puan'])} | {P(e['goreli'])} | {O.yesno(e['koruma_gecti'])} | "
                               f"{P(e['ENS_toparlanma'])} | {P(e['VM-A_toparlanma'])} |")
        return out + [""]

    v = res["varyantlar"]
    L += ["## 3. Hedefsiz ENS (tüm portföy baştan simüle edildi)", ""]
    L += period_table("Tüm ölçüm dönemi (2017-12-01 → 2026-10-31):",
                      [r for r in v["donem"] if r["ad"] in ("ENS (temel)", "Hedefsiz", "VM-A")])
    L += ep_table({k: v["donemler"][k] for k in ("ENS (temel)", "Hedefsiz")})
    L += [f"v2 kuralı bilgi amaçlı uygulanırsa (hedefsiz): **{v['kural']['Hedefsiz']}**", ""]

    k = res["kotumser"]
    L += ["## 4. Kötümser stop stres testi ve 1 dakikalık doğrulama", "",
          "**Kötümser stop gerçekçi bir dolum modeli değildir; aşırı kötümser bir stres testidir.** "
          "Her stop çıkışı o 4 saatlik mumun en düşük fiyatından (üstüne kayma ve komisyon) doldurulur.", ""]
    L += period_table("Tüm ölçüm dönemi:", k["donem"])
    L += ep_table({"Kötümser stop": k["donemler"]})
    L += [f"v2 kuralı bilgi amaçlı uygulanırsa (kötümser stop): **{k['kural']}**", "",
          "### 4.2 Stop çıkışlarının 1 dakikalık veriyle kontrolü", "",
          "1 dakikalık veri, stop'un 4 saatlik mum içinde ilk hangi dakikada tetiklendiğini gösterir. Ancak dakika içindeki "
          "sırayı ve gerçek emir defteri dolumunu **kesin olarak kanıtlamaz**. Dakika dolumu = min(o dakikanın açılışı, stop).", "",
          "| Kimlik | Çıkış mumu | Aynı mumda giriş | Stop | Motor dolumu | İlk değen dakika | Dakika dolumu | Fark (bp) | Kötümser fark (bp) | Durum |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for r in k["dakika"]:
        L.append(f"| {r['kimlik']} | {r['cikis_mumu']} | {'evet' if r.get('ayni_mumda_giris') else 'hayır'} | "
                 f"{f2(r.get('stop'))} | {f2(r.get('motor_dolum'))} | {r.get('ilk_degen_dakika', '—')} | "
                 f"{f2(r.get('dakika_dolum'))} | {f2(r.get('fark_bp_motor'), 1)} | {f2(r.get('fark_bp_kotumser'), 1)} | {r['durum']} |")
    ks = k["dakika_ozet"]
    L += ["", f"Özet: {ks['dogrulanan']}/{ks['toplam']} stop doğrulandı; motor ile dakika dolumu arasındaki fark ortalama "
          f"{f2(ks['ort_fark_bp'], 1)} bp, en kötü {f2(ks['en_kotu_fark_bp'], 1)} bp. "
          f"Kötümser modelin ortalama farkı {f2(ks['ort_kotumser_bp'], 1)} bp."
          + (f" 1 dk veri sorunları: {k['dakika_hatalari']}" if k["dakika_hatalari"] else ""), ""]

    x = res["haric_2018_2020"]
    L += ["## 5. 2018–2020 hariç (1. ayı dönemi çıkarıldı)", "",
          f"Ölçüm {x['baslangic']} (1. dönemin toparlanma günü) → 2026-10-31. Kalan büyük ayı dönemi: {x['donem_sayisi']}. "
          + ("v2 kuralına göre n < 3 olduğu için bu kesit **zaten karar veremez**; " if x["donem_sayisi"] < 3 else "")
          + "Yalnızca hassasiyet göstergesidir, karar değiştirmez.", ""]
    L += period_table("Kesit sonuçları:", x["donem"])
    L += ep_table({k2: x["donemler"][k2] for k2 in x["donemler"]})
    L += [f"İşlem listeleri JSON'da: ENS {x['ens_islem']} işlem, VM-A {x['vma_islem']} işlem.", ""]

    L += ["## 6. Parametre varyantları (en iyisi seçilmez)", ""]
    L += period_table("Tüm ölçüm dönemi:", [r for r in v["donem"] if r["ad"] != "VM-A"])
    L += ep_table({k2: v["donemler"][k2] for k2 in v["donemler"] if k2 not in ("ENS (temel)", "Hedefsiz")})
    L += ["| Varyant | v2 kuralı bilgi amaçlı uygulanırsa |", "|---|---|"]
    L += [f"| {k2} | {s} |" for k2, s in v["kural"].items()]
    L.append("")

    d = res["dsr"]
    L += ["## 7. DSR (yeni denemeler dahil)", ""]
    if "hata" in d:
        L += [f"Hesaplanamadı: {d['hata']}", ""]
    else:
        L += [d["yontem"], "", f"Etkin boyut: {d['etkin_boyut']}", "",
              "| Strateji | " + " | ".join(d["N"]) + " |", "|---|" + "---|" * len(d["N"])]
        for name, tab in d["sonuc"].items():
            L.append(f"| {name} | " + " | ".join(f2(tab[n]['dsr'], 3) if tab.get(n) else "—" for n in d["N"]) + " |")
        L.append("")
    L += ["## 8. Notlar", ""] + [f"- {n}" for n in res["notlar"]]
    return "\n".join(L)


# =================================================================== ana akış
def main():
    t_all = time.time()
    now = datetime.now(UTC)
    now_ms = int(now.timestamp() * 1000)
    run_id = f"{os.environ.get('GITHUB_RUN_ID', 'yerel')}-{os.environ.get('GITHUB_RUN_ATTEMPT', '1')}"
    stamp = now.strftime("%Y%m%dT%H%M%SZ")
    out_dir = os.path.join("results", "v2_ek", f"{stamp}_{run_id}")
    if os.path.exists(out_dir):
        raise SystemExit(f"{out_dir} zaten var; önceki sonuçların üzerine yazılmaz.")
    commit = os.environ.get("GITHUB_SHA") or subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                                                            text=True).stdout.strip()
    res = {"etiket": LABEL, "calistirma": {"zaman": now.isoformat(timespec="seconds"), "calistirma_id": run_id,
                                          "commit": commit, "python": sys.version.split()[0], "numpy": np.__version__,
                                          "platform": platform.platform(), "belge_ozetleri": {}}, "notlar": []}
    T = O.Tests()
    ok_docs = True
    for pth, exp in DOCS.items():
        got = O.sha256_file(pth)
        res["calistirma"]["belge_ozetleri"][pth] = got
        ok_docs &= got == exp
    T.add("Ön kayıt belgeleri ve düzeltme notu değişmemiş (SHA-256)", ok_docs, f"{len(DOCS)} belge")
    O.test_engine_identity(T)

    log("Veri indiriliyor…")
    c1, files, problems, notes = O.load_1h(now_ms)
    ck_ok = sum(1 for f in files if f["checksum_ok"] is True)
    ck_bad = [f["dosya"] for f in files if f["checksum_ok"] is False]
    res["veri"] = {**O.data_stats(c1), "dosya_sayisi": len(files), "checksum_ok": ck_ok, "checksum_uyusmayan": ck_bad,
                   "sorunlar": problems, "notlar": notes, "veri_sha256": O.dataset_hash(c1), "dosyalar": files}
    T.add("Arşiv dosyaları eksiksiz ve CHECKSUM uyuşmazlığı yok", not problems and not ck_bad,
          f"{len(files)} dosya, CHECKSUM doğrulanan {ck_ok}")
    c4 = D.aggregate(c1, 4)
    if not external.FG:
        try:
            external.load_fear_greed(0)
        except Exception as e:  # noqa: BLE001
            res["notlar"].append(f"Korku-açgözlülük verisi alınamadı: {e}")

    # --- temel çalıştırmalar ve yeniden üretim
    base = {lvl: O.simulate(c4, fee, slip) for lvl, (fee, slip) in O.COSTS.items()}
    ens = {lvl: sim_ens(c4, ens_params(fee, slip)) for lvl, (fee, slip) in O.COSTS.items()}
    same = all(ens[l]["days"] == base[l]["days"] and ens[l]["eq"] == base[l]["eq"]["ENS"]
               and O.compare_trades(ens[l]["trades"], base[l]["ens_trades"])[0] for l in O.COSTS)
    T.add("Analiz simülasyonu (temel ENS) v2 hesabıyla birebir aynı", same, "günlük değer ve işlem listesi, 1× ve 2×")
    try:
        with open(BASE_RUN, encoding="utf-8") as fh:
            ref = json.load(fh)["kayitlar"]
        ok_r, det = True, []
        for lvl in O.COSTS:
            rd = ref[lvl]
            n = len(rd["gunler"])
            ok_r &= [O.dstr(x) for x in base[lvl]["days"][:n]] == rd["gunler"]
            for k2 in ("ENS", "VM-A", "VM-B"):
                ok_r &= [round(x, 6) for x in base[lvl]["eq"][k2][:n]] == rd["ozsermaye"][k2]
            tr_ref = rd["ens_islemler"]
            ok_r &= O.compare_trades(base[lvl]["ens_trades"][:len(tr_ref)], tr_ref)[0]
            for k2 in ("VM-A", "VM-B"):
                vr = rd["vm_islemler"][k2]
                ok_r &= base[lvl]["vm_trades"][k2][:len(vr)] == vr
            det.append(f"{lvl}: {n} gün, {len(tr_ref)} ENS işlemi")
        T.add("v2 ilk çalıştırması (cebadcb) işlem işlem yeniden üretildi", ok_r, "; ".join(det))
    except Exception as e:  # noqa: BLE001
        T.add("v2 ilk çalıştırması işlem işlem yeniden üretildi", None, f"hata: {e}")

    # --- mutabakat
    tr = base["1x"]["ens_trades"]
    tr_hist = [t for t in tr]
    reasons = collections.Counter(t["reason"] for t in tr_hist)
    ok_m = sum(reasons.values()) == len(tr_hist)
    T.add("Çıkış mutabakatı: sebeplerin toplamı işlem sayısına eşit", ok_m,
          ", ".join(f"{k} {v}" for k, v in reasons.items()) + f" = {sum(reasons.values())} / {len(tr_hist)}")
    res["mutabakat"] = {"sebepler": dict(reasons), "toplam": sum(reasons.values()), "islem_sayisi": len(tr_hist),
                        "hedef_islemleri": [{"kimlik": f"ENS-1x-{k}", "giris": O.iso(t["entry_ts"]),
                                             "cikis": O.iso(t["exit_ts"]), "pnl": t["pnl"], "pnl_pct": t["pnl_pct"]}
                                            for k, t in enumerate(tr_hist) if t["reason"] == "hedef"],
                        "hedef_pnl": sum(t["pnl"] for t in tr_hist if t["reason"] == "hedef"),
                        "toplam_pnl": sum(t["pnl"] for t in tr_hist)}

    # --- varyantlar (baştan simülasyon)
    var = {name: {lvl: sim_ens(c4, ens_params(fee, slip, over)) for lvl, (fee, slip) in O.COSTS.items()}
           for name, over in VARIANTS.items()}
    T.add("Hedefsiz varyantta hiç hedef çıkışı yok ve yalnızca tp_atr değişti",
          all(not any(t["reason"] == "hedef" for t in var["Hedefsiz"][l]["trades"]) for l in O.COSTS)
          and var["Hedefsiz"]["1x"]["subs_bo_len"] == ens["1x"]["subs_bo_len"],
          f"tp_atr {ens['1x']['tp_atr']} → {var['Hedefsiz']['1x']['tp_atr']:.0e}, bo_len {ens['1x']['subs_bo_len']}")
    T.add("Parametre varyantlarında kırılım uzunlukları doğru uygulandı",
          [var[n]["1x"]["subs_bo_len"] for n in list(VARIANTS)[1:]] == [[90, 180, 270], [150, 300, 450], [180, 360, 540]],
          str({n: var[n]["1x"]["subs_bo_len"] for n in list(VARIANTS)[1:]}))
    pess = {lvl: sim_ens(c4, ens_params(fee, slip), pessimistic=True) for lvl, (fee, slip) in O.COSTS.items()}
    again = sim_ens(c4, ens_params(*O.COSTS["1x"]))
    T.add("Kötümser stop yaması çalıştırmadan sonra kaldırıldı (temel sonuç değişmedi)",
          again["eq"] == ens["1x"]["eq"] and S._close_position is _ORIG_CLOSE)
    n_stop = sum(1 for t in pess["1x"]["trades"] if t["reason"] in STOP_REASONS)
    T.add("Kötümser stop modeli uygulandı (stop dolumları değişti)",
          n_stop == 0 or pess["1x"]["eq"] != ens["1x"]["eq"], f"kötümser çalıştırmada {n_stop} stop çıkışı")

    res["testler"] = T.rows
    res["kritik_testler_gecti"] = T.critical_ok
    res["notlar"] += [
        "Kötümser stop, stop çıkışlarını mumun en düşük fiyatından doldurur. Gerçekçi değil, alt sınır stres testidir.",
        "1 dakikalık veri tetiklenme dakikasını gösterir, dakika içi sırayı ve gerçek dolumu kanıtlamaz.",
        "Varyantlar keşifseldir. Hiçbiri ana stratejiye dönüştürülmez; değişiklik yeni ön kayıt ve kullanıcı onayı gerektirir.",
        "Bütün sonuçlar spot BTCUSDT; futures (funding, likidasyon, teminat) ayrı çalışma gerektirir.",
        "Hedefli ve hedefsiz farkı yalnızca tüm portföy baştan simüle edilerek ölçüldü; işlem kârlarının toplanması etki değildir.",
    ]

    if T.critical_ok:
        dc = O.daily_close(c1)
        hs = O.find_spells(dc, O.HIST_END // DAY - 1)
        eps = [s for s in hs if s["big"] and s["complete"] and s["t0"] >= O.HIST_START // DAY]
        d0, d1 = O.HIST_START // DAY, O.HIST_END // DAY
        runs_by = {"ENS (temel)": {l: base[l] for l in O.COSTS}}
        for name in VARIANTS:
            runs_by[name] = {l: as_run(base[l], var[name][l]) for l in O.COSTS}
        rows, donemler, kural = [], {}, {}
        for name, rl in runs_by.items():
            for lvl, run in rl.items():
                rows.append({"lvl": lvl, "ad": name, "m": stats(run, "ENS", d0, d1),
                             "islem": len([t for t in run["ens_trades"] if t["exit_ts"] < O.HIST_END])})
            donemler[name] = {lvl: ep_summary(run, eps) for lvl, run in rl.items()}
            kural[name] = O.evaluate(rl, eps)["sonuc"]
        for lvl in O.COSTS:
            rows.append({"lvl": lvl, "ad": "VM-A", "m": stats(base[lvl], "VM-A", d0, d1),
                         "islem": len([t for t in base[lvl]["vm_trades"]["VM-A"] if t["ts"] < O.HIST_END])})
        res["varyantlar"] = {"donem": rows, "donemler": donemler, "kural": kural}

        prun = {l: as_run(base[l], pess[l]) for l in O.COSTS}
        dk, dk_files, dk_err = stop_check_1m(base["1x"]["ens_trades"], ens["1x"]["stops"], c4)
        okv = [r for r in dk if r.get("durum") == "doğrulandı"]
        res["kotumser"] = {
            "donem": [{"lvl": l, "ad": "ENS kötümser stop", "m": stats(prun[l], "ENS", d0, d1)} for l in O.COSTS]
                     + [{"lvl": l, "ad": "ENS (temel)", "m": stats(base[l], "ENS", d0, d1)} for l in O.COSTS],
            "donemler": {l: ep_summary(prun[l], eps) for l in O.COSTS},
            "kural": O.evaluate(prun, eps)["sonuc"],
            "dakika": dk, "dakika_dosyalari": dk_files, "dakika_hatalari": dk_err,
            "dakika_ozet": {"toplam": len(dk), "dogrulanan": len(okv),
                            "ort_fark_bp": float(np.mean([r["fark_bp_motor"] for r in okv])) if okv else None,
                            "en_kotu_fark_bp": float(min(r["fark_bp_motor"] for r in okv)) if okv else None,
                            "ort_kotumser_bp": float(np.mean([r["fark_bp_kotumser"] for r in okv])) if okv else None}}

        x0 = eps[0]["t2"] if eps else d0
        sub_eps = eps[1:]
        xrows, xdon = [], {}
        for name, rl in runs_by.items():
            for lvl, run in rl.items():
                xrows.append({"lvl": lvl, "ad": name, "m": stats(run, "ENS", x0, d1),
                              "islem": len([t for t in run["ens_trades"] if x0 * DAY <= t["entry_ts"] < O.HIST_END])})
            xdon[name] = {lvl: ep_summary(run, sub_eps) for lvl, run in rl.items()}
        for lvl in O.COSTS:
            xrows.append({"lvl": lvl, "ad": "VM-A", "m": stats(base[lvl], "VM-A", x0, d1),
                          "islem": len([t for t in base[lvl]["vm_trades"]["VM-A"] if x0 * DAY <= t["ts"] < O.HIST_END])})
        res["haric_2018_2020"] = {
            "baslangic": O.dstr(x0), "donem_sayisi": len(sub_eps), "donem": xrows, "donemler": xdon,
            "ens_islem": len([t for t in base["1x"]["ens_trades"] if x0 * DAY <= t["entry_ts"] < O.HIST_END]),
            "vma_islem": len([t for t in base["1x"]["vm_trades"]["VM-A"] if x0 * DAY <= t["ts"] < O.HIST_END]),
            "islemler": {lvl: {"ENS": [t for t in base[lvl]["ens_trades"] if x0 * DAY <= t["entry_ts"] < O.HIST_END],
                               "VM-A": [t for t in base[lvl]["vm_trades"]["VM-A"] if x0 * DAY <= t["ts"] < O.HIST_END]}
                         for lvl in O.COSTS}}

        try:
            c1m = [c for c in c1 if c[0] < V.MAIN_END]
            c4f = D.aggregate(c1m, 4)
            c4_main = [c for c in c4f if V.SIM_START - V.WARMUP_BARS * BAR4 <= c[0] < V.MAIN_END]
            v1run = V.run_ens(c4_main, V.ens_params(0.4), V.MAIN_START, V.MAIN_END)
            bm, _, _ = V.benchmarks_for(v1run, None, V.daily_closes(c4f, c4f[0][0] + 400 * DAY, V.MAIN_END))
            data = {"1h": [c for c in c1 if V.SIM_START - 30 * DAY <= c[0] < V.MAIN_END], "4h": c4_main}
            d15 = D.history_symbol("BTC", V.months_between(V.SIM_START - 30 * DAY, 0), "15m")
            d15 = [c for c in d15 if V.SIM_START - 30 * DAY <= c[0] < V.MAIN_END]
            ser = V.all_trial_returns(data, d15)
            ser["v2|VM-A"] = returns_main(base["1x"], "VM-A")
            ser["v2|VM-B"] = returns_main(base["1x"], "VM-B")
            ser["v2|VM-ref"] = [bm["VM"][i + 1] / bm["VM"][i] - 1 for i in range(len(bm["VM"]) - 1)]
            strat = {"ENS (temel)": returns_main(base["1x"], "ENS"), "VM-A": ser["v2|VM-A"]}
            for name in VARIANTS:
                r = returns_main(runs_by[name]["1x"], "ENS")
                ser[f"ek|{name}"] = r
                strat[name] = r
            T_ = min(len(x) for x in ser.values())
            ser = {k2: x[:T_] for k2, x in ser.items()}
            ne = V.n_eff_estimates(ser)
            Ns = {f"N_toplam={N_TOTAL}": N_TOTAL, "N_eff_katilim": ne["N_eff_katilim_orani"],
                  "N_eff_ort_korelasyon": ne["N_eff_ort_korelasyon"], "N_eff_kume": ne["N_eff_kume"]}
            res["dsr"] = {"yontem": "v1 ve v2 ile aynı yöntem (bot/overfit.deflated_sharpe), ölçüm 2023-11-01 → 2026-10-31; "
                                    f"deneme seti v2'nin {len(ser) - len(VARIANTS)} serisi + {len(VARIANTS)} yeni varyant.",
                          "seri_sayisi": len(ser), "etkin_boyut": ne, "N": list(Ns),
                          "sonuc": {k2: V.dsr_table(x[:T_], ser, Ns) for k2, x in strat.items()}}
        except Exception as e:  # noqa: BLE001
            res["dsr"] = {"hata": str(e)}
        res["kayitlar"] = {
            "varyant_islemleri": {n: {l: var[n][l]["trades"] for l in O.COSTS} for n in VARIANTS},
            "kotumser_islemleri": {l: pess[l]["trades"] for l in O.COSTS},
            "gunler": [O.dstr(d) for d in base["1x"]["days"]],
            "ozsermaye": {**{n: {l: [round(x, 6) for x in var[n][l]["eq"]] for l in O.COSTS} for n in VARIANTS},
                          "Kötümser stop": {l: [round(x, 6) for x in pess[l]["eq"]] for l in O.COSTS}}}
    res["sure_sn"] = round(time.time() - t_all)
    res["gunluk"] = LOG

    os.makedirs(out_dir)
    with open(os.path.join(out_dir, "sonuc.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1, default=str)
    with open(os.path.join(out_dir, "RAPOR.md"), "w", encoding="utf-8") as fh:
        fh.write(markdown(res))
    idx = os.path.join("results", "V2_EK_ANALIZ.md")
    if not os.path.exists(idx):
        with open(idx, "w", encoding="utf-8") as fh:
            fh.write(f"# {LABEL}: çalıştırmalar\n\nYalnızca sona ekleme ile büyür; her satır ayrı ve değiştirilmeyen bir çalıştırmadır.\n\n"
                     "| Zaman (UTC) | Commit | Kritik testler | Rapor |\n|---|---|---|---|\n")
    with open(idx, "a", encoding="utf-8") as fh:
        fh.write(f"| {stamp} | `{commit[:7]}` | {'geçti' if T.critical_ok else 'KALDI'} | "
                 f"[RAPOR.md](v2_ek/{stamp}_{run_id}/RAPOR.md) |\n")
    log(f"Bitti ({res['sure_sn']} sn) → {out_dir}")


if __name__ == "__main__":
    main()
