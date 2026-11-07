# Ön Kayıt v2 / v2.1 — Sonuç

> **Bu bir istatistiksel üstünlük kanıtı değil, önceden belirlenmiş operasyonel tercih kuralının sonucudur. Geçmiş veri sonucu keşifseldir.**
> Bu çalıştırmanın sonucu **nihai karar değildir**. Nihai karar yalnızca temiz (ileri) veride 3 tamamlanmış büyük ayı dönemi oluştuğunda verilir (v2.1 §4). Gerçek paraya geçiş v1 §11 ve güvenlik kapılarına bağlıdır.

## Çalıştırma bilgisi

- Zaman: 2026-11-07T05:06:23+00:00 · çalıştırma: 42341284080-1 · commit: `7fdd54b911f6e9f537a962396bd519b4aafe4db6`
- Python 3.12.16 · numpy 2.1.3 · Linux-7.0.0-1017-azure-x86_64-with-glibc2.39
- Belgeler: `docs/ON_KAYIT_v2.md` dd485f666560…, `docs/ON_KAYIT_v2_1.md` 4a194a3ab5c7…
- Veri: Binance spot BTCUSDT 1s, 80725 mum (2017-08-17 → 2026-11-06), 117 arşiv dosyası, CHECKSUM doğrulanan 117, veri özeti `9b9298c1496ef9ee…`

## 1. Doğrulama testleri

**28/28 test geçti.** Bütün kritik testler geçti.

