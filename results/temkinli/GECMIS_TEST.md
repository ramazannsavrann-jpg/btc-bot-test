# Geçmiş Test (Backtest) Sonucu

Veri: Binance arşivi (data.binance.vision), 2024-11-01 → 2026-10-31 (17520 saatlik mum)

Ayarlar 2024-11-01 → 2026-03-26 arasında seçildi, sonra botun **hiç görmediği** 2026-03-27 → 2026-10-31 döneminde denendi.

Seçilen ayar: RSI giriş 30.0, stop 2.5×ATR, hedef 3.0×ATR, zirve kırılımı kapalı

## Görülmemiş dönemde 100$

| | Bot (seçilen ayar) | Bot (varsayılan ayar) |
|---|---|---|
| Son bakiye | 105.24$ | 95.87$ |
| Getiri | %5.24 | %-4.13 |
| İşlem sayısı | 7 | 21 |
| Başarı oranı | %85.7 | %47.6 |
| En büyük düşüş | %1.56 | %4.53 |
| Aynı dönem BTC al-tut | %12.73 | %12.73 |

## 100$ bir haftada ne olur? (görülmemiş dönem, her gün başlayan 7 günlük denemeler)

| | Bot | Sadece BTC alıp tutmak |
|---|---|---|
| Deneme sayısı | 213 | 213 |
| Tipik sonuç (ortanca) | 100.0$ | 100.3$ |
| En kötü hafta | 99.43$ | 82.41$ |
| En iyi hafta | 101.33$ | 124.26$ |
| Kötü %10'luk dilim | 100.0$ | 95.43$ |
| İyi %10'luk dilim | 101.03$ | 106.39$ |
| Kazandıran hafta oranı | %18.3 | %51.6 |

_Komisyon (%0,1) ve kayma (%0,05) dahildir. Geçmiş sonuç geleceği garanti etmez._
