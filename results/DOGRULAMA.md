# ✅ Doğrulama Raporu — Kırılım Ansamblı (4s)

Ön kayıt: `docs/ON_KAYIT_v1.md` (testlerden önce GitHub'a gönderildi, etiket `on-kayit-v1`). Rastgele tohum 20261105. Oluşturma: 2026-11-05T10:56+00:00. Süre: 1545 sn.

Veri: {'mum_1s': 80581, 'bosluk_sayisi': 28, 'eksik_1s_mum': 127, 'ilk': '2017-08-17', 'son': '2026-10-31', 'mum_4s': 20123}

## 1. Ön kayıtlı geçiş şartları

| # | Şart | Sonuç | Eşik | Durum |
|---|---|---|---|---|
| 1 | P(Sharpe ansambl > Sharpe B100) | %38.2 | >= 0.90 | ❌ |
| 2 | P(Calmar ansambl > Calmar VM) | %49.4 | >= 0.90 | ❌ |
| 3 | P(Sharpe ansambl > Sharpe WM) | %37.5 | >= 0.90 | ❌ |
| 4 | P(MDD ansambl < MDD B100) | %97.5 | >= 0.90 | ✅ |
| 5 | 2× maliyetle toplam net getiri (%) | 72.47 | > 0 | ✅ |
| 6 | 2018–2022 MDD (%) / en düşük özsermaye (%) | 22.31 / 87.42 | MDD <= 40 ve en düşük >= 50 | ✅ |
| 7 | Canlı kâğıt test ≥ 12 ay ve ≥ 20 işlem | henüz başladı (5 Kasım 2026) | 12 ay + 20 işlem | ❌ |
| 8 | Operasyonel doğruluk testleri | kısmen (motor eşdeğerliği ve look-ahead testi geçti) | tüm senaryolar | ❌ |

**Geçmiş veriye dayalı 6 şarttan 3 tanesi sağlandı.** Şart 7–8 (12 ay canlı test, operasyonel testler) zaman gerektirir. Bütün şartlar sağlanmadan gerçek paraya geçilmez.

## 2. Ana dönem (2023-11-01 → 2026-10-31) — ansambl ve benchmark'lar

Nakit getirisi %0. Hepsine aynı komisyon (%0,1) ve kayma (%0,05) uygulandı.

| Portföy | Getiri | Yıllık | Sharpe | Sortino | En büyük düşüş | Calmar |
|---|---|---|---|---|---|---|
| ENS (vt %40) | %80.03 | %21.63 | 0.924 | 1.477 | %22.92 | 0.944 |
| %100 BTC al-tut | %123.63 | %30.74 | 0.807 | 1.224 | %52.97 | 0.58 |
| %25 BTC sabit | %30.91 | %9.38 | 0.562 | 0.828 | %28.87 | 0.325 |
| %25 BTC aylık dengeli | %30.45 | %9.26 | 0.81 | 1.229 | %15.87 | 0.583 |
| %50 BTC sabit | %61.82 | %17.38 | 0.667 | 0.996 | %41.44 | 0.42 |
| %50 BTC aylık dengeli | %62.72 | %17.6 | 0.809 | 1.227 | %29.92 | 0.588 |
| %75 BTC sabit | %92.72 | %24.42 | 0.746 | 1.123 | %48.47 | 0.504 |
| %75 BTC aylık dengeli | %94.63 | %24.83 | 0.808 | 1.225 | %42.26 | 0.588 |
| Ağırlık eşleştirilmiş BTC/nakit (WM, aylık) | %44.03 | %12.92 | 0.809 | 1.228 | %22.05 | 0.586 |
| Oynaklık eşleştirilmiş BTC (VM) | %75.74 | %20.66 | 0.85 | 1.293 | %26.52 | 0.779 |

Ansambl: 54 işlem, zamanın %54.9'inde pozisyonda, **ortalama BTC sermaye ağırlığı 0.356** (pozisyonda kalma süresiyle karıştırılmamalı). VM'nin ortalama BTC ağırlığı 0.501. WM, ortalama ağırlığı dönem sonunda bilindiği için geriye dönük (ex-post) bir kıyastır.

## 3. Sharpe düzeltmeleri

- Standart Sharpe (günlük, ×√365): **0.924** (BTC: 0.807)
- Otokorelasyon düzeltmeli Sharpe (Lo 2002, ilk 10 gecikme): **0.847**; otokorelasyonlar 1–10: [-0.052, 0.038, 0.065, 0.002, 0.036, -0.083, 0.052, -0.043, 0.061, 0.02]
- Newey-West (Bartlett, gecikme 6): günlük ortalama getiri 0.000617, HAC standart hata 0.000393 (naif 0.000386), t = 1.571, %95 aralık [-0.000153, 0.001388]
- PSR (Sharpe > 0 olasılığı, çarpıklık/basıklık düzeltmeli; seçim riski HARİÇ): **%94.8**

## 4. Maliyet ve oynaklık hedefi

- 2× maliyetle ana dönem: getiri %72.47, Sharpe 0.867, düşüş %23.93

| Hedef | Getiri | Yıllık | Sharpe | Düşüş | Calmar | İşlem | Ort. BTC ağırlığı |
|---|---|---|---|---|---|---|---|
| %20 | %41.18 | %12.17 | 0.87 | %13.64 | 0.892 | 54 | 0.204 |
| %30 | %61.76 | %17.37 | 0.887 | %19.81 | 0.877 | 54 | 0.294 |
| %40 | %80.03 | %21.63 | 0.924 | %22.92 | 0.944 | 54 | 0.356 |

## 5. Gecikmeli dolum (sinyal sonrası +15/+30/+60 dk)

Girişler ve sinyalle çıkışlar gecikmeli fiyattan; stoplar borsada bekleyen emir sayıldığı için gecikmesiz. Kayma bir kez uygulandı; fiyat farkı ayrı kalem.

| Kaynak | Gecikme | Getiri | Sharpe | Düşüş | Calmar | Dolum | Ort. aleyhte fark (bp) | Eksik veri |
|---|---|---|---|---|---|---|---|---|
| 1dk_veri | +15dk | %79.23 | 0.92 | %23.11 | 0.928 | 135 | 6.1 | 0 |
| 1dk_veri | +30dk | %79.62 | 0.922 | %22.54 | 0.955 | 136 | 6.11 | 0 |
| 1dk_veri | +60dk | %80.12 | 0.922 | %23.2 | 0.933 | 136 | 11.57 | 0 |
| 15dk_kontrol | +15dk | %79.23 | 0.92 | %23.11 | 0.928 | 135 | 6.1 | 0 |
| 15dk_kontrol | +30dk | %79.62 | 0.922 | %22.54 | 0.955 | 136 | 6.11 | 0 |
| 15dk_kontrol | +60dk | %80.12 | 0.922 | %23.2 | 0.933 | 136 | 11.57 | 0 |

## 6. Bootstrap A — strateji getirisi (destekleyici, karar ölçütü değil)

Gerçekleşmiş günlük getirilerin sırası, 10.000 örnekle karıştırıldı (ansambl ve benchmark'lar aynı günlerle). Stratejinin kararlarını yeniden üretmez.

| Blok | P(Sharpe > B100) | P(Calmar > VM) | P(Sharpe > WM) | P(MDD < B100) | Sharpe ortanca [%5–%95] | P(negatif getiri) |
|---|---|---|---|---|---|---|
| 7g | %58.3 | %57.2 | %58.7 | %98.5 | 0.9153 [-0.0323 – 1.8185] | %8.4 |
| 14g | %56.8 | %56.0 | %57.5 | %98.5 | 0.8972 [-0.0819 – 1.8275] | %9.0 |
| 30g | %57.9 | %57.9 | %58.4 | %98.7 | 0.9041 [-0.1145 – 1.7725] | %9.5 |

## 7. Bootstrap B — sentetik fiyat yolları (KARAR ölçütü)

4 saatlik mumlar (açılış/en yüksek/en düşük/kapanış birlikte) blok blok yeniden örneklendi; ansambl ve benchmark'lar her yolda baştan çalıştırıldı.

| Senaryo | Yol | P1 Sharpe>B100 | P2 Calmar>VM | P3 Sharpe>WM | P4 MDD<B100 | Ans. yıllık ortanca [%5–%95] | Ans. düşüş ortanca [%5–%95] |
|---|---|---|---|---|---|---|---|
| vt40_blok180 (tümü) | 2000 | %31.9 ±0.010 | %43.3 | %31.2 | %94.1 | %12.735 [-9.945 – 46.9985] | %26.555 [17.069 – 42.693] |
| vt40_blok180 (ilk 1000) | 1000 | %33.3 ±0.015 | %44.0 | %32.3 | %93.9 | %11.89 [-10.515 – 46.7895] | %26.64 [16.9495 – 43.4745] |
| vt40_blok360 (tümü) | 2000 | %38.2 ±0.011 | %49.4 | %37.5 | %97.5 | %14.51 [-6.741 – 50.3505] | %25.02 [16.489 – 40.0715] |
| vt40_blok360 (ilk 1000) | 1000 | %37.2 ±0.015 | %48.8 | %36.4 | %97.7 | %13.905 [-7.0825 – 47.964] | %25.435 [16.5585 – 40.574] |
| vt40_blok540 (tümü) | 2000 | %39.6 ±0.011 | %49.4 | %39.2 | %97.9 | %15.055 [-6.79 – 46.371] | %24.42 [16.3485 – 38.8415] |
| vt40_blok540 (ilk 1000) | 1000 | %38.7 ±0.015 | %47.7 | %38.3 | %97.5 | %15.245 [-6.4605 – 46.711] | %25.05 [16.426 – 39.271] |
| vt30_blok360 (tümü) | 2000 | %36.1 ±0.011 | %47.5 | %35.4 | %99.2 | %11.385 [-5.611 – 37.0945] | %20.68 [13.569 – 33.4735] |
| vt30_blok360 (ilk 1000) | 1000 | %37.9 ±0.015 | %50.0 | %37.0 | %99.2 | %11.085 [-5.6425 – 35.597] | %20.745 [13.477 – 33.482] |
| vt20_blok360 (tümü) | 2000 | %37.2 ±0.011 | %48.5 | %35.9 | %100.0 | %8.32 [-4.2505 – 25.6515] | %14.415 [9.319 – 24.302] |
| vt20_blok360 (ilk 1000) | 1000 | %36.1 ±0.015 | %47.9 | %34.4 | %100.0 | %7.945 [-3.8845 – 25.5645] | %14.515 [9.129 – 24.341] |

**Sentetik yolların gerçekle karşılaştırması (ana senaryo, blok 360):**

- Tutarsız mum (en yüksek < açılış/kapanış vb.): 0
- Yol başına ortalama blok sayısı: 19.2
- Açılış boşluğu (mutlak ortalama): blok sınırlarında 0.0, tüm mumlarda 0.0, gerçek veride 0.0
- Oynaklık kümelenmesi (|getiri| otokorelasyonu, gecikme 1–10 ort.): sentetik {'ortanca': 0.0983, 'p5': 0.0833, 'p95': 0.1122, 'ortalama': 0.0982}, gerçek 0.1016
- Trend uzunluğu (20 günlük getiri işaretinin koşu uzunluğu, gün): sentetik {'ortanca': 9.3565, 'p5': 7.854, 'p95': 11.5699, 'ortalama': 9.4942}, gerçek 8.41
- BTC en büyük düşüş (%): sentetik {'ortanca': 47.17, 'p5': 30.3795, 'p95': 71.02, 'ortalama': 48.0639}, gerçek 52.97
- Sınırlama: sentetik yollar sadece bu 3 yılın mumlarından üretilir; hiç yaşanmamış rejimleri temsil etmez, blok birleşimleri yapay geçişler yaratabilir.

## 8. Günlük rejim analizi

Her günün rejimi, sadece önceki günün verisiyle belirlendi.

**Yön**

| Rejim | Gün | Ayrı dönem | Ansambl log getiri | BTC log getiri | Ans. Sharpe | BTC Sharpe | Ans. düşüş | BTC düşüş | İşlem açılışı | Piyasada | Ort. ağırlık |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Yükseliş | 574 | 11 | %58.02 | %82.93 | 1.296 | 1.397 | %20.65 | %29.03 | 27 | %85.0 | 0.583 |
| Yatay/kararsız | 208 | 29 | %1.47 | %-21.43 | 0.288 | -0.593 | %7.15 | %36.79 | 12 | %34.6 | 0.192 |
| Düşüş | 314 | 19 | %-0.7 | %19.13 | -0.073 | 0.695 | %6.86 | %41.21 | 12 | %13.4 | 0.05 |

**Oynaklık**

| Rejim | Gün | Ayrı dönem | Ansambl log getiri | BTC log getiri | Ans. Sharpe | BTC Sharpe | Ans. düşüş | BTC düşüş | İşlem açılışı | Piyasada | Ort. ağırlık |
|---|---|---|---|---|---|---|---|---|---|---|---|
| normal | 637 | 32 | %47.05 | %81.41 | 1.198 | 1.221 | %13.55 | %42.52 | 26 | %57.1 | 0.383 |
| yüksek | 190 | 12 | %-6.37 | %-6.98 | -0.361 | -0.022 | %16.25 | %26.31 | 5 | %37.4 | 0.249 |
| düşük | 269 | 20 | %18.12 | %6.2 | 1.229 | 0.408 | %19.42 | %34.97 | 20 | %62.1 | 0.367 |

## 9. 2018–2022 tarihsel stres testi (2018-01-01 → 2022-10-31)

Binance BTCUSDT verisi 2017-08-17'de başlar; 2017–2019 likiditesi ve piyasa yapısı bugünden farklıdır. Bu dönem parametre seçiminde kullanılmadı.

| Portföy | Getiri | Yıllık | Sharpe | Sortino | En büyük düşüş | Calmar |
|---|---|---|---|---|---|---|
| Ansambl (vt %40) | %432.69 | %41.36 | 1.382 | 2.366 | %22.31 | 1.854 |
| %100 BTC al-tut | %49.16 | %8.63 | 0.495 | 0.703 | %81.18 | 0.106 |
| Oynaklık eşleştirilmiş BTC (VM) | %301.63 | %33.33 | 1.022 | 1.566 | %40.74 | 0.818 |
| Ağırlık eşleştirilmiş BTC/nakit (WM, aylık) | %38.98 | %7.05 | 0.5 | 0.714 | %25.66 | 0.275 |
| %50 BTC aylık dengeli | %74.89 | %12.26 | 0.497 | 0.708 | %52.12 | 0.235 |

Ansambl: 71 işlem, en düşük özsermaye başlangıcın %87.42'i, ort. BTC ağırlığı 0.215.

## 10. Ezber riski — etkin deneme sayısı, DSR, PBO

- Seri sayısı 249 (değişken 247, hiç işlem yapmayan 2); N_toplam = 263 (30 coin ayarları dahil). 30 coin turnuvasının 14 ayarı çok varlıklı olduğu için korelasyona giremedi; sadece N_toplam'a eklendi.
- Etkin boyut tahmini — **özdeğer katılım oranı (ana): 8.2**, ortalama korelasyon (0.269): 3.7, kümeleme (ρ>0,7): 50

| Varsayım | DSR (ansambl, seçim riski dahil) | Şansla beklenen en iyi Sharpe |
|---|---|---|
| N=10 | %0.9 | 2.27 |
| N=20 | %0.1 | 2.74 |
| N=40 | %0.0 | 3.16 |
| N=69 | %0.0 | 3.46 |
| N_eff_katilim | %1.9 | 2.1 |
| N_eff_ort_korelasyon | %14.8 | 1.52 |
| N_eff_kume | %0.0 | 3.28 |
| N_toplam=263 | %0.0 | 4.12 |

- PBO (bütün denemeler, CSCV 16 blok): **%6.7** (249 seri)

## 11. Pozisyon taşıma testi (ayar seçen stratejiler, walk-forward)

A = pencere sonunda kapat; B = pozisyonu açıldığı ayarlarla taşı. Ansambl ayar seçmediği için tek kesintisiz simülasyondur.

| Strateji | A getiri | B getiri | A Sharpe | B Sharpe | A düşüş | B düşüş | A işlem | B işlem |
|---|---|---|---|---|---|---|---|---|
| temkinli | %-0.53 | %-0.53 | 0.0 | 0.0 | %13.11 | %13.11 | 66 | 66 |
| temkinli_4s | %-5.88 | %-4.85 | -0.54 | -0.43 | %6.82 | %6.82 | 18 | 18 |
| donchian | %-19.16 | %-19.54 | -0.5 | -0.52 | %37.74 | %38.04 | 254 | 254 |
| donchian_filtre | %-12.12 | %-12.53 | -0.31 | -0.32 | %31.91 | %32.23 | 238 | 238 |
| donchian_4s | %22.97 | %22.48 | 0.83 | 0.82 | %13.44 | %13.44 | 75 | 75 |
| supertrend_4s | %17.82 | %17.41 | 0.68 | 0.66 | %8.85 | %8.91 | 52 | 52 |
| aktif | %-46.56 | %-46.56 | -1.65 | -1.65 | %50.15 | %50.15 | 339 | 339 |
| formasyon | %-56.89 | %-57.18 | -1.23 | -1.24 | %68.54 | %68.75 | 537 | 537 |
| tsmom | %12.0 | %13.02 | 0.29 | 0.3 | %37.46 | %37.46 | 74 | 74 |
| tsmom_trend | %37.22 | %64.87 | 0.59 | 0.87 | %31.97 | %31.97 | 45 | 45 |
| kirilim_orta | %43.4 | %67.18 | 0.67 | 0.88 | %26.43 | %25.81 | 24 | 24 |
| donchian_4s_ch | %20.85 | %20.85 | 0.94 | 0.94 | %6.34 | %6.34 | 61 | 61 |
| donchian_4s_adx | %8.37 | %8.37 | 0.42 | 0.42 | %12.45 | %12.45 | 58 | 58 |
| donchian_4s_macd | %25.13 | %24.63 | 0.9 | 0.89 | %10.72 | %10.72 | 74 | 74 |
| donchian_4s_kama | %25.08 | %24.58 | 0.89 | 0.88 | %10.72 | %10.72 | 75 | 75 |
| donchian_4s_mom | %20.64 | %20.16 | 0.79 | 0.77 | %9.98 | %9.98 | 66 | 66 |
| donchian_4s_bulut | %15.42 | %14.96 | 0.61 | 0.6 | %12.26 | %12.38 | 74 | 74 |

_Bu rapor otomatik üretildi; yorum ve yanıtlar ayrıca yazılır. Sanal test; yatırım tavsiyesi değildir._
