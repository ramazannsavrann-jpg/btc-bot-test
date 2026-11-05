# Ön Kayıt v1: Düzeltme Notu 1 (hedef fiyat)

**Statü:** Bu not, v1 ön kaydından **sonra** (2026-11-05), v1 ve v2 sonuçları görüldükten sonra yazıldı. İlk ön kayıtla **aynı statüde değildir**. v1'i başından beri doğru kaydedilmiş gibi göstermez.

`docs/ON_KAYIT_v1.md` **değiştirilmedi** (SHA-256 `e6b23406a5397c7d4d77004b5d52d9e79a8ce0cf89038288e5ae9411d3745b2f`). v2 ve v2.1 de değiştirilmedi.

## Hata

v1 §1 Kırılım Ansamblı için "**Hedef fiyat yok**" diyor. Bu yanlış.

Kodda (`bot/research_candidates.py`, `TREND_EXIT = {"tp_atr": 100.0, ...}`) her alt sistemde **hedef = giriş fiyatı + 100 × ATR(14)** vardır. Hedef, motorda (`bot/strategy.py`) mum içinde en yüksek fiyat hedefe ulaşınca çalışır ve max(açılış, hedef) fiyatından dolar. Aynı mumda stop da tetiklenmişse stop önce sayılır.

v1, v2 ve v2.1'in bütün hesapları bu kodla yapıldı. Yani **hesaplar kodla tutarlı, belgedeki tarif eksik ve yanlış.** v1'in hesap sonuçları bu nedenle otomatik olarak geçersiz olmaz. Ama "v1 belgesi stratejiyi eksiksiz ve doğru tanımlar" iddiası artık geçerli değildir.

## Etkilenen işlemler

**Kaynak:** v2 ilk çalıştırması.
- Rapor: `results/v2/20261105T124818Z_42030216089-1/sonuc.json`
- Commit: `cebadcb`
- Uzun ve kesintisiz simülasyon, 1× maliyet, 2017-08-17 → 2026-11-04.

İşlem kimliği, o dosyadaki `kayitlar.1x.ens_islemler` listesindeki sıra numarasıdır (0'dan başlar).

**Çıkış mutabakatı:**

| Çıkış sebebi | Sayı |
|---|---|
| Orta noktanın altı | 120 |
| Stop | 20 |
| Hedef (giriş + 100×ATR) | 4 |
| **Toplam** | **144** |

**Hedefle kapanan 4 işlem:**

Her satır ayrı bir alt sistemin işlemidir. Kâr, o alt sistemin sermayesi üzerinden net $ cinsindendir; portföy 100 $ ile başladı.

| Kimlik | Giriş (UTC) | Çıkış (UTC) | Giriş fiyatı | Çıkış fiyatı | Adet | Net kâr ($) | Kâr % |
|---|---|---|---|---|---|---|---|
| ENS-1x-18 | 2019-04-02 04:00 | 2019-05-11 20:00 | 4.181,07 | 7.319,26 | 0,00860801 | 26,91 | 74,7 |
| ENS-1x-19 | 2019-04-02 04:00 | 2019-05-11 20:00 | 4.181,07 | 7.319,26 | 0,00847406 | 26,50 | 74,7 |
| ENS-1x-40 | 2020-10-12 16:00 | 2020-12-26 12:00 | 11.555,16 | 25.505,86 | 0,00906398 | 126,11 | 120,3 |
| ENS-1x-41 | 2020-10-21 04:00 | 2020-12-27 04:00 | 12.188,39 | 26.972,74 | 0,00633899 | 93,47 | 120,9 |

- Bu 4 işlemin net kârı toplam 273,0 $. Bu, 144 işlemin toplam net kârının (1.715,2 $) yaklaşık %15,9'u.
- **Bu oran hedefin katkısı değildir.** Hedef olmasaydı bu pozisyonlar başka bir zamanda ve fiyatta kapanacak, sonraki sinyaller de değişecekti. Hedefin gerçek etkisi yalnızca hedefsiz bir versiyonun **baştan simülasyonuyla** ölçülebilir; bu, ek analizde (B) yapılır.
- **Zamanlama:**
  - Mayıs 2019 çıkışları, v2'nin 1. ayı döneminin toparlanma aşamasına düşer (dip 2018-12-15 → toparlanma 2020-11-24).
  - Aralık 2020 çıkışları bu dönemin toparlanma gününden **sonradır**; hiçbir ayı dönemi penceresine girmez, yalnızca tüm dönem CAGR'sini etkiler.
  - Her iki tarih de v1'in 2018–2022 stres testi penceresindedir. v1'in ana döneminde (2023-11 → 2026-10) hedef çıkışı yoktur.

## Yapılacak

- Hedefsiz versiyon (tp_atr → etkisiz), yeni bir strateji varyantı olarak tüm portföy baştan simüle edilerek hesaplanır. Sonuç "ön kayıt dışı, keşifsel, karar değiştirmez" diye etiketlenir ve deneme sayısına eklenir.
- Canlı ve ön kayıtlı strateji **değişmez**. Hedef kuralını kaldırmak veya değiştirmek yeni bir ön kayıt ve kullanıcı onayı gerektirir.
- Kural tariflerinin kodla birebir eşleşmesi bundan sonraki ön kayıtlarda ayrıca test edilir: belgedeki parametre tablosu ile koddaki etkin parametrelerin karşılaştırılması.
