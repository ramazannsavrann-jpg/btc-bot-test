# 🔬 Araştırma Turnuvası (4 yıl, walk-forward)

Sınav dönemi **2023-11-01 → 2026-11-01** (12 pencere × 3 ay). Her pencerede ayarlar sadece önceki 12 ayda seçildi. Komisyon %0,1 + kayma %0,05, kaldıraç yok, sadece alım yönü.

**BTC al-tut aynı dönemde:** getiri %123.97, yıllık %30.84, Sharpe 0.79, en büyük düşüş %52.97, Calmar 0.58

| # | Bot | Mum | Getiri | Yıllık | Sharpe | Sortino | Calmar | En büyük düşüş | Piyasada | Haftada işlem | PF | 2× maliyet | 3× maliyet | Pozitif pencere |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Kırılım Ansamblı 20/40/60 gün (4s) | 4h | %68.7 | %19.04 | 0.84 | 1.34 | 0.79 | %24.21 | %52.2 | 0.4 | 1.89 | %59.91 | %51.79 | 7/12 |
| 2 | Donchian (4s) | 4h | %21.22 | %6.63 | 0.73 | 1.47 | 0.65 | %10.21 | %23.5 | 0.53 | 1.44 | %9.77 | %-0.15 | 8/12 |
| 3 | Donchian (4s) + MACD > 0 | 4h | %20.39 | %6.38 | 0.7 | 1.4 | 0.59 | %10.72 | %23.4 | 0.53 | 1.42 | %7.62 | %-2.13 | 8/12 |
| 4 | Zaman Serisi Momentum + EMA200 | 4h | %51.37 | %14.82 | 0.67 | 1.05 | 0.42 | %35.19 | %51.3 | 0.29 | 1.43 | %37.12 | %24.22 | 6/12 |
| 5 | Donchian + Chandelier 84 (4s) | 4h | %15.47 | %4.91 | 0.67 | 1.2 | 0.74 | %6.64 | %24.1 | 0.45 | 1.4 | %6.96 | %0.04 | 8/12 |
| 6 | Donchian (4s) + KAMA yükseliyor | 4h | %17.63 | %5.56 | 0.61 | 1.24 | 0.52 | %10.72 | %23.6 | 0.54 | 1.35 | %5.11 | %-4.43 | 8/12 |
| 7 | Donchian (4s) + 30 gün momentum > 0 ve SMA40 üstü | 4h | %15.35 | %4.87 | 0.57 | 1.16 | 0.49 | %9.98 | %20.2 | 0.48 | 1.34 | %4.36 | %-4.09 | 9/12 |
| 8 | Donchian (4s) + Ichimoku bulutu üstü | 4h | %15.71 | %4.98 | 0.57 | 1.11 | 0.38 | %13.15 | %22.7 | 0.52 | 1.31 | %4.08 | %-4.86 | 8/12 |
| 9 | Donchian (4s) + ADX > 20 | 4h | %13.29 | %4.25 | 0.52 | 1.08 | 0.38 | %11.06 | %17.5 | 0.42 | 1.34 | %2.51 | %-4.77 | 8/12 |
| 10 | Kırılım + Orta Nokta Çıkış (4s) | 4h | %23.69 | %7.34 | 0.48 | 0.71 | 0.44 | %16.54 | %40.7 | 0.17 | 1.48 | %17.8 | %12.28 | 6/12 |
| 11 | Zaman Serisi Momentum (vol. hedefli) | 1h | %25.66 | %7.91 | 0.42 | 0.65 | 0.21 | %38.0 | %58.9 | 0.47 | 1.18 | %9.31 | %-11.39 | 5/12 |
| 12 | Supertrend (4s) | 4h | %7.61 | %2.48 | 0.3 | 0.54 | 0.19 | %12.93 | %23.4 | 0.36 | 1.2 | %0.01 | %-5.97 | 3/12 |
| 13 | Temkinli Trend (4s) | 4h | %-2.22 | %-0.75 | -0.13 | -0.19 | -0.07 | %10.77 | %3.7 | 0.18 | 0.87 | %-5.58 | %-7.01 | 3/12 |
| 14 | Donchian + Haber/Duygu Freni | 1h | %-10.63 | %-3.68 | -0.24 | -0.42 | -0.12 | %30.41 | %16.6 | 1.6 | 0.91 | %-45.4 | %-64.92 | 5/12 |
| 15 | Temkinli Trend | 1h | %-7.52 | %-2.57 | -0.37 | -0.53 | -0.18 | %14.52 | %3.4 | 0.47 | 0.82 | %-23.81 | %-36.04 | 6/12 |
| 16 | Donchian + Chandelier | 1h | %-26.15 | %-9.61 | -0.66 | -1.11 | -0.23 | %41.96 | %17.8 | 1.73 | 0.81 | %-55.86 | %-70.28 | 3/12 |
| 17 | Formasyon Avcısı | 1h | %-55.87 | %-23.87 | -1.11 | -1.82 | -0.36 | %66.18 | %35.4 | 3.65 | 0.8 | %-88.29 | %-94.41 | 5/12 |
| 18 | Aktif Trend | 1h | %-57.08 | %-24.57 | -2.05 | -2.72 | -0.42 | %57.92 | %17.2 | 2.42 | 0.64 | %-83.6 | %-91.06 | 1/12 |

