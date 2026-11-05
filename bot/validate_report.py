"""DOGRULAMA.md üretimi (Türkçe, sade). Bütün sayılar dogrulama.json'dan gelir."""
from __future__ import annotations


def _p(x):
    return "-" if x is None else f"%{x * 100:.1f}" if isinstance(x, float) and abs(x) <= 1.5 else str(x)


def _row(name, m):
    return (f"| {name} | %{m.get('getiri_pct')} | %{m.get('cagr_pct')} | {m.get('sharpe')} | {m.get('sortino')} | "
            f"%{m.get('max_dusus_pct')} | {m.get('calmar')} |")


def markdown(r):
    L = ["# ✅ Doğrulama Raporu — Kırılım Ansamblı (4s)", "",
         f"Ön kayıt: `{r['on_kayit']}` (testlerden önce GitHub'a gönderildi, etiket `on-kayit-v1`). "
         f"Rastgele tohum {r['tohum']}. Oluşturma: {r['olusturma']}. Süre: {r.get('sure_sn')} sn.", "",
         f"Veri: {r['veri']}", ""]

    # --- eşikler
    L += ["## 1. Ön kayıtlı geçiş şartları", "",
          "| # | Şart | Sonuç | Eşik | Durum |", "|---|---|---|---|---|"]
    for e in r["esikler"]:
        res = e["sonuc"]
        if isinstance(res, float) and res <= 1:
            res = f"%{res * 100:.1f}"
        L.append(f"| {e['no']} | {e['sart']} | {res} | {e['esik']} | {'✅' if e['gecti'] else '❌'} |")
    passed = sum(e["gecti"] for e in r["esikler"][:6])
    L += ["", f"**Geçmiş veriye dayalı 6 şarttan {passed} tanesi sağlandı.** Şart 7–8 (12 ay canlı test, "
              "operasyonel testler) zaman gerektirir. Bütün şartlar sağlanmadan gerçek paraya geçilmez.", ""]

    # --- ana dönem
    a = r["ana_donem"]
    L += [f"## 2. Ana dönem ({a['olcum']}) — ansambl ve benchmark'lar", "",
          "Nakit getirisi %0. Hepsine aynı komisyon (%0,1) ve kayma (%0,05) uygulandı.", "",
          "| Portföy | Getiri | Yıllık | Sharpe | Sortino | En büyük düşüş | Calmar |", "|---|---|---|---|---|---|---|"]
    names = {"B100": "%100 BTC al-tut", "VM": "Oynaklık eşleştirilmiş BTC (VM)",
             "WM": "Ağırlık eşleştirilmiş BTC/nakit (WM, aylık)", "S25": "%25 BTC sabit", "S50": "%50 BTC sabit",
             "S75": "%75 BTC sabit", "M25": "%25 BTC aylık dengeli", "M50": "%50 BTC aylık dengeli",
             "M75": "%75 BTC aylık dengeli"}
    for k, m in a["tablo"].items():
        L.append(_row(names.get(k, k), m))
    e = a["tablo"]["ENS (vt %40)"]
    L += ["", f"Ansambl: {e.get('islem')} işlem, zamanın %{e.get('piyasada_pct')}'inde pozisyonda, "
              f"**ortalama BTC sermaye ağırlığı {e.get('ort_btc_agirligi')}** (pozisyonda kalma süresiyle karıştırılmamalı). "
              f"VM'nin ortalama BTC ağırlığı {a['vm_ortalama_agirlik']}. "
              f"WM, ortalama ağırlığı dönem sonunda bilindiği için geriye dönük (ex-post) bir kıyastır.", ""]

    sd = r["sharpe_duzeltme"]
    nw = sd["newey_west"]
    L += ["## 3. Sharpe düzeltmeleri", "",
          f"- Standart Sharpe (günlük, ×√365): **{sd['standart']}** (BTC: {sd['btc_standart']})",
          f"- Otokorelasyon düzeltmeli Sharpe (Lo 2002, ilk 10 gecikme): **{sd['lo_2002']}**; "
          f"otokorelasyonlar 1–10: {sd['otokorelasyon_1_10']}",
          f"- Newey-West (Bartlett, gecikme {nw['gecikme']}): günlük ortalama getiri {nw['ortalama_gunluk']}, "
          f"HAC standart hata {nw['hac_std_hata']} (naif {nw['naif_std_hata']}), t = {nw['t']}, "
          f"%95 aralık {nw['guven_95']}",
          f"- PSR (Sharpe > 0 olasılığı, çarpıklık/basıklık düzeltmeli; seçim riski HARİÇ): **{_p(sd['psr_gt_0'])}**", ""]

    L += ["## 4. Maliyet ve oynaklık hedefi", "",
          f"- 2× maliyetle ana dönem: getiri %{r['maliyet_2x']['getiri_pct']}, Sharpe {r['maliyet_2x']['sharpe']}, "
          f"düşüş %{r['maliyet_2x']['max_dusus_pct']}", "",
          "| Hedef | Getiri | Yıllık | Sharpe | Düşüş | Calmar | İşlem | Ort. BTC ağırlığı |", "|---|---|---|---|---|---|---|---|"]
    for k, m in r["vol_hedefleri_gercek"].items():
        L.append(f"| {k} | %{m['getiri_pct']} | %{m['cagr_pct']} | {m['sharpe']} | %{m['max_dusus_pct']} | "
                 f"{m['calmar']} | {m['islem']} | {m['ort_btc_agirligi']} |")
    L.append("")

    gd = r.get("gecikmeli_dolum", {})
    if "hata" in gd:
        L += ["## 5. Gecikmeli dolum", "", f"Hesaplanamadı: {gd['hata']}", ""]
    else:
        L += ["## 5. Gecikmeli dolum (sinyal sonrası +15/+30/+60 dk)", "",
              "Girişler ve sinyalle çıkışlar gecikmeli fiyattan; stoplar borsada bekleyen emir sayıldığı için gecikmesiz. "
              "Kayma bir kez uygulandı; fiyat farkı ayrı kalem.", "",
              "| Kaynak | Gecikme | Getiri | Sharpe | Düşüş | Calmar | Dolum | Ort. aleyhte fark (bp) | Eksik veri |",
              "|---|---|---|---|---|---|---|---|---|"]
        for src in ("1dk_veri", "15dk_kontrol"):
            for k, m in gd.get(src, {}).items():
                L.append(f"| {src} | {k} | %{m['getiri_pct']} | {m['sharpe']} | %{m['max_dusus_pct']} | {m['calmar']} | "
                         f"{m['dolum']} | {m['ort_fark_bp_aleyhte']} | {m['eksik_veri']} |")
        L.append("")

    # --- bootstrap A
    L += ["## 6. Bootstrap A — strateji getirisi (destekleyici, karar ölçütü değil)", "",
          "Gerçekleşmiş günlük getirilerin sırası, 10.000 örnekle karıştırıldı (ansambl ve benchmark'lar aynı günlerle). "
          "Stratejinin kararlarını yeniden üretmez.", "",
          "| Blok | P(Sharpe > B100) | P(Calmar > VM) | P(Sharpe > WM) | P(MDD < B100) | Sharpe ortanca [%5–%95] | P(negatif getiri) |",
          "|---|---|---|---|---|---|---|"]
    for b, x in r["bootstrap_A"].items():
        s = x["ENS_sharpe"]
        L.append(f"| {b} | {_p(x['P_sharpe_gt_B100']['olasilik'])} | {_p(x['P_calmar_gt_VM']['olasilik'])} | "
                 f"{_p(x['P_sharpe_gt_WM']['olasilik'])} | {_p(x['P_mdd_lt_B100']['olasilik'])} | "
                 f"{s.get('ortanca')} [{s.get('p5')} – {s.get('p95')}] | {_p(x['P_negatif_getiri']['olasilik'])} |")
    L.append("")

    # --- bootstrap B
    B = r["bootstrap_B"]
    L += ["## 7. Bootstrap B — sentetik fiyat yolları (KARAR ölçütü)", "",
          "4 saatlik mumlar (açılış/en yüksek/en düşük/kapanış birlikte) blok blok yeniden örneklendi; ansambl ve "
          "benchmark'lar her yolda baştan çalıştırıldı.", "",
          "| Senaryo | Yol | P1 Sharpe>B100 | P2 Calmar>VM | P3 Sharpe>WM | P4 MDD<B100 | Ans. yıllık ortanca [%5–%95] | Ans. düşüş ortanca [%5–%95] |",
          "|---|---|---|---|---|---|---|---|"]
    for k, x in B.items():
        for part in ("tum", "ilk_1000"):
            t = x[part]
            c, m = t["ENS_cagr"], t["ENS_mdd"]
            L.append(f"| {k} ({'tümü' if part == 'tum' else 'ilk 1000'}) | {x['n'] if part == 'tum' else min(1000, x['n'])} | "
                     f"{_p(t['P1_sharpe_gt_B100']['olasilik'])} ±{t['P1_sharpe_gt_B100']['mc_hata']:.3f} | "
                     f"{_p(t['P2_calmar_gt_VM']['olasilik'])} | {_p(t['P3_sharpe_gt_WM']['olasilik'])} | "
                     f"{_p(t['P4_mdd_lt_B100']['olasilik'])} | %{c.get('ortanca')} [{c.get('p5')} – {c.get('p95')}] | "
                     f"%{m.get('ortanca')} [{m.get('p5')} – {m.get('p95')}] |")
    k0 = B.get("vt40_blok360", {}).get("kontrol", {})
    real = r.get("bootstrap_B_gercek_yol", {})
    L += ["", "**Sentetik yolların gerçekle karşılaştırması (ana senaryo, blok 360):**", "",
          f"- Tutarsız mum (en yüksek < açılış/kapanış vb.): {k0.get('tutarsiz_mum')}",
          f"- Yol başına ortalama blok sayısı: {k0.get('ortalama_blok_sayisi')}",
          f"- Açılış boşluğu (mutlak ortalama): blok sınırlarında {k0.get('blok_siniri_acilis_boslugu_ort')}, "
          f"tüm mumlarda {k0.get('tum_acilis_boslugu_ort')}, gerçek veride {real.get('gap_abs_mean')}",
          f"- Oynaklık kümelenmesi (|getiri| otokorelasyonu, gecikme 1–10 ort.): sentetik {k0.get('acf_abs')}, gerçek {real.get('acf_abs')}",
          f"- Trend uzunluğu (20 günlük getiri işaretinin koşu uzunluğu, gün): sentetik {k0.get('trend_run')}, gerçek {real.get('trend_run')}",
          f"- BTC en büyük düşüş (%): sentetik {k0.get('btc_mdd')}, gerçek {real.get('btc_mdd')}",
          "- Sınırlama: sentetik yollar sadece bu 3 yılın mumlarından üretilir; hiç yaşanmamış rejimleri temsil etmez, "
          "blok birleşimleri yapay geçişler yaratabilir.", ""]

    # --- rejim
    L += ["## 8. Günlük rejim analizi", "", "Her günün rejimi, sadece önceki günün verisiyle belirlendi.", ""]
    for axis, title in (("yon", "Yön"), ("oynaklik", "Oynaklık")):
        L += [f"**{title}**", "", "| Rejim | Gün | Ayrı dönem | Ansambl log getiri | BTC log getiri | Ans. Sharpe | BTC Sharpe | Ans. düşüş | BTC düşüş | İşlem açılışı | Piyasada | Ort. ağırlık |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for g, x in r["rejim"].get(axis, {}).items():
            L.append(f"| {g} | {x['gun']} | {x['ayri_donem']} | %{x['ens_log_getiri_pct']} | %{x['btc_log_getiri_pct']} | "
                     f"{x['ens_sharpe']} | {x['btc_sharpe']} | %{x['ens_mdd_pct']} | %{x['btc_mdd_pct']} | "
                     f"{x['islem_acilisi']} | %{x['piyasada_pct']} | {x['ort_btc_agirligi']} |")
        L.append("")

    st = r["stres_2018_2022"]
    L += [f"## 9. 2018–2022 tarihsel stres testi ({st['olcum']})", "", st["not"], "",
          "| Portföy | Getiri | Yıllık | Sharpe | Sortino | En büyük düşüş | Calmar |", "|---|---|---|---|---|---|---|"]
    for k in ("ENS", "B100", "VM", "WM", "M50"):
        L.append(_row(names.get(k, "Ansambl (vt %40)" if k == "ENS" else k), st[k]))
    L += ["", f"Ansambl: {st['ENS']['islem']} işlem, en düşük özsermaye başlangıcın %{st['ENS']['en_dusuk_ozsermaye_pct']}'i, "
              f"ort. BTC ağırlığı {st['ENS']['ort_btc_agirligi']}.", ""]

    ez = r.get("ezber", {})
    L += ["## 10. Ezber riski — etkin deneme sayısı, DSR, PBO", ""]
    if "hata" in ez:
        L += [f"Hesaplanamadı: {ez['hata']}", ""]
    else:
        ne = ez["etkin_boyut"]
        L += [f"- Seri sayısı {ne['seri']} (değişken {ne['degisken_seri']}, hiç işlem yapmayan {ne['sabit_seri']}); "
              f"N_toplam = {ez['n_toplam']} (30 coin ayarları dahil). {ez['not']}",
              f"- Etkin boyut tahmini — **özdeğer katılım oranı (ana): {ne['N_eff_katilim_orani']}**, ortalama korelasyon "
              f"({ne['ort_korelasyon']}): {ne['N_eff_ort_korelasyon']}, kümeleme (ρ>0,7): {ne['N_eff_kume']}",
              "", "| Varsayım | DSR (ansambl, seçim riski dahil) | Şansla beklenen en iyi Sharpe |", "|---|---|---|"]
        for k, d in ez["dsr"].items():
            if d:
                L.append(f"| {k} | {_p(d['dsr'])} | {d['beklenen_en_iyi_sans_sharpe_yillik']} |")
        pb = ez.get("pbo_tum_denemeler") or {}
        L += ["", f"- PBO (bütün denemeler, CSCV 16 blok): **{_p(pb.get('pbo'))}** ({pb.get('deneme')} seri)", ""]

    tt = r.get("tasima_testi", {})
    L += ["## 11. Pozisyon taşıma testi (ayar seçen stratejiler, walk-forward)", "",
          "A = pencere sonunda kapat; B = pozisyonu açıldığı ayarlarla taşı. Ansambl ayar seçmediği için tek kesintisiz simülasyondur.", "",
          "| Strateji | A getiri | B getiri | A Sharpe | B Sharpe | A düşüş | B düşüş | A işlem | B işlem |", "|---|---|---|---|---|---|---|---|---|"]
    for k, x in tt.get("sonuc", {}).items():
        if "hata" in x:
            L.append(f"| {k} | hata: {x['hata']} |||||||| ")
            continue
        a_, b_ = x["A_kapat"], x["B_tasi"]
        L.append(f"| {k} | %{a_['getiri_pct']} | %{b_['getiri_pct']} | {a_['sharpe']} | {b_['sharpe']} | "
                 f"%{a_['max_dusus_pct']} | %{b_['max_dusus_pct']} | {a_['islem']} | {b_['islem']} |")
    L += ["", "_Bu rapor otomatik üretildi; yorum ve yanıtlar ayrıca yazılır. Sanal test; yatırım tavsiyesi değildir._", ""]
    return "\n".join(L)