| # | Test | Sonuç | Ayrıntı |
|---|---|---|---|
| 1 | Ön kayıt belgeleri değişmemiş (SHA-256) | ✅ geçti | v2 ve v2.1 özetleri kayıtlı değerlerle karşılaştırıldı |
| 2 | Motor dosyaları v1 doğrulamasını üreten kodla aynı | ✅ geçti | 9 dosya birebir (v1 sonuç commit'i b50bae2) |
| 3 | Arşiv dosyaları eksiksiz ve CHECKSUM uyuşmazlığı yok | ✅ geçti | 117 dosya, CHECKSUM doğrulanan 117, uyuşmayan 0, alınamayan 0 |
| 4 | Ayı dönemi birim testi: basit dönem | ✅ geçti |  |
| 5 | Ayı dönemi birim testi: eşit zirve: t0 = C=P olan son gün; eşitlikte toparlanma | ✅ geçti |  |
| 6 | Ayı dönemi birim testi: tam %40 düşüş büyük sayılır | ✅ geçti |  |
| 7 | Ayı dönemi birim testi: %39,99 düşüş büyük sayılmaz | ✅ geçti |  |
| 8 | Ayı dönemi birim testi: yeni zirvesiz ikinci düşüş aynı dönem | ✅ geçti |  |
| 9 | Ayı dönemi birim testi: eşit dipte en erken gün | ✅ geçti |  |
| 10 | Ayı dönemi birim testi: tamamlanmamış dönem | ✅ geçti |  |
| 11 | Ayı dönemi birim testi: eksik gün atlanır, doldurulmaz | ✅ geçti |  |
| 12 | Ayı dönemi birim testi: ardışık dönemler çakışmaz | ✅ geçti |  |
| 13 | Maliyet formülü motorla aynı (alış ve satış) | ✅ geçti | alış True, satış True, motor eşleşmesi True |
| 14 | Sabit fiyatta maliyetsiz VM değer kaybetmez, maliyetli VM yalnızca maliyet kadar kaybeder | ✅ geçti | maliyetsiz 100.000000, maliyetli 99.703445, işlem 1 |
| 15 | Temiz başlangıç: kayıt saatini kesen mum dışarıda, performans 2026-11-06 00:00 UTC | ✅ geçti | T_kayıt 2026-11-05 12:35 UTC, ilk temiz 4s mum 2026-11-05 16:00 UTC, performans başlangıcı 2026-11-06 00:00 UTC |
| 16 | v1 veri özeti aynı (mum sayısı, boşluk, eksik, ilk/son) | ✅ geçti | mum_1s 80581/80581, bosluk_sayisi 28/28, eksik_1s_mum 127/127, ilk 2017-08-17/2017-08-17, son 2026-10-31/2026-10-31, mum_4s 20123/20123 |
| 17 | v1 ana dönem ENS özetleri aynı | ✅ geçti | getiri_pct 80.03/80.03, cagr_pct 21.63/21.63, max_dusus_pct 22.92/22.92, calmar 0.944/0.944, sharpe 0.924/0.924, sortino 1.477/1.477, islem 54/54, piyasada_pct 54.9/54.9, ort_btc_agirligi 0.356/0.356 |
| 18 | v1 2× maliyet özetleri aynı | ✅ geçti | getiri_pct 72.47/72.47, max_dusus_pct 23.93/23.93, sharpe 0.867/0.867 |
| 19 | v1 B100 ve VM özetleri aynı | ✅ geçti | B100 getiri_pct 123.63/123.63, B100 max_dusus_pct 52.97/52.97, B100 sharpe 0.807/0.807, VM getiri_pct 75.74/75.74, VM max_dusus_pct 26.52/26.52, VM sharpe 0.85/0.85 |
| 20 | v1 2018–2022 stres testi özetleri aynı | ✅ geçti | getiri_pct 432.69/432.69, max_dusus_pct 22.31/22.31, sharpe 1.382/1.382, islem 71/71, en_dusuk_ozsermaye_pct 87.42/87.42, ort_btc_agirligi 0.215/0.215 |
| 21 | v2 sarmalayıcısı ↔ v1 kodu: işlem sayısı, zamanları ve büyüklükleri aynı (v1 penceresi) | ✅ geçti | 72 işlem; giriş/çıkış zamanı, fiyat, adet, kâr ve çıkış sebebi birebir |
| 22 | v2 sarmalayıcısı ↔ v1 kodu: günlük portföy değeri ve pozisyon ağırlığı aynı (v1 penceresi) | ✅ geçti | 1096 gün karşılaştırıldı |
| 23 | Aynı evren, sermaye, başlangıç ve maliyet (ENS ve VM-A) | ✅ geçti | evren BTCUSDT 4s (aynı 20159 mum), başlangıç sermayesi 100/100, ikisi de nakitte başlar (2017-08-17 04:00 UTC), nakit getirisi %0, maliyet 1× {'fee': 0.001, 'slip': 0.0005} / 2× {'fee': 0.002, 'slip': 0.001}; ENS sermayeyi kendi içinde 3 alt sisteme böler (toplam sermaye aynı) |
| 24 | Oynaklık tahmincisi ENS ile aynı (540 adet 4s basit getiri, bölen n, ×√2190) | ✅ geçti | VM-A σ dizisi ENS'nin rvol dizisiyle birebir |
| 25 | VM tutarlılığı: nakit ≥ 0, işlem anındaki ağırlık ≤ %99 | ✅ geçti | en düşük nakit 31.922627, işlem anı en yüksek ağırlık VM-A 0.9900, VM-B 0.9900 |
| 26 | Uzun dönem: v2 sarmalayıcısı ↔ v1 kodu, işlemler ve günlük portföy değeri aynı | ✅ geçti | 144 işlem; giriş/çıkış zamanı, fiyat, adet, kâr ve çıkış sebebi birebir; 3256 gün |
| 27 | Geleceği görme testi: veri 4 rastgele noktada kesildiğinde önceki kararlar değişmiyor | ✅ geçti | kesim: 2019-07-09 12:00 UTC, 2019-12-23 16:00 UTC, 2020-04-24 04:00 UTC, 2024-03-12 04:00 UTC |
| 28 | v1 etkin deneme sayısı (N_eff) yeniden üretildi (bilgi) | ✅ geçti | seri 249/249, N_eff_katilim_orani 8.2/8.2, N_eff_ort_korelasyon 3.7/3.7, N_eff_kume 50/50 |

## 2. Geçmiş veri: keşifsel, geçici varsayılan

Ölçüm: 2017-12-01 → 2026-10-31. Ayı dönemi tanımı v2 §4 / v2.1 §2.

### 2.1 Su altı dönemleri (zirveden en az %20 düşüş olanlar; tamamı JSON'da)

| Zirve (t0) | Dip (t1) | Toparlanma (t2) | Derinlik | Büyük (≤ −%40) | Tamamlandı | Sayıldı |
|---|---|---|---|---|---|---|
| 2017-09-01 | 2017-09-14 | 2017-10-12 | -%34.0 | hayır | evet | hayır |
| 2017-11-04 | 2017-11-12 | 2017-11-16 | -%21.0 | hayır | evet | hayır |
| 2017-12-16 | 2018-12-15 | 2020-11-24 | -%83.2 | evet | evet | evet |
| 2021-01-08 | 2021-01-27 | 2021-02-08 | -%25.2 | hayır | evet | hayır |
| 2021-02-21 | 2021-02-28 | 2021-03-11 | -%21.4 | hayır | evet | hayır |
| 2021-04-13 | 2021-07-20 | 2021-10-19 | -%53.1 | evet | evet | evet |
| 2021-11-08 | 2022-11-21 | 2024-03-04 | -%76.6 | evet | evet | evet |
| 2024-03-13 | 2024-09-06 | 2024-11-06 | -%26.2 | hayır | evet | hayır |
| 2025-01-21 | 2025-04-08 | 2025-05-18 | -%28.1 | hayır | evet | hayır |
| 2025-10-06 | 2026-06-30 | — | -%53.0 | evet | hayır | hayır |

Toplam su altı dönemi: 50; sayılan tamamlanmış büyük ayı dönemi: **3**.

### Dönem 2017-12-16 → dip 2018-12-15 → toparlanma 2020-11-24 (BTC -%83.2)

| Maliyet | Strateji | Ayı MDD | Ayı getirisi | Toparlanma getirisi | Tam döngü getirisi | Tam döngü MDD | İşlem | Piyasada | Ort. ağırlık |
|---|---|---|---|---|---|---|---|---|---|
| 1x | ENS | %24.0 | -%24.0 | %300.2 | %204.0 | %28.4 | 38 | %44.2 | 0.22 |
| 1x | VM-A | %58.1 | -%58.1 | %301.8 | %68.5 | %58.1 | 71 | %100.0 | 0.605 |
| 1x | VM-B | %59.2 | -%59.2 | %295.6 | %61.3 | %59.3 | 118 | %100.0 | 0.654 |
| 1x | B100 | %83.2 | -%83.2 | %496.6 | %0.3 | %83.2 | 0 | %100.0 | 1.0 |
| 2x | ENS | %24.4 | -%24.4 | %292.4 | %196.8 | %28.9 | 38 | %44.2 | 0.22 |
| 2x | VM-A | %58.2 | -%58.2 | %299.7 | %67.2 | %58.2 | 71 | %100.0 | 0.606 |
| 2x | VM-B | %59.4 | -%59.4 | %291.2 | %58.9 | %59.5 | 118 | %100.0 | 0.655 |
| 2x | B100 | %83.2 | -%83.2 | %496.6 | %0.3 | %83.2 | 0 | %100.0 | 1.0 |

| Maliyet | ENS'nin VM-A'ya göre ayı MDD avantajı | Göreli | ≥10 puan | ≥%25 | Koruma şartı | Kaçırılan toparlanma (VM-A − ENS) | Katılım oranı |
|---|---|---|---|---|---|---|---|
| 1x | +34.0 puan | %58.6 | ✅ geçti | ✅ geçti | ✅ geçti | +1.6 puan | 0.996 |
| 2x | +33.8 puan | %58.1 | ✅ geçti | ✅ geçti | ✅ geçti | +7.3 puan | 0.982 |

### Dönem 2021-04-13 → dip 2021-07-20 → toparlanma 2021-10-19 (BTC -%53.1)

| Maliyet | Strateji | Ayı MDD | Ayı getirisi | Toparlanma getirisi | Tam döngü getirisi | Tam döngü MDD | İşlem | Piyasada | Ort. ağırlık |
|---|---|---|---|---|---|---|---|---|---|
| 1x | ENS | %11.6 | -%11.6 | %16.0 | %2.6 | %12.3 | 10 | %45.8 | 0.176 |
| 1x | VM-A | %26.8 | -%26.8 | %47.3 | %7.8 | %26.8 | 11 | %100.0 | 0.454 |
| 1x | VM-B | %29.6 | -%29.6 | %52.0 | %7.0 | %29.6 | 21 | %100.0 | 0.509 |
| 1x | B100 | %53.1 | -%53.1 | %115.8 | %1.1 | %53.1 | 0 | %100.0 | 1.0 |
| 2x | ENS | %11.5 | -%11.5 | %15.5 | %2.2 | %12.4 | 10 | %45.8 | 0.176 |
| 2x | VM-A | %26.8 | -%26.8 | %47.2 | %7.7 | %26.8 | 11 | %100.0 | 0.454 |
| 2x | VM-B | %29.7 | -%29.7 | %51.8 | %6.8 | %29.7 | 21 | %100.0 | 0.509 |
| 2x | B100 | %53.1 | -%53.1 | %115.8 | %1.1 | %53.1 | 0 | %100.0 | 1.0 |

| Maliyet | ENS'nin VM-A'ya göre ayı MDD avantajı | Göreli | ≥10 puan | ≥%25 | Koruma şartı | Kaçırılan toparlanma (VM-A − ENS) | Katılım oranı |
|---|---|---|---|---|---|---|---|
| 1x | +15.3 puan | %57.0 | ✅ geçti | ✅ geçti | ✅ geçti | +31.4 puan | 0.787 |
| 2x | +15.3 puan | %57.0 | ✅ geçti | ✅ geçti | ✅ geçti | +31.7 puan | 0.785 |

### Dönem 2021-11-08 → dip 2022-11-21 → toparlanma 2024-03-04 (BTC -%76.6)

| Maliyet | Strateji | Ayı MDD | Ayı getirisi | Toparlanma getirisi | Tam döngü getirisi | Tam döngü MDD | İşlem | Piyasada | Ort. ağırlık |
|---|---|---|---|---|---|---|---|---|---|
| 1x | ENS | %21.5 | -%21.5 | %150.1 | %96.3 | %21.8 | 40 | %49.9 | 0.33 |
| 1x | VM-A | %59.9 | -%59.9 | %291.7 | %57.0 | %59.9 | 30 | %100.0 | 0.775 |
| 1x | VM-B | %65.3 | -%65.0 | %275.0 | %31.2 | %65.3 | 63 | %100.0 | 0.804 |
| 1x | B100 | %76.6 | -%76.6 | %332.4 | %1.1 | %76.6 | 0 | %100.0 | 1.0 |
| 2x | ENS | %22.3 | -%22.3 | %137.4 | %84.4 | %22.7 | 41 | %49.3 | 0.328 |
| 2x | VM-A | %60.0 | -%60.0 | %291.0 | %56.5 | %60.0 | 30 | %100.0 | 0.776 |
| 2x | VM-B | %65.4 | -%65.1 | %273.5 | %30.2 | %65.4 | 63 | %100.0 | 0.805 |
| 2x | B100 | %76.6 | -%76.6 | %332.4 | %1.1 | %76.6 | 0 | %100.0 | 1.0 |

| Maliyet | ENS'nin VM-A'ya göre ayı MDD avantajı | Göreli | ≥10 puan | ≥%25 | Koruma şartı | Kaçırılan toparlanma (VM-A − ENS) | Katılım oranı |
|---|---|---|---|---|---|---|---|
| 1x | +38.4 puan | %64.1 | ✅ geçti | ✅ geçti | ✅ geçti | +141.6 puan | 0.638 |
| 2x | +37.7 puan | %62.8 | ✅ geçti | ✅ geçti | ✅ geçti | +153.6 puan | 0.607 |

### 2.2 Tüm ölçüm dönemi

| Maliyet | Strateji | Toplam getiri | CAGR | MDD |
|---|---|---|---|---|
| 1x | ENS | %1555.5 | %36.99 | %28.4 |
| 1x | VM-A | %680.8 | %25.92 | %59.9 |
| 1x | VM-B | %512.7 | %22.54 | %65.3 |
| 1x | B100 | %688.5 | %26.06 | %83.2 |
| 2x | ENS | %1362.5 | %35.10 | %28.9 |
| 2x | VM-A | %669.1 | %25.71 | %60.0 |
| 2x | VM-B | %492.2 | %22.07 | %65.4 |
| 2x | B100 | %688.5 | %26.06 | %83.2 |

### 2.3 Karar şartları (v2 §6)

| # | Şart | Sonuç |
|---|---|---|
| 1 | Tamamlanmış büyük ayı dönemi ≥ 3 (n = 3) | ✅ geçti |
| 2 | Koruma şartını iki maliyette de geçen dönem ≥ 2 (geçen: 3) | ✅ geçti |
| 3 | CAGR(VM-A) − CAGR(ENS) ≤ 2 puan (1×: -11.1 puan, 2×: -9.4 puan) | ✅ geçti |
| 4 | 1–3 her iki maliyette | ✅ geçti |

**Geçmiş veri sonucu (keşifsel, geçici):** Bütün şartlar sağlandı: ENS ayı piyasası koruma alternatifi olarak GEÇİCİ tercih edilir (keşifsel; nihai karar değil).

### 2.4 DSR (bilgi amaçlı, karara girmez)

v1 ile aynı: Bailey & López de Prado (2014) DSR (bot/overfit.deflated_sharpe); günlük getiriler, ölçüm 2023-11-01 → 2026-10-31; deneme Sharpe dağılımı = v1'in 249 serisi + VM-A, VM-B, VM-ref; N_eff = v1'in üç yöntemi, VM serileri eklenmiş korelasyon matrisinden.

Etkin boyut: {'seri': 252, 'degisken_seri': 250, 'sabit_seri': 2, 'N_eff_katilim_orani': 8.3, 'N_eff_ort_korelasyon': 3.8, 'ort_korelasyon': 0.262, 'N_eff_kume': 51}

| Deneme sayısı | ENS DSR | VM-A DSR |
|---|---|---|
| N_toplam=266 | 0.0 | 0.0 |
| N_eff_katilim | 0.019 | 0.009 |
| N_eff_ort_korelasyon | 0.149 | 0.092 |
| N_eff_kume | 0.0 | 0.0 |

## 3. İleri (temiz) veri: yalnızca gözlem

Performans başlangıcı: 2026-11-06 00:00 UTC. Son tam gün: 2026-11-06.

**Durum:** 0 tamamlanmış ileri büyük ayı dönemi. 3'e ulaşmadan bütün sonuçlar yalnızca gözlemdir; nihai kararı ve geçici varsayılanı değiştirmez.

| 1x | Strateji | Getiri | MDD | Gün | CAGR |
|---|---|---|---|---|---|
| 1x | ENS | %0.00 | %0.00 | 1 | 1 yıldan kısa |
| 1x | VM-A | -%0.31 | %0.31 | 1 | 1 yıldan kısa |
| 1x | VM-B | -%0.31 | %0.31 | 1 | 1 yıldan kısa |
| 1x | B100 | -%0.32 | %0.32 | 1 | 1 yıldan kısa |

| 2x | Strateji | Getiri | MDD | Gün | CAGR |
|---|---|---|---|---|---|
| 2x | ENS | %0.00 | %0.00 | 1 | 1 yıldan kısa |
| 2x | VM-A | -%0.31 | %0.31 | 1 | 1 yıldan kısa |
| 2x | VM-B | -%0.31 | %0.31 | 1 | 1 yıldan kısa |
| 2x | B100 | -%0.32 | %0.32 | 1 | 1 yıldan kısa |

Kayıt anında süren düşüş dönemi: zirve 2025-10-06, şu ana kadarki dip 2026-06-30 (-%53.0). Kayıt anında sürüyordu; −%40'ı geçse bile ileri karara girmez.

## 4. Notlar

- ‘Ağırlık ≤ %99’ işlem anındaki hedeftir. Fiyat yükselince her iki stratejide de gerçek ağırlık %99'un biraz üstüne kayabilir (ENS'de pozisyon adedi sabit, VM'de 0,05 bant). Bu, v2.1 §3'ün yorumudur, kural değişikliği değildir.
- Pencere başında veya sonunda strateji günlük kaydı yoksa (eksik 4s mum) önceki son kayıt kullanılır.
- VM-ref ve B100 v1 tanımıyla yalnızca bilgi amaçlıdır; karar ENS ile VM-A arasındadır.
- MDD karşılaştırmaları float64 ile, eşiklerde kesin ≥ / ≤ ile yapılır; sınırdaki değer şartı sağlamamış sayılır.
- v1 doğrulaması işlem listesi saklamadığı için işlem düzeyindeki karşılaştırma, v1 commit'iyle birebir aynı olduğu doğrulanan v1 koduyla yapıldı. Bu çalıştırma tam işlem listelerini ve günlük değerleri saklar; sonraki çalıştırmalar bununla işlem işlem karşılaştırılabilir.