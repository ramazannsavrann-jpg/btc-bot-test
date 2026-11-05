# ÖN KAYIT DIŞI — KEŞİFSEL ANALİZ, KARAR DEĞİŞTİRMEZ

> Bu analizler v2/v2.1 ön kayıt sonucunu **değiştirmez**. Varyantlar arasından en iyi parametre **seçilmez** ve ana stratejiye dönüştürülmez. Yeni varyantlar deneme sayısına eklenmiştir (N = 266 + 4 = 270). Bütün sonuçlar spot BTCUSDT içindir; futures için geçerli değildir.

## Çalıştırma bilgisi

- Zaman 2026-11-05T13:02:55+00:00 · çalıştırma 42032270155-1 · commit `7a196f8c2bda539e967ca024d475ca435ef98484` · Python 3.12.16 · numpy 2.1.3
- Belgeler (SHA-256): `docs/ON_KAYIT_v2.md` dd485f666560…, `docs/ON_KAYIT_v2_1.md` 4a194a3ab5c7…, `docs/ON_KAYIT_v1.md` e6b23406a539…, `docs/ON_KAYIT_v1_DUZELTME_1.md` 3b6bfb4843ec…
- Veri: 80677 adet 1s mum (2017-08-17 → 2026-11-04), 115 dosya, CHECKSUM doğrulanan 115, veri özeti `0c7648569fa6e1fc…` (tam dosya listesi ve SHA-256'lar JSON'da)

## 1. Doğrulama testleri

**10/10 test geçti.**