## Ezber (overfitting) riski

- **PBO = %50.4** (69 aday×ayar). Eğitimde en iyi görünen ayarın sınavda ortancanın altında kalma olasılığı. %50 civarı = seçim yazı-turadan farksız.
- **Deflated Sharpe = %1.0** (en iyi: `kirilim_orta|(360, 0.4)`, yıllık Sharpe 0.91, bu kadar denemede şansla beklenen en iyi Sharpe 2.24). %95 üstü güçlü kanıt sayılır.

## Rejime göre ortalama 3 aylık getiri

| Bot | Yükseliş | Yatay/kararsız | Düşüş |
|---|---|---|---|
| Kırılım Ansamblı 20/40/60 gün (4s) | %4.52 | %5.39 | %6.23 |
| Donchian (4s) | %1.97 | %0.74 | %2.79 |
| Donchian (4s) + MACD > 0 | %1.75 | %0.6 | %3.41 |
| Zaman Serisi Momentum + EMA200 | %4.56 | %3.67 | %5.11 |
| Donchian + Chandelier 84 (4s) | %1.42 | %0.4 | %2.35 |
| Donchian (4s) + KAMA yükseliyor | %1.56 | %0.6 | %2.75 |
| Donchian (4s) + 30 gün momentum > 0 ve SMA40 üstü | %1.59 | %-0.17 | %3.11 |
| Donchian (4s) + Ichimoku bulutu üstü | %1.59 | %0.65 | %1.74 |
| Donchian (4s) + ADX > 20 | %1.21 | %-0.41 | %3.85 |
| Kırılım + Orta Nokta Çıkış (4s) | %3.68 | %-0.25 | %1.77 |
| Zaman Serisi Momentum (vol. hedefli) | %3.35 | %0.64 | %4.98 |
| Supertrend (4s) | %0.95 | %-2.18 | %6.0 |
| Temkinli Trend (4s) | %0.16 | %-1.08 | %0.74 |
| Donchian + Haber/Duygu Freni | %-1.14 | %-3.47 | %5.97 |
| Temkinli Trend | %-1.43 | %-0.05 | %0.78 |
| Donchian + Chandelier | %-4.16 | %-2.76 | %4.18 |
| Formasyon Avcısı | %-7.46 | %-9.21 | %4.13 |
| Aktif Trend | %-8.71 | %-6.44 | %-1.64 |

## Botlar

