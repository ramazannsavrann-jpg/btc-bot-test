# 🏆 Strateji Turnuvası

Ayarlar **2024-11-01 → 2026-03-26** döneminde seçildi; sıralama botların **hiç görmediği** **2026-03-27 → 2026-10-31** dönemindeki sonuca göre. Komisyon %0,1 + kayma %0,05 dahil, kaldıraç yok.

Şart: sınav döneminde haftada en az 1.5 işlem. Puan = getiri ÷ en büyük düşüş; normal ve 2 kat komisyonlu sonucun ortalaması (komisyona dayanıksız botlar geriye düşer).

| # | Bot | Mum | 100$ → | 2× komisyonla | Haftada işlem | Başarı | En büyük düşüş | Al-tut | 1 haftada tipik | Puan |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Donchian + Haber/Duygu Freni | 1h | 103.79$ | 91.94$ | 1.85 | %37.9 | %14.03 | %12.73 | 99.66$ | -0.1 |
| 2 | Grid Bot 7/24 | 15m | 102.02$ | 91.62$ | 9.11 | %88.8 | %14.74 | %12.73 | 100.24$ | -0.173 |
| 3 | Grid Bot + Olay Freni | 15m | 101.78$ | 91.46$ | 9.05 | %88.7 | %14.84 | %12.73 | 100.26$ | -0.186 |
| 4 | Formasyon Avcısı (hepsi) | 1h | 95.79$ | 78.97$ | 2.27 | %35.2 | %16.05 | %12.73 | 99.42$ | -0.571 |
| 5 | Donchian Kırılım + Chandelier | 1h | 93.95$ | 81.91$ | 1.63 | %35.3 | %14.37 | %12.73 | 99.54$ | -0.71 |
| 6 | Aşırı Korkuda Dip Alımı | 1h | 83.77$ | 72.19$ | 2.78 | %31.0 | %22.42 | %12.73 | 100.0$ | -0.825 |
| 7 | Takoz / Üçgen Kırılımı | 1h | 81.95$ | 69.82$ | 2.05 | %28.1 | %23.5 | %12.73 | 99.18$ | -0.844 |
| 8 | Aktif Trend + Haber/Duygu Freni | 1h | 83.08$ | 68.79$ | 2.62 | %50.0 | %21.54 | %12.73 | 100.0$ | -0.862 |
| 9 | Aktif Trend (RSI + Kırılım) | 1h | 82.91$ | 68.25$ | 2.68 | %50.0 | %21.7 | %12.73 | 100.0$ | -0.864 |
| 10 | Formasyon Avcısı + Trend/Haber Freni | 1h | 84.38$ | 68.05$ | 2.59 | %28.4 | %20.92 | %12.73 | 99.21$ | -0.869 |
| 11 | Yatay Direnç Kırılımı | 1h | 88.64$ | 77.7$ | 1.79 | %33.9 | %14.6 | %12.73 | 99.57$ | -0.881 |
| 12 | Gece Saati Etkisi (kontrol) | 1h | 79.54$ | 66.65$ | 3.07 | %16.7 | %21.58 | %12.73 | 99.27$ | -0.968 |
| 13 | EMA 9/21 Hızlı (15dk) | 15m | 49.79$ | 31.86$ | 6.9 | %32.9 | %50.89 | %12.73 | 97.84$ | -0.991 |
| 14 | Connors RSI(2) Geri Çekilme | 1h | 81.63$ | 71.81$ | 3.1 | %38.1 | %18.67 | %12.73 | 99.71$ | -0.992 |
| 15 | Fincan-Kulp ⚠️az işlem | 1h | 100.0$ | 100.0$ | 0.0 | %0.0 | %0.0 | %12.73 | 100.0$ | 0.0 |
| 16 | BinH + Cluc (Freqtrade) ⚠️az işlem | 15m | 99.73$ | 99.56$ | 0.06 | %100.0 | %1.0 | %12.73 | 100.0$ | -0.177 |
| 17 | Ters Omuz-Baş-Omuz ⚠️az işlem | 1h | 98.96$ | 97.67$ | 0.32 | %30.0 | %6.93 | %12.73 | 100.0$ | -0.235 |
| 18 | İkili Dip (W) Kırılımı ⚠️az işlem | 1h | 98.34$ | 89.15$ | 1.21 | %31.6 | %10.31 | %12.73 | 100.0$ | -0.437 |
| 19 | Boğa Bayrağı / Flama ⚠️az işlem | 1h | 98.45$ | 96.6$ | 0.35 | %36.4 | %4.92 | %12.73 | 100.0$ | -0.488 |
| 20 | Bollinger + RSI Dip Alımı ⚠️az işlem | 1h | 98.64$ | 95.89$ | 0.35 | %45.5 | %2.66 | %12.73 | 100.0$ | -0.675 |
| 21 | UT Bot Alerts + EMA200 ⚠️az işlem | 1h | 87.02$ | 79.8$ | 1.34 | %31.0 | %17.32 | %12.73 | 100.0$ | -0.807 |
| 22 | Supertrend + EMA200 ⚠️az işlem | 1h | 89.61$ | 83.72$ | 1.21 | %36.8 | %14.04 | %12.73 | 99.95$ | -0.82 |
| 23 | Squeeze Momentum (LazyBear) ⚠️az işlem | 1h | 88.67$ | 78.72$ | 1.41 | %18.2 | %15.4 | %12.73 | 99.55$ | -0.841 |