| # | Test | Sonuç | Ayrıntı |
|---|---|---|---|
| 1 | Ön kayıt belgeleri ve düzeltme notu değişmemiş (SHA-256) | ✅ geçti | 4 belge |
| 2 | Motor dosyaları v1 doğrulamasını üreten kodla aynı | ✅ geçti | 9 dosya birebir (v1 sonuç commit'i b50bae2) |
| 3 | Arşiv dosyaları eksiksiz ve CHECKSUM uyuşmazlığı yok | ✅ geçti | 115 dosya, CHECKSUM doğrulanan 115 |
| 4 | Analiz simülasyonu (temel ENS) v2 hesabıyla birebir aynı | ✅ geçti | günlük değer ve işlem listesi, 1× ve 2× |
| 5 | v2 ilk çalıştırması (cebadcb) işlem işlem yeniden üretildi | ✅ geçti | 1x: 3365 gün, 144 ENS işlemi; 2x: 3365 gün, 145 ENS işlemi |
| 6 | Çıkış mutabakatı: sebeplerin toplamı işlem sayısına eşit | ✅ geçti | orta noktanın altı 120, stop 20, hedef 4 = 144 / 144 |
| 7 | Hedefsiz varyantta hiç hedef çıkışı yok ve yalnızca tp_atr değişti | ✅ geçti | tp_atr 100.0 → 1e+12, bo_len [120, 240, 360] |
| 8 | Parametre varyantlarında kırılım uzunlukları doğru uygulandı | ✅ geçti | {'15/30/45 gün': [90, 180, 270], '25/50/75 gün': [150, 300, 450], '30/60/90 gün': [180, 360, 540]} |
| 9 | Kötümser stop yaması çalıştırmadan sonra kaldırıldı (temel sonuç değişmedi) | ✅ geçti |  |
| 10 | Kötümser stop modeli uygulandı (stop dolumları değişti) | ✅ geçti | kötümser çalıştırmada 20 stop çıkışı |

## 2. Çıkış mutabakatı (ENS temel, 1×, tüm veri)

| Çıkış sebebi | Sayı |
|---|---|
| orta noktanın altı | 120 |
| stop | 20 |
| hedef | 4 |
| **Toplam** | **144** (işlem listesi: 144) |

Hedefle kapanan işlemler (kimlik = v2 ilk çalıştırmasındaki ve bu çalıştırmadaki işlem sırası):

| Kimlik | Giriş | Çıkış | Net kâr ($) | Kâr % |
|---|---|---|---|---|
| ENS-1x-18 | 2019-04-02 04:00 UTC | 2019-05-11 20:00 UTC | 26.91 | 74.7 |
| ENS-1x-19 | 2019-04-02 04:00 UTC | 2019-05-11 20:00 UTC | 26.50 | 74.7 |
| ENS-1x-40 | 2020-10-12 16:00 UTC | 2020-12-26 12:00 UTC | 126.11 | 120.3 |
| ENS-1x-41 | 2020-10-21 04:00 UTC | 2020-12-27 04:00 UTC | 93.47 | 120.9 |

Bu işlemlerin net kâr toplamı 273.0 $; tüm işlemlerin 1715.2 $. Gerçek etki için aşağıdaki baştan simülasyona bakın.

## 3. Hedefsiz ENS (tüm portföy baştan simüle edildi)

Tüm ölçüm dönemi (2017-12-01 → 2026-10-31):

| Maliyet | Strateji | Getiri | CAGR | MDD | Sharpe | Calmar | İşlem |
|---|---|---|---|---|---|---|---|
| 1x | ENS (temel) | %1555.5 | %36.99 | %28.4 | 1.28 | 1.30 | 144 |
| 2x | ENS (temel) | %1362.5 | %35.10 | %28.9 | 1.23 | 1.21 | 145 |
| 1x | Hedefsiz | %1618.0 | %37.56 | %28.4 | 1.27 | 1.32 | 143 |
| 2x | Hedefsiz | %1419.6 | %35.68 | %28.9 | 1.22 | 1.23 | 144 |
| 1x | VM-A | %680.8 | %25.92 | %59.9 | 0.76 | 0.43 | 158 |
| 2x | VM-A | %669.1 | %25.71 | %60.0 | 0.76 | 0.43 | 158 |

| Strateji | Maliyet | Dönem (zirve → dip) | ENS ayı MDD | VM-A ayı MDD | Avantaj | Göreli | Koruma şartı | ENS toparlanma | VM-A toparlanma |
|---|---|---|---|---|---|---|---|---|---|
| ENS (temel) | 1x | 2017-12-16 → 2018-12-15 | %24.0 | %58.1 | +34.0 puan | %58.6 | ✅ geçti | %300.2 | %301.8 |
| ENS (temel) | 1x | 2021-04-13 → 2021-07-20 | %11.6 | %26.8 | +15.3 puan | %57.0 | ✅ geçti | %16.0 | %47.3 |
| ENS (temel) | 1x | 2021-11-08 → 2022-11-21 | %21.5 | %59.9 | +38.4 puan | %64.1 | ✅ geçti | %150.1 | %291.7 |
| ENS (temel) | 2x | 2017-12-16 → 2018-12-15 | %24.4 | %58.2 | +33.8 puan | %58.1 | ✅ geçti | %292.4 | %299.7 |
| ENS (temel) | 2x | 2021-04-13 → 2021-07-20 | %11.5 | %26.8 | +15.3 puan | %57.0 | ✅ geçti | %15.5 | %47.2 |
| ENS (temel) | 2x | 2021-11-08 → 2022-11-21 | %22.3 | %60.0 | +37.7 puan | %62.8 | ✅ geçti | %137.4 | %291.0 |
| Hedefsiz | 1x | 2017-12-16 → 2018-12-15 | %24.0 | %58.1 | +34.0 puan | %58.6 | ✅ geçti | %308.2 | %301.8 |
| Hedefsiz | 1x | 2021-04-13 → 2021-07-20 | %7.8 | %26.8 | +19.1 puan | %71.1 | ✅ geçti | %16.0 | %47.3 |
| Hedefsiz | 1x | 2021-11-08 → 2022-11-21 | %21.4 | %59.9 | +38.6 puan | %64.3 | ✅ geçti | %151.3 | %291.7 |
| Hedefsiz | 2x | 2017-12-16 → 2018-12-15 | %24.4 | %58.2 | +33.8 puan | %58.1 | ✅ geçti | %301.0 | %299.7 |
| Hedefsiz | 2x | 2021-04-13 → 2021-07-20 | %7.7 | %26.8 | +19.1 puan | %71.3 | ✅ geçti | %15.5 | %47.2 |
| Hedefsiz | 2x | 2021-11-08 → 2022-11-21 | %22.2 | %60.0 | +37.8 puan | %63.0 | ✅ geçti | %138.2 | %291.0 |

v2 kuralı bilgi amaçlı uygulanırsa (hedefsiz): **Bütün şartlar sağlandı: ENS ayı piyasası koruma alternatifi olarak GEÇİCİ tercih edilir (keşifsel; nihai karar değil).**

## 4. Kötümser stop stres testi ve 1 dakikalık doğrulama

**Kötümser stop gerçekçi bir dolum modeli değildir; aşırı kötümser bir stres testidir.** Her stop çıkışı o 4 saatlik mumun en düşük fiyatından (üstüne kayma ve komisyon) doldurulur.

Tüm ölçüm dönemi:

| Maliyet | Strateji | Getiri | CAGR | MDD | Sharpe | Calmar | İşlem |
|---|---|---|---|---|---|---|---|
| 1x | ENS kötümser stop | %1392.8 | %35.41 | %28.7 | 1.23 | 1.23 | — |
| 2x | ENS kötümser stop | %1218.5 | %33.54 | %29.3 | 1.18 | 1.14 | — |
| 1x | ENS (temel) | %1555.5 | %36.99 | %28.4 | 1.28 | 1.30 | — |
| 2x | ENS (temel) | %1362.5 | %35.10 | %28.9 | 1.23 | 1.21 | — |

| Strateji | Maliyet | Dönem (zirve → dip) | ENS ayı MDD | VM-A ayı MDD | Avantaj | Göreli | Koruma şartı | ENS toparlanma | VM-A toparlanma |
|---|---|---|---|---|---|---|---|---|---|
| Kötümser stop | 1x | 2017-12-16 → 2018-12-15 | %24.2 | %58.1 | +33.9 puan | %58.4 | ✅ geçti | %298.4 | %301.8 |
| Kötümser stop | 1x | 2021-04-13 → 2021-07-20 | %13.5 | %26.8 | +13.3 puan | %49.6 | ✅ geçti | %15.2 | %47.3 |
| Kötümser stop | 1x | 2021-11-08 → 2022-11-21 | %22.1 | %59.9 | +37.8 puan | %63.1 | ✅ geçti | %149.7 | %291.7 |
| Kötümser stop | 2x | 2017-12-16 → 2018-12-15 | %24.5 | %58.2 | +33.6 puan | %57.8 | ✅ geçti | %290.5 | %299.7 |
| Kötümser stop | 2x | 2021-04-13 → 2021-07-20 | %13.5 | %26.8 | +13.3 puan | %49.7 | ✅ geçti | %14.7 | %47.2 |
| Kötümser stop | 2x | 2021-11-08 → 2022-11-21 | %23.0 | %60.0 | +37.0 puan | %61.7 | ✅ geçti | %137.0 | %291.0 |

v2 kuralı bilgi amaçlı uygulanırsa (kötümser stop): **Bütün şartlar sağlandı: ENS ayı piyasası koruma alternatifi olarak GEÇİCİ tercih edilir (keşifsel; nihai karar değil).**

### 4.2 Stop çıkışlarının 1 dakikalık veriyle kontrolü

1 dakikalık veri, stop'un 4 saatlik mum içinde ilk hangi dakikada tetiklendiğini gösterir. Ancak dakika içindeki sırayı ve gerçek emir defteri dolumunu **kesin olarak kanıtlamaz**. Dakika dolumu = min(o dakikanın açılışı, stop).

| Kimlik | Çıkış mumu | Aynı mumda giriş | Stop | Motor dolumu | İlk değen dakika | Dakika dolumu | Fark (bp) | Kötümser fark (bp) | Durum |
|---|---|---|---|---|---|---|---|---|---|
| ENS-1x-5 | 2018-05-16 00:00 UTC | hayır | 8147.76 | 8147.76 | 2018-05-16 02:24 UTC +144 dk | 8147.76 | 0.0 | -79.5 | doğrulandı |
| ENS-1x-8 | 2018-08-04 12:00 UTC | hayır | 6989.51 | 6989.51 | 2018-08-04 15:28 UTC +208 dk | 6989.51 | 0.0 | -55.1 | doğrulandı |
| ENS-1x-14 | 2019-02-24 12:00 UTC | hayır | 3789.56 | 3789.56 | 2019-02-24 14:15 UTC +135 dk | 3789.56 | 0.0 | -154.3 | doğrulandı |
| ENS-1x-26 | 2020-01-02 16:00 UTC | hayır | 6977.45 | 6977.45 | 2020-01-02 17:01 UTC +61 dk | 6977.45 | 0.0 | -75.5 | doğrulandı |
| ENS-1x-32 | 2020-06-11 16:00 UTC | hayır | 9145.62 | 9145.62 | 2020-06-11 16:59 UTC +59 dk | 9145.62 | 0.0 | -35.7 | doğrulandı |
| ENS-1x-48 | 2021-04-18 00:00 UTC | hayır | 54178.01 | 54178.01 | 2021-04-18 03:34 UTC +214 dk | 54178.01 | 0.0 | -599.3 | doğrulandı |
| ENS-1x-49 | 2021-04-18 00:00 UTC | hayır | 56553.87 | 56553.87 | 2021-04-18 03:20 UTC +200 dk | 56553.87 | 0.0 | -994.2 | doğrulandı |
| ENS-1x-51 | 2021-05-12 20:00 UTC | hayır | 50381.08 | 50381.08 | 2021-05-12 23:54 UTC +234 dk | 50381.08 | 0.0 | -353.5 | doğrulandı |
| ENS-1x-54 | 2021-09-07 12:00 UTC | hayır | 45210.41 | 45210.41 | 2021-09-07 15:08 UTC +188 dk | 45210.41 | 0.0 | -523.6 | doğrulandı |
| ENS-1x-63 | 2022-04-06 20:00 UTC | hayır | 43151.61 | 43151.61 | 2022-04-06 23:51 UTC +231 dk | 43151.61 | 0.0 | -7.1 | doğrulandı |
| ENS-1x-71 | 2022-08-19 04:00 UTC | hayır | 22330.82 | 22330.82 | 2022-08-19 06:37 UTC +157 dk | 22330.82 | 0.0 | -395.4 | doğrulandı |
| ENS-1x-93 | 2024-01-03 12:00 UTC | hayır | 41096.08 | 41096.08 | 2024-01-03 12:09 UTC +9 dk | 41096.08 | 0.0 | -84.2 | doğrulandı |
| ENS-1x-98 | 2024-04-12 16:00 UTC | hayır | 65985.69 | 65985.69 | 2024-04-12 18:35 UTC +155 dk | 65985.69 | 0.0 | -136.2 | doğrulandı |
| ENS-1x-102 | 2024-06-14 16:00 UTC | hayır | 65576.38 | 65576.38 | 2024-06-14 16:27 UTC +27 dk | 65576.38 | 0.0 | -76.0 | doğrulandı |
| ENS-1x-104 | 2024-08-01 12:00 UTC | hayır | 63546.62 | 63546.62 | 2024-08-01 15:17 UTC +197 dk | 63546.62 | 0.0 | -138.6 | doğrulandı |
| ENS-1x-107 | 2024-10-10 16:00 UTC | hayır | 59352.14 | 59352.14 | 2024-10-10 18:04 UTC +124 dk | 59352.14 | 0.0 | -68.4 | doğrulandı |
| ENS-1x-122 | 2025-08-18 00:00 UTC | hayır | 115365.04 | 115365.04 | 2025-08-18 02:51 UTC +171 dk | 115365.04 | 0.0 | -31.6 | doğrulandı |
| ENS-1x-126 | 2025-10-10 16:00 UTC | hayır | 117445.15 | 117445.15 | 2025-10-10 18:37 UTC +157 dk | 117445.15 | 0.0 | -127.1 | doğrulandı |
| ENS-1x-127 | 2025-10-10 20:00 UTC | hayır | 112317.46 | 112317.46 | 2025-10-10 21:13 UTC +73 dk | 112317.46 | 0.0 | -918.6 | doğrulandı |
| ENS-1x-132 | 2026-01-20 12:00 UTC | hayır | 90180.44 | 90180.44 | 2026-01-20 15:04 UTC +184 dk | 90180.44 | 0.0 | -35.6 | doğrulandı |

Özet: 20/20 stop doğrulandı; motor ile dakika dolumu arasındaki fark ortalama 0.0 bp, en kötü 0.0 bp. Kötümser modelin ortalama farkı -244.5 bp.

## 5. 2018–2020 hariç (1. ayı dönemi çıkarıldı)

Ölçüm 2020-11-24 (1. dönemin toparlanma günü) → 2026-10-31. Kalan büyük ayı dönemi: 2. v2 kuralına göre n < 3 olduğu için bu kesit **zaten karar veremez**; Yalnızca hassasiyet göstergesidir, karar değiştirmez.

Kesit sonuçları:

| Maliyet | Strateji | Getiri | CAGR | MDD | Sharpe | Calmar | İşlem |
|---|---|---|---|---|---|---|---|
| 1x | ENS (temel) | %307.1 | %26.68 | %23.3 | 1.04 | 1.15 | 103 |
| 2x | ENS (temel) | %268.6 | %24.58 | %24.7 | 0.97 | 1.00 | 104 |
| 1x | Hedefsiz | %314.1 | %27.05 | %26.9 | 1.03 | 1.00 | 104 |
| 2x | Hedefsiz | %274.8 | %24.93 | %28.1 | 0.97 | 0.89 | 105 |
| 1x | 15/30/45 gün | %299.4 | %26.28 | %30.9 | 1.04 | 0.85 | 129 |
| 2x | 15/30/45 gün | %252.2 | %23.63 | %32.6 | 0.96 | 0.73 | 130 |
| 1x | 25/50/75 gün | %312.9 | %26.99 | %27.9 | 1.04 | 0.97 | 79 |
| 2x | 25/50/75 gün | %290.1 | %25.78 | %28.6 | 1.01 | 0.90 | 79 |
| 1x | 30/60/90 gün | %318.4 | %27.27 | %20.0 | 1.03 | 1.36 | 66 |
| 2x | 30/60/90 gün | %296.4 | %26.11 | %20.8 | 1.00 | 1.25 | 66 |
| 1x | VM-A | %278.3 | %25.13 | %59.9 | 0.76 | 0.42 | 82 |
| 2x | VM-A | %275.6 | %24.97 | %60.0 | 0.75 | 0.42 | 82 |

| Strateji | Maliyet | Dönem (zirve → dip) | ENS ayı MDD | VM-A ayı MDD | Avantaj | Göreli | Koruma şartı | ENS toparlanma | VM-A toparlanma |
|---|---|---|---|---|---|---|---|---|---|
| ENS (temel) | 1x | 2021-04-13 → 2021-07-20 | %11.6 | %26.8 | +15.3 puan | %57.0 | ✅ geçti | %16.0 | %47.3 |
| ENS (temel) | 1x | 2021-11-08 → 2022-11-21 | %21.5 | %59.9 | +38.4 puan | %64.1 | ✅ geçti | %150.1 | %291.7 |
| ENS (temel) | 2x | 2021-04-13 → 2021-07-20 | %11.5 | %26.8 | +15.3 puan | %57.0 | ✅ geçti | %15.5 | %47.2 |
| ENS (temel) | 2x | 2021-11-08 → 2022-11-21 | %22.3 | %60.0 | +37.7 puan | %62.8 | ✅ geçti | %137.4 | %291.0 |
| Hedefsiz | 1x | 2021-04-13 → 2021-07-20 | %7.8 | %26.8 | +19.1 puan | %71.1 | ✅ geçti | %16.0 | %47.3 |
| Hedefsiz | 1x | 2021-11-08 → 2022-11-21 | %21.4 | %59.9 | +38.6 puan | %64.3 | ✅ geçti | %151.3 | %291.7 |
| Hedefsiz | 2x | 2021-04-13 → 2021-07-20 | %7.7 | %26.8 | +19.1 puan | %71.3 | ✅ geçti | %15.5 | %47.2 |
| Hedefsiz | 2x | 2021-11-08 → 2022-11-21 | %22.2 | %60.0 | +37.8 puan | %63.0 | ✅ geçti | %138.2 | %291.0 |
| 15/30/45 gün | 1x | 2021-04-13 → 2021-07-20 | %6.1 | %26.8 | +20.8 puan | %77.4 | ✅ geçti | %18.7 | %47.3 |
| 15/30/45 gün | 1x | 2021-11-08 → 2022-11-21 | %23.4 | %59.9 | +36.5 puan | %61.0 | ✅ geçti | %147.8 | %291.7 |
| 15/30/45 gün | 2x | 2021-04-13 → 2021-07-20 | %6.1 | %26.8 | +20.8 puan | %77.3 | ✅ geçti | %18.2 | %47.2 |
| 15/30/45 gün | 2x | 2021-11-08 → 2022-11-21 | %24.4 | %60.0 | +35.5 puan | %59.2 | ✅ geçti | %132.5 | %291.0 |
| 25/50/75 gün | 1x | 2021-04-13 → 2021-07-20 | %9.4 | %26.8 | +17.4 puan | %65.0 | ✅ geçti | %15.8 | %47.3 |
| 25/50/75 gün | 1x | 2021-11-08 → 2022-11-21 | %21.9 | %59.9 | +38.0 puan | %63.5 | ✅ geçti | %121.9 | %291.7 |
| 25/50/75 gün | 2x | 2021-04-13 → 2021-07-20 | %9.4 | %26.8 | +17.4 puan | %65.0 | ✅ geçti | %15.4 | %47.2 |
| 25/50/75 gün | 2x | 2021-11-08 → 2022-11-21 | %22.3 | %60.0 | +37.7 puan | %62.8 | ✅ geçti | %117.5 | %291.0 |
| 30/60/90 gün | 1x | 2021-04-13 → 2021-07-20 | %13.1 | %26.8 | +13.7 puan | %51.2 | ✅ geçti | %10.3 | %47.3 |
| 30/60/90 gün | 1x | 2021-11-08 → 2022-11-21 | %18.8 | %59.9 | +41.1 puan | %68.6 | ✅ geçti | %103.1 | %291.7 |
| 30/60/90 gün | 2x | 2021-04-13 → 2021-07-20 | %13.1 | %26.8 | +13.7 puan | %51.1 | ✅ geçti | %9.9 | %47.2 |
| 30/60/90 gün | 2x | 2021-11-08 → 2022-11-21 | %19.1 | %60.0 | +40.9 puan | %68.2 | ✅ geçti | %98.5 | %291.0 |

İşlem listeleri JSON'da: ENS 103 işlem, VM-A 82 işlem.

## 6. Parametre varyantları (en iyisi seçilmez)

Tüm ölçüm dönemi:

| Maliyet | Strateji | Getiri | CAGR | MDD | Sharpe | Calmar | İşlem |
|---|---|---|---|---|---|---|---|
| 1x | ENS (temel) | %1555.5 | %36.99 | %28.4 | 1.28 | 1.30 | 144 |
| 2x | ENS (temel) | %1362.5 | %35.10 | %28.9 | 1.23 | 1.21 | 145 |
| 1x | Hedefsiz | %1618.0 | %37.56 | %28.4 | 1.27 | 1.32 | 143 |
| 2x | Hedefsiz | %1419.6 | %35.68 | %28.9 | 1.22 | 1.23 | 144 |
| 1x | 15/30/45 gün | %1506.7 | %36.53 | %30.9 | 1.29 | 1.18 | 186 |
| 2x | 15/30/45 gün | %1272.0 | %34.14 | %32.6 | 1.22 | 1.05 | 187 |
| 1x | 25/50/75 gün | %1381.0 | %35.29 | %27.9 | 1.24 | 1.27 | 114 |
| 2x | 25/50/75 gün | %1268.9 | %34.10 | %28.6 | 1.20 | 1.19 | 114 |
| 1x | 30/60/90 gün | %1396.1 | %35.45 | %25.4 | 1.22 | 1.39 | 98 |
| 2x | 30/60/90 gün | %1289.3 | %34.33 | %25.7 | 1.19 | 1.34 | 98 |

| Strateji | Maliyet | Dönem (zirve → dip) | ENS ayı MDD | VM-A ayı MDD | Avantaj | Göreli | Koruma şartı | ENS toparlanma | VM-A toparlanma |
|---|---|---|---|---|---|---|---|---|---|
| 15/30/45 gün | 1x | 2017-12-16 → 2018-12-15 | %25.2 | %58.1 | +32.8 puan | %56.6 | ✅ geçti | %302.2 | %301.8 |
| 15/30/45 gün | 1x | 2021-04-13 → 2021-07-20 | %6.1 | %26.8 | +20.8 puan | %77.4 | ✅ geçti | %18.7 | %47.3 |
| 15/30/45 gün | 1x | 2021-11-08 → 2022-11-21 | %23.4 | %59.9 | +36.5 puan | %61.0 | ✅ geçti | %147.8 | %291.7 |
| 15/30/45 gün | 2x | 2017-12-16 → 2018-12-15 | %25.8 | %58.2 | +32.3 puan | %55.6 | ✅ geçti | %292.9 | %299.7 |
| 15/30/45 gün | 2x | 2021-04-13 → 2021-07-20 | %6.1 | %26.8 | +20.8 puan | %77.3 | ✅ geçti | %18.2 | %47.2 |
| 15/30/45 gün | 2x | 2021-11-08 → 2022-11-21 | %24.4 | %60.0 | +35.5 puan | %59.2 | ✅ geçti | %132.5 | %291.0 |
| 25/50/75 gün | 1x | 2017-12-16 → 2018-12-15 | %24.0 | %58.1 | +34.1 puan | %58.7 | ✅ geçti | %252.6 | %301.8 |
| 25/50/75 gün | 1x | 2021-04-13 → 2021-07-20 | %9.4 | %26.8 | +17.4 puan | %65.0 | ✅ geçti | %15.8 | %47.3 |
| 25/50/75 gün | 1x | 2021-11-08 → 2022-11-21 | %21.9 | %59.9 | +38.0 puan | %63.5 | ✅ geçti | %121.9 | %291.7 |
| 25/50/75 gün | 2x | 2017-12-16 → 2018-12-15 | %24.2 | %58.2 | +33.9 puan | %58.4 | ✅ geçti | %246.2 | %299.7 |
| 25/50/75 gün | 2x | 2021-04-13 → 2021-07-20 | %9.4 | %26.8 | +17.4 puan | %65.0 | ✅ geçti | %15.4 | %47.2 |
| 25/50/75 gün | 2x | 2021-11-08 → 2022-11-21 | %22.3 | %60.0 | +37.7 puan | %62.8 | ✅ geçti | %117.5 | %291.0 |
| 30/60/90 gün | 1x | 2017-12-16 → 2018-12-15 | %24.2 | %58.1 | +33.9 puan | %58.3 | ✅ geçti | %252.5 | %301.8 |
| 30/60/90 gün | 1x | 2021-04-13 → 2021-07-20 | %13.1 | %26.8 | +13.7 puan | %51.2 | ✅ geçti | %10.3 | %47.3 |
| 30/60/90 gün | 1x | 2021-11-08 → 2022-11-21 | %18.8 | %59.9 | +41.1 puan | %68.6 | ✅ geçti | %103.1 | %291.7 |
| 30/60/90 gün | 2x | 2017-12-16 → 2018-12-15 | %24.4 | %58.2 | +33.8 puan | %58.1 | ✅ geçti | %246.6 | %299.7 |
| 30/60/90 gün | 2x | 2021-04-13 → 2021-07-20 | %13.1 | %26.8 | +13.7 puan | %51.1 | ✅ geçti | %9.9 | %47.2 |
| 30/60/90 gün | 2x | 2021-11-08 → 2022-11-21 | %19.1 | %60.0 | +40.9 puan | %68.2 | ✅ geçti | %98.5 | %291.0 |

| Varyant | v2 kuralı bilgi amaçlı uygulanırsa |
|---|---|
| ENS (temel) | Bütün şartlar sağlandı: ENS ayı piyasası koruma alternatifi olarak GEÇİCİ tercih edilir (keşifsel; nihai karar değil). |
| Hedefsiz | Bütün şartlar sağlandı: ENS ayı piyasası koruma alternatifi olarak GEÇİCİ tercih edilir (keşifsel; nihai karar değil). |
| 15/30/45 gün | Bütün şartlar sağlandı: ENS ayı piyasası koruma alternatifi olarak GEÇİCİ tercih edilir (keşifsel; nihai karar değil). |
| 25/50/75 gün | Bütün şartlar sağlandı: ENS ayı piyasası koruma alternatifi olarak GEÇİCİ tercih edilir (keşifsel; nihai karar değil). |
| 30/60/90 gün | Bütün şartlar sağlandı: ENS ayı piyasası koruma alternatifi olarak GEÇİCİ tercih edilir (keşifsel; nihai karar değil). |

## 7. DSR (yeni denemeler dahil)

v1 ve v2 ile aynı yöntem (bot/overfit.deflated_sharpe), ölçüm 2023-11-01 → 2026-10-31; deneme seti v2'nin 252 serisi + 4 yeni varyant.

Etkin boyut: {'seri': 256, 'degisken_seri': 254, 'sabit_seri': 2, 'N_eff_katilim_orani': 8.6, 'N_eff_ort_korelasyon': 3.9, 'ort_korelasyon': 0.254, 'N_eff_kume': 51}

| Strateji | N_toplam=270 | N_eff_katilim | N_eff_ort_korelasyon | N_eff_kume |
|---|---|---|---|---|
| ENS (temel) | 0.000 | 0.012 | 0.144 | 0.000 |
| VM-A | 0.000 | 0.006 | 0.088 | 0.000 |
| Hedefsiz | 0.000 | 0.012 | 0.144 | 0.000 |
| 15/30/45 gün | 0.000 | 0.011 | 0.142 | 0.000 |
| 25/50/75 gün | 0.000 | 0.014 | 0.161 | 0.000 |
| 30/60/90 gün | 0.000 | 0.011 | 0.142 | 0.000 |

## 8. Notlar

- Kötümser stop, stop çıkışlarını mumun en düşük fiyatından doldurur. Gerçekçi değil, alt sınır stres testidir.
- 1 dakikalık veri tetiklenme dakikasını gösterir, dakika içi sırayı ve gerçek dolumu kanıtlamaz.
- Varyantlar keşifseldir. Hiçbiri ana stratejiye dönüştürülmez; değişiklik yeni ön kayıt ve kullanıcı onayı gerektirir.
- Bütün sonuçlar spot BTCUSDT; futures (funding, likidasyon, teminat) ayrı çalışma gerektirir.
- Hedefli ve hedefsiz farkı yalnızca tüm portföy baştan simüle edilerek ölçüldü; işlem kârlarının toplanması etki değildir.