- **Kırılım Ansamblı 20/40/60 gün (4s)** — Aynı kırılım stratejisinin 20, 40 ve 60 günlük üç kopyası, her biri paranın 1/3'üyle; oynaklık hedefli büyüklük (yıllık %40). Tek ayara bahis yapmaz. İşlem 63, başarı %42.9, işlem başı beklenti 1.0904$, ort. kazanç 5.3926$ / ort. kayıp -2.1362$, en uzun kayıp serisi 15, ort. tutma 481.9 saat. Al-tutu geçen pencere 4/12. Son ayar: `{}`.
- **Donchian (4s)** — Donchian kırılımı 4 saatlik mumlarda (daha az işlem). İşlem 83, başarı %34.9, işlem başı beklenti 0.2557$, ort. kazanç 2.412$ / ort. kayıp -0.9023$, en uzun kayıp serisi 9, ort. tutma 74.4 saat. Al-tutu geçen pencere 4/12. Son ayar: `{'dc_entry': 20, 'dc_exit': 10}`.
- **Donchian (4s) + MACD > 0** — Donchian 4s kırılımı; sadece MACD > 0 iken alır. İşlem 83, başarı %36.1, işlem başı beklenti 0.2456$, ort. kazanç 2.3154$ / ort. kayıp -0.9259$, en uzun kayıp serisi 9, ort. tutma 74.3 saat. Al-tutu geçen pencere 4/12. Son ayar: `{'dc_entry': 20}`.
- **Zaman Serisi Momentum + EMA200** — TSMOM, ek olarak fiyat 4s EMA200 üstündeyken. İşlem 46, başarı %34.8, işlem başı beklenti 1.1168$, ort. kazanç 10.7391$ / ort. kayıp -4.0152$, en uzun kayıp serisi 9, ort. tutma 292.9 saat. Al-tutu geçen pencere 3/12. Son ayar: `{'mom_days': 60, 'vol_target': 0.5}`.
- **Donchian + Chandelier 84 (4s)** — Donchian 4s; iz süren stop = girişten beri zirve − k×ATR(84). İşlem 70, başarı %40.0, işlem başı beklenti 0.221$, ort. kazanç 1.9226$ / ort. kayıp -0.9135$, en uzun kayıp serisi 6, ort. tutma 90.6 saat. Al-tutu geçen pencere 5/12. Son ayar: `{'chandelier_atr': 4.0}`.
- **Donchian (4s) + KAMA yükseliyor** — Donchian 4s kırılımı; sadece KAMA yükseliyor iken alır. İşlem 85, başarı %34.1, işlem başı beklenti 0.2074$, ort. kazanç 2.3579$ / ort. kayıp -0.9062$, en uzun kayıp serisi 9, ort. tutma 73.2 saat. Al-tutu geçen pencere 4/12. Son ayar: `{'dc_entry': 20}`.
- **Donchian (4s) + 30 gün momentum > 0 ve SMA40 üstü** — Donchian 4s kırılımı; sadece 30 gün momentum > 0 ve SMA40 üstü iken alır. İşlem 75, başarı %33.3, işlem başı beklenti 0.2046$, ort. kazanç 2.4064$ / ort. kayıp -0.8962$, en uzun kayıp serisi 8, ort. tutma 71.0 saat. Al-tutu geçen pencere 4/12. Son ayar: `{'dc_entry': 20}`.
- **Donchian (4s) + Ichimoku bulutu üstü** — Donchian 4s kırılımı; sadece Ichimoku bulutu üstü iken alır. İşlem 82, başarı %35.4, işlem başı beklenti 0.1915$, ort. kazanç 2.2822$ / ort. kayıp -0.9524$, en uzun kayıp serisi 9, ort. tutma 72.7 saat. Al-tutu geçen pencere 4/12. Son ayar: `{'dc_entry': 20}`.
- **Donchian (4s) + ADX > 20** — Donchian 4s kırılımı; sadece ADX > 20 iken alır. İşlem 65, başarı %32.3, işlem başı beklenti 0.2044$, ort. kazanç 2.4863$ / ort. kayıp -0.8846$, en uzun kayıp serisi 6, ort. tutma 71.0 saat. Al-tutu geçen pencere 5/12. Son ayar: `{'dc_entry': 20}`.
- **Kırılım + Orta Nokta Çıkış (4s)** — Kapanış son N mumun en yüksek kapanışını geçince alır; N mumluk en yüksek/en düşük kapanışın orta noktası (sadece yukarı taşınır) kırılınca satar. İsteğe bağlı oynaklık hedefli büyüklük. İşlem 27, başarı %37.0, işlem başı beklenti 0.8774$, ort. kazanç 7.3352$ / ort. kayıp -2.9213$, en uzun kayıp serisi 8, ort. tutma 396.1 saat. Al-tutu geçen pencere 5/12. Son ayar: `{'bo_len': 240, 'vol_target': 0}`.
- **Zaman Serisi Momentum (vol. hedefli)** — Günde bir kez bakar: son N günün getirisi pozitifse tutar, negatife dönünce satar. Pozisyon büyüklüğü oynaklığa göre ayarlanır (hedef yıllık oynaklık / gerçekleşen oynaklık). İşlem 74, başarı %33.8, işlem başı beklenti 0.3467$, ort. kazanç 6.672$ / ort. kayıp -2.8805$, en uzun kayıp serisi 8, ort. tutma 209.1 saat. Al-tutu geçen pencere 3/12. Son ayar: `{'mom_days': 60, 'vol_target': 0.5}`.
- **Supertrend (4s)** — Supertrend yukarı dönünce al, aşağı dönünce sat; EMA200 filtresi. İşlem 57, başarı %33.3, işlem başı beklenti 0.1336$, ort. kazanç 2.3598$ / ort. kayıp -0.9795$, en uzun kayıp serisi 4, ort. tutma 108.1 saat. Al-tutu geçen pencere 5/12. Son ayar: `{'st_mult': 4.0}`.
- **Temkinli Trend (4s)** — Temkinli Trend'in 4 saatlik mumlu hâli. İşlem 28, başarı %57.1, işlem başı beklenti -0.0793$, ort. kazanç 0.9412$ / ort. kayıp -1.4401$, en uzun kayıp serisi 4, ort. tutma 34.6 saat. Al-tutu geçen pencere 5/12. Son ayar: `{'rsi_entry': 30.0, 'tp_atr': 3.0}`.
- **Donchian + Haber/Duygu Freni** — Donchian; FOMC/CPI civarında ve aşırı açgözlülükte alım yok. İşlem 251, başarı %35.9, işlem başı beklenti -0.0423$, ort. kazanç 1.2662$ / ort. kayıp -0.7738$, en uzun kayıp serisi 10, ort. tutma 17.4 saat. Al-tutu geçen pencere 5/12. Son ayar: `{'dc_entry': 24, 'fg_max': 75}`.
- **Temkinli Trend** — EMA50/200 trendinde RSI dönüşüyle alır; ATR stop/hedef. İşlem 73, başarı %56.2, işlem başı beklenti -0.103$, ort. kazanç 0.8126$ / ort. kayıp -1.2761$, en uzun kayıp serisi 5, ort. tutma 12.4 saat. Al-tutu geçen pencere 5/12. Son ayar: `{'rsi_entry': 30.0, 'tp_atr': 3.0}`.
- **Donchian + Chandelier** — N mumluk zirve kırılımı, EMA200 üstü; iz süren 3×ATR stop. İşlem 270, başarı %35.6, işlem başı beklenti -0.0973$, ort. kazanç 1.169$ / ort. kayıp -0.7959$, en uzun kayıp serisi 13, ort. tutma 17.3 saat. Al-tutu geçen pencere 3/12. Son ayar: `{'dc_entry': 24, 'dc_exit': 12}`.
- **Formasyon Avcısı** — İkili dip, ters OBO, direnç, fincan-kulp, takoz kırılımları. İşlem 571, başarı %32.9, işlem başı beklenti -0.0988$, ort. kazanç 1.2054$ / ort. kayıp -0.7389$, en uzun kayıp serisi 9, ort. tutma 16.3 saat. Al-tutu geçen pencere 4/12. Son ayar: `{'pivot_k': 5, 'tp_atr': 100.0}`.
- **Aktif Trend** — Trendde RSI dönüşü veya 24 saatlik zirve kırılımı. İşlem 378, başarı %50.3, işlem başı beklenti -0.1526$, ort. kazanç 0.5493$ / ort. kayıp -0.8619$, en uzun kayıp serisi 5, ort. tutma 12.0 saat. Al-tutu geçen pencere 4/12. Son ayar: `{'rsi_entry': 35.0, 'tp_atr': 3.0}`.

_Not: Sınav pencerelerinin bir kısmına önceki turnuvalarda bakıldı; bu yüzden tamamen dokunulmamış değiller. Geçmiş sonuç geleceği garanti etmez. Yatırım tavsiyesi değildir._