## Botlar ne yapıyor?

- **Donchian + Haber/Duygu Freni** — Donchian kırılım botu; ama faiz kararı/enflasyon açıklamasına 4 saat kala ve sonrası 4 saat işlem açmaz, Korku & Açgözlülük endeksi çok yüksekken almaz. Seçilen ayar: `{'dc_entry': 24, 'dc_exit': 24, 'fg_max': 75}`. 1 hafta 100$: en kötü 97.01$, en iyi 111.39$, kazandıran hafta %33.3.
- **Grid Bot 7/24** — Binance Spot Grid gibi: fiyatın ±%X aralığına kademeler kurar, düşüşte parça parça alır, bir üst kademede satar. Yatay piyasada sürekli işlem yapar. Seçilen ayar: `{'n_levels': 8, 'range_pct': 0.05}`. 1 hafta 100$: en kötü 92.41$, en iyi 102.15$, kazandıran hafta %59.6.
- **Grid Bot + Olay Freni** — Grid botu; faiz kararı ve enflasyon açıklaması civarında yeni kademe alımı yapmaz (sert tek yönlü hareketlere yakalanmamak için). Seçilen ayar: `{'n_levels': 8, 'range_pct': 0.05}`. 1 hafta 100$: en kötü 92.41$, en iyi 102.15$, kazandıran hafta %59.6.
- **Formasyon Avcısı (hepsi)** — İkili dip, ters OBO, bayrak, yatay direnç, fincan-kulp ve takoz/üçgen formasyonlarından hangisi kırılırsa alır. Seçilen ayar: `{'pivot_k': 5, 'vol_confirm': True, 'tp_atr': 100.0}`. 1 hafta 100$: en kötü 94.77$, en iyi 111.72$, kazandıran hafta %33.8.
- **Donchian Kırılım + Chandelier** — Fiyat son N saatin zirvesini kırınca ve EMA200 üstündeyken alır; girişten beri zirve − 3×ATR iz süren stop veya kanal dibi kırılınca satar. Bilimsel kanıtı en güçlü aile. Seçilen ayar: `{'dc_entry': 48, 'dc_exit': 12}`. 1 hafta 100$: en kötü 96.51$, en iyi 110.74$, kazandıran hafta %26.3.
- **Aşırı Korkuda Dip Alımı** — Korku & Açgözlülük endeksi çok düşükken (herkes korkarken) fiyat 20'lik ortalamanın üstüne dönünce alır; iz süren 3×ATR stopla çıkar. Seçilen ayar: `{'fg_buy': 40}`. 1 hafta 100$: en kötü 94.31$, en iyi 105.29$, kazandıran hafta %20.7.
- **Takoz / Üçgen Kırılımı** — Son iki tepe ve iki dipten çizilen daralan formasyonun (düşen takoz, simetrik/yükselen üçgen) üst çizgisi kırılınca alır; isteğe bağlı hacim onayı. Seçilen ayar: `{'pivot_k': 5, 'vol_confirm': False, 'tp_atr': 100.0}`. 1 hafta 100$: en kötü 95.76$, en iyi 105.97$, kazandıran hafta %25.4.
- **Aktif Trend + Haber/Duygu Freni** — Aktif Trend botu; büyük ekonomik açıklamalar civarında ve aşırı açgözlülükte alım yapmaz. Seçilen ayar: `{'rsi_entry': 40.0, 'tp_atr': 2.0, 'fg_max': 90}`. 1 hafta 100$: en kötü 94.93$, en iyi 103.05$, kazandıran hafta %22.1.
- **Aktif Trend (RSI + Kırılım)** — Temkinli botun sık işlem yapan hâli: trendde RSI dönüşü veya 24 saatlik zirve kırılımında alır. Seçilen ayar: `{'rsi_entry': 40.0, 'tp_atr': 2.0}`. 1 hafta 100$: en kötü 94.93$, en iyi 103.05$, kazandıran hafta %22.1.
- **Formasyon Avcısı + Trend/Haber Freni** — Formasyon Avcısı; ama sadece fiyat EMA200 üstündeyken, büyük ekonomik açıklamalardan uzakta ve aşırı açgözlülük yokken alır. Seçilen ayar: `{'pivot_k': 3, 'tp_atr': 100.0, 'fg_max': 75}`. 1 hafta 100$: en kötü 95.73$, en iyi 113.53$, kazandıran hafta %25.4.
- **Yatay Direnç Kırılımı** — En az iki kez test edilmiş yatay direnç seviyesinin üstüne kapanış gelince alır. Seçilen ayar: `{'pivot_k': 5, 'tp_atr': 100.0}`. 1 hafta 100$: en kötü 96.39$, en iyi 107.02$, kazandıran hafta %33.8.
- **Gece Saati Etkisi (kontrol)** — Araştırmalardaki 'BTC gece 22:00–00:00 UTC yükselir' etkisi: trend yukarıysa 22:00'de alır, 00:00'da satar. Karşılaştırma için. Seçilen ayar: `{}`. 1 hafta 100$: en kötü 97.15$, en iyi 101.5$, kazandıran hafta %7.5.
- **EMA 9/21 Hızlı (15dk)** — 15 dakikalık mumlarda EMA9, EMA21'i yukarı kesince alır, aşağı kesince satar. Çok sık işlem; komisyonun etkisini gösterir. Seçilen ayar: `{'x_fast': 9, 'x_slow': 21}`. 1 hafta 100$: en kötü 94.96$, en iyi 100.52$, kazandıran hafta %3.8.
- **Connors RSI(2) Geri Çekilme** — Fiyat SMA200 üstündeyken RSI(2) çok düşünce (kısa sert düşüş) alır, fiyat 5'li ortalamanın üstüne çıkınca satar. Sık işlem yapar. Seçilen ayar: `{'rsi2_entry': 10.0, 'exit_len': 10}`. 1 hafta 100$: en kötü 96.26$, en iyi 102.92$, kazandıran hafta %18.3.
- **Fincan-Kulp** — Benzer iki tepe arasında yuvarlak dip (fincan) ve sığ geri çekilme (kulp) sonrası ağız kırılınca alır. Seçilen ayar: `{'pivot_k': 3, 'tp_atr': 3.0}`. 1 hafta 100$: en kötü 100.0$, en iyi 100.0$, kazandıran hafta %0.0.
- **BinH + Cluc (Freqtrade)** — Freqtrade topluluğunun ünlü dip alıcısı: 15 dakikada sert düşüşte Bollinger altından alır, kârdayken orta banda dönünce satar; %5 stop / %5 hedef. Seçilen ayar: `{}`. 1 hafta 100$: en kötü 99.37$, en iyi 100.22$, kazandıran hafta %6.1.
- **Ters Omuz-Baş-Omuz** — Sol omuz, daha derin baş, sağ omuz diplerinden sonra eğimli boyun çizgisi kırılınca alır. Seçilen ayar: `{'pivot_k': 5, 'tp_atr': 100.0}`. 1 hafta 100$: en kötü 97.55$, en iyi 106.0$, kazandıran hafta %9.4.
- **İkili Dip (W) Kırılımı** — İki benzer dip oluşur; aradaki tepenin (boyun çizgisi) üstüne kapanış gelince alır. Seçilen ayar: `{'pivot_k': 3, 'tp_atr': 100.0}`. 1 hafta 100$: en kötü 96.51$, en iyi 108.63$, kazandıran hafta %23.0.
- **Boğa Bayrağı / Flama** — Sert yükseliş (direk) sonrası dar dinlenmenin (bayrak) üstü kırılınca alır. Seçilen ayar: `{'pivot_k': 3, 'tp_atr': 3.0}`. 1 hafta 100$: en kötü 97.23$, en iyi 106.81$, kazandıran hafta %3.8.
- **Bollinger + RSI Dip Alımı** — Yükseliş trendinde fiyat alt Bollinger bandının altına ve RSI 30'un altına düşünce alır, orta banda dönünce satar. Seçilen ayar: `{'bb_k': 2.5, 'bb_rsi': 35.0}`. 1 hafta 100$: en kötü 98.29$, en iyi 101.04$, kazandıran hafta %15.0.
- **UT Bot Alerts + EMA200** — TradingView'in en popüler sinyal aracı: fiyat ATR iz süren stop çizgisini yukarı kesince alır, aşağı kesince satar. Seçilen ayar: `{'ut_key': 3.0, 'ut_atr': 14}`. 1 hafta 100$: en kötü 94.95$, en iyi 106.12$, kazandıran hafta %24.9.
- **Supertrend + EMA200** — TradingView Supertrend yukarı dönünce (fiyat EMA200 üstündeyse) alır, aşağı dönünce satar. Seçilen ayar: `{'st_mult': 3.0, 'st_len': 10}`. 1 hafta 100$: en kötü 96.79$, en iyi 106.12$, kazandıran hafta %25.8.
- **Squeeze Momentum (LazyBear)** — Bollinger bandı Keltner kanalına sıkışıp patlayınca, momentum yukarıysa alır; momentum zayıflayınca satar. Seçilen ayar: `{'sq_min_bars': 6, 'sq_kc': 1.5}`. 1 hafta 100$: en kötü 97.45$, en iyi 104.24$, kazandıran hafta %20.2.

_Geçmiş sonuç geleceği garanti etmez. Sanal test; yatırım tavsiyesi değildir._
