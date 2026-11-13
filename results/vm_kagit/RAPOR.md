# VM-A Canlı Kâğıt Test (oynaklık hedefli BTC)

_SANAL paradır; gerçek emir verilmez. Yatırım tavsiyesi değildir. Kurallar: ön kayıt v2/v2.1 VM-A._

- Başlangıç: 05.11 16:20, BTC 80,390$ · son çalıştırma 13.11 22:22
- Bakiye: **90.21$** (-9.79%) · aynı sürede BTC al-tut -14.29% · BTC ağırlığı %98.9
- İşlem sayısı: 1 · bekleyen emir: yok
- Veri: Binance (data-api.binance.vision)

Son gün sonu kararı (13.11 03:00): σ %37.6, hedef %99.0, mevcut ağırlık %98.9 → bant içinde, işlem yok

## ENS ile karşılaştırma (aynı zaman damgaları)

Canlı ENS botu (Kırılım Ansamblı) 05.11 12:55 başladı; 7 günlük testi 12.11 12:55 tarihinde biter (mevcut bot değiştirilmedi). ENS'de canlı %10 düşüş freni açık, VM-A'da yok (v2.1). Asıl ileri karşılaştırma, aynı kurallarla hesaplanan ön kayıt v2 hesabıdır.

Ortak dönem 05.11 16:20 → 12.11 13:46 (173 eşleşen kayıt, en fazla 20 dk fark):

| Bot | Başlangıç | Son | Getiri |
|---|---|---|---|
| VM-A | 100.00$ | 96.37$ | -3.63% |
| ENS | 100.00$ | 100.00$ | +0.00% |
| BTC | 80,390$ | 73,661$ | -8.37% |

## İşlemler (son 20)

| Yön | Sinyal | Dolum mumu | Mum açılışı | 1 dk referans | Fark | Dolum (kayma dahil) | Adet | Hedef |
|---|---|---|---|---|---|---|---|---|
| ALIM | 06.11 03:00 | 06.11 03:00 | 76,088.01 | 76,234.60 | +0.193% | 76,272.72 | 0.001297 | %99 |

## Dolum kayıtları (gerçekçi dolum, son 10)

| Olay | Sinyal | Karar anı | Kayıt anı | Gecikme (dk) | 1 dk mum | Mum fiyatı | Referans | Fark % |
|---|---|---|---|---|---|---|---|---|
| vm_al | 06.11 03:00 | 06.11 03:31 | 06.11 07:31 | 31.9 | 06.11 03:31 | 76088.01 | 76234.6 | 0.1927 |

1 dakikalık mum kapanışı gerçek işlem fiyatı değildir; bu bir simülasyondur.

## Günlük

- 06.11 03:00 ALIM 0.001297 BTC @ 76,273$ (hedef ağırlık %99, sinyal 06.11 03:00)
- 05.11 16:20 Test başladı. BTC 80,390$, sanal bakiye 100$. Geçmişte işlem yapılmaz.

## Günlük karşılaştırma (aynı başlangıç: ortak ilk kayıtta ikisi de 100)

İkisi de ortak ilk kayıtta 100'e eşitlenir; her gün, iki botun en fazla 20 dk arayla eşleşen son kaydı kullanılır. Değerler piyasa değeri esasındadır (nakit + adet × fiyat). Eşleşen kayıt olmayan gün tahmin edilmez, 'eksik' yazılır.

| Gün | Kayıt | VM-A | ENS | BTC |
|---|---|---|---|---|
| 2026-11-05 | 05.11 23:53 | 100.00 | 100.00 | 95.00 |
| 2026-11-06 | 06.11 23:22 | 99.40 | 100.00 | 94.40 |
| 2026-11-07 | 07.11 23:57 | 99.29 | 100.00 | 94.30 |
| 2026-11-08 | 08.11 23:56 | 99.46 | 100.00 | 94.45 |
| 2026-11-09 | 09.11 23:11 | 98.09 | 100.00 | 93.14 |
| 2026-11-10 | 10.11 23:24 | 96.27 | 100.00 | 91.40 |
| 2026-11-11 | 11.11 22:59 | 96.94 | 100.00 | 92.04 |
| 2026-11-12 | 12.11 13:46 | 96.51 | 100.00 | 91.63 |
