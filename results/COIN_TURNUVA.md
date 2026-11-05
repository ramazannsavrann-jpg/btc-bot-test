# 🪙 30 Coin Turnuvası

Coin listesi, testin başındaki (Kasım 2024) hacme göre seçildi (bugünün kazananlarını seçip sonucu şişirmemek için): BTC, ETH, DOGE, SOL, XRP, PEPE, PNUT, BNB, ADA, SUI, NEIRO, SHIB, WIF, XLM, ACT, BONK, WLD, AVAX, FLOKI, NEAR, DOT, HBAR, BOME, FET, ARB, TRX, LTC, APT, ENA, SEI

Ayarlar **2024-11-11 → 2026-03-27** döneminde seçildi; sonuçlar botun **hiç görmediği** **2026-03-27 → 2026-10-31** dönemine ait. Komisyon %0,1; kayma büyük coinlerde %0,05, orta %0,1, küçük %0,2.

| # | Bot | 100$ → | 2× maliyetle | Haftada işlem | Başarı | En büyük düşüş | BTC al-tut | 1 haftada tipik | Puan |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 30 Coin Momentum Rotasyonu | 73.94$ | 61.53$ | 8.66 | %31.4 | %49.69 | %12.73 | 99.67$ | -0.6 |
| 2 | 30 Coin Akıllı Skor | 78.58$ | 69.05$ | 9.78 | %30.4 | %28.75 | %12.73 | 98.74$ | -0.833 |
| 3 | 30 Coin Donchian Tarayıcı | 69.53$ | 52.97$ | 9.05 | %28.6 | %32.12 | %12.73 | 98.34$ | -0.97 |

## Ayrıntı

- **30 Coin Momentum Rotasyonu** — Her gün son günlerin en güçlü coinlerini (EMA200 üstünde olanlar) eşit ağırlıkla tutar, güçten düşeni satar. BTC düşüş trendindeyse nakde geçer. Ayar: `{'rot_k': 5, 'mom_len': 72}`. 1 hafta 100$: en kötü 89.43$, en iyi 139.17$, kazandıran hafta %33.5. En çok kazandıran: [('BOME', 7.43), ('ENA', 4.31), ('PNUT', 4.25)]; en çok kaybettiren: [('NEAR', -6.78), ('HBAR', -6.9), ('BONK', -11.5)].
- **30 Coin Akıllı Skor** — 30 coinin her birine trend, göreceli güç, momentum, kırılım, formasyon, hacim ve RSI'dan 8 üzerinden puan verir; eşik üstündekilerin en iyilerine girer. BTC yönü, haber ve duygu freni açık. Ayar: `{'score_min': 7, 'max_pos': 5}`. 1 hafta 100$: en kötü 91.67$, en iyi 117.34$, kazandıran hafta %25.5. En çok kazandıran: [('PNUT', 6.52), ('SUI', 4.04), ('SEI', 2.03)]; en çok kaybettiren: [('WLD', -5.0), ('APT', -5.53), ('FLOKI', -5.98)].
- **30 Coin Donchian Tarayıcı** — 30 coinde zirve kırılımı arar (trend + haber/duygu freni), en güçlü momentumlu olanlara girer. Ayar: `{'dc_len': 48, 'max_pos': 3}`. 1 hafta 100$: en kötü 90.4$, en iyi 125.74$, kazandıran hafta %25.9. En çok kazandıran: [('SEI', 6.36), ('ARB', 5.03), ('PNUT', 3.28)]; en çok kaybettiren: [('HBAR', -4.26), ('TRX', -5.77), ('NEAR', -7.31)].

_Geçmiş sonuç geleceği garanti etmez. Sanal test; yatırım tavsiyesi değildir._
