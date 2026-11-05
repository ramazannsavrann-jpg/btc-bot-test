# Ön Kayıt v1 — Kırılım Ansamblı (4s) Doğrulama Planı

**Durum:** Testler ÇALIŞTIRILMADAN önce yazıldı ve GitHub'a gönderildi. Bu belge sonradan değiştirilmez.
Sonradan yapılan her değişiklik yeni bir sürüm (`ON_KAYIT_v2.md` …) olarak eklenir ve raporda
**"ön kayıt dışı"** diye işaretlenir. Kanıt: bu dosyanın SHA-256 özeti, commit hash'i, `on-kayit-v1`
etiketi (tag) ve GitHub Actions sunucusunun yazdığı zaman damgası (`docs/ON_KAYIT_v1_zaman.txt`).

Hazırlayanlar: Claude (kod), ChatGPT (denetim) ve proje sahibi (onay). Tarih: 2026-11-05.
Kod tabanı: commit `4242f33837da0c35bdfc44ac9bee9b4d4f32af08` (bu belgenin üst commit'i).

---

## 0. Değişmeyecek olanlar

- Stratejilerin sinyal mantığı, işlem kuralları ve mevcut sonuçlar değişmez. Yeni indikatör ya da strateji eklenmez.
- Canlı kâğıt testteki botlar ve kayıtları silinmez veya sıfırlanmaz.
- Geleceği görme kontrolleri (veri kesme testi) ve işlem tekrarını önleme (son işlenen mum kaydı) korunur.
- Hiçbir parametre, sonucu iyileştirmek için sonradan değiştirilmez.

## 1. Test edilen strateji (kurallar koddan birebir)

**Kırılım Ansamblı (4s)** — `bot/research_candidates.py` içindeki `kirilim_ansambl`, `bot/ensemble.py` motoru.

- 3 alt sistem, her biri başlangıç sermayesinin 1/3'ü ile bağımsız çalışır. `bo_len` = 120 / 240 / 360 adet 4 saatlik mum (= 20 / 40 / 60 gün).
- **Giriş:** 4s mum kapanışı, önceki `bo_len` mumun en yüksek kapanışını geçerse; işlem bir sonraki mumun açılışında.
- **Çıkış:** kapanış, son `bo_len` mumun en yüksek ve en düşük kapanışının orta noktasının altına inerse. Orta nokta yalnızca yukarı taşınır.
  - Ek stop: giriş − 6×ATR(14).
  - Süre stopu: 2880 saat (120 gün).
  - Hedef fiyat yok; başa-baş kuralı yok.
- **Büyüklük:** alt sistem sermayesi × min(0,99 ; 0,40 / σ). σ = son 90 günün (540 mum) 4s getirilerinden yıllıklanmış oynaklık. Ağırlık asla %100'ü geçmez (spot, kaldıraç yok).
- **Maliyet:** komisyon %0,10 ve kayma %0,05, her alış ve satışta ayrı.
- **Diğer:** 3 ardışık kayıpta 24 saat mola. Girişler EMA50, EMA200, RSI(14) ve ATR(14) ısınmış olmadan yapılmaz (motorun mevcut davranışı).
- Canlı testte %10 hesap düşüş freni açık; geçmiş testlerde kapalı (mevcut araştırmayla aynı).

## 2. Veri ve dönemler

- **Kaynak:** Binance spot BTCUSDT, `data.binance.vision` aylık arşivleri. 1 saatlik mumlar UTC'ye hizalı 4 saatlik mumlara birleştirilir; yalnızca 4 parçası tam olan mumlar kullanılır.
- **Veri kontrolü:** eksik ve tekrarlı mum sayısı raporlanır. Tekrarlı mumlar tekilleştirilir, eksik mumlar doldurulmaz.
- **Ana dönem:**
  - Simülasyon 2022-11-01'de başlar.
  - Ölçüm **2023-11-01 00:00 UTC → 2026-10-31 23:59 UTC** (36 ay). Önceki walk-forward sınav dönemiyle aynı; son gün 2026-10-31 olarak yazılır.
  - İlk 12 ay yalnızca ısınma ve geçmiştir, ölçüme girmez.
- **Stres testi:**
  - Ölçüm **2018-01-01 → 2022-10-31**.
  - Isınma için 2017-08-17'den (Binance BTCUSDT başlangıcı) itibaren gerçek veri.
  - Bu dönem hiçbir parametre seçiminde kullanılmaz.
  - Sınırlamalar raporda belirtilir: 2017–2019 likiditesi daha düşüktü, piyasa yapısı farklıydı, BTCUSDT hacmi daha azdı.
- **Günlük özsermaye:** her UTC gününün son 4s mum kapanışındaki değer.
- **Nakit getirisi:** %0 (USDT). Bütün karşılaştırmalarda aynı.

## 3. Benchmark'lar

Hepsine aynı komisyon ve kayma uygulanır (alım ve yeniden dengeleme tutarı üzerinden), nakit getirisi %0.

| Kod | Tanım | Kullanım |
|---|---|---|
| B100 | %100 BTC al-tut | **Sharpe kıyası** |
| S25 / S50 / S75 | Başlangıçta %25/50/75 BTC, sonra dokunulmaz | Ek bilgi |
| M25 / M50 / M75 | Her ayın ilk günü %25/50/75'e yeniden dengelenen | Ek bilgi |
| WM | Ağırlık eşleştirilmiş: ansamblın günlük gerçekleşen **BTC sermaye ağırlığının** (BTC değeri / özsermaye) dönem ortalaması, aylık dengelenen | İkincil karar ölçütü. Ortalama dönem sonunda bilindiği için **geriye dönük (ex-post)** bir kıyastır. |
| VM | Oynaklık eşleştirilmiş BTC: her gün w = min(1, σ_ens / σ_btc); her iki σ da **o güne kadarki** son 90 günün günlük getirilerinden. \|Δw\| > 0,05 olursa yeniden dengelenir. | **CAGR, MDD, Calmar için birincil kıyas** |

"Piyasada kalma oranı" (pozisyonda geçen zaman) ile "BTC sermaye ağırlığı" ayrı ayrı raporlanır ve birbirine karıştırılmaz.

## 4. Ölçümler

- CAGR, maksimum düşüş (MDD), Calmar, Sortino, toparlanma süresi, işlem sayısı, piyasada kalma oranı, ortalama BTC ağırlığı.
- **Sharpe:** günlük getiriler, ×√365, risksiz getiri 0.
- **Otokorelasyon düzeltmeli Sharpe:** Lo (2002) yöntemiyle, q = 10 gecikme. Yıllıklama çarpanı η(q) = q / √(q + 2·Σ_{k=1}^{q−1} (q−k)·ρ_k), ρ_k = günlük getiri otokorelasyonu.
- **HAC / Newey-West:** günlük ortalama getirinin standart hatası. Bartlett çekirdeği, gecikme L = ⌊4·(T/100)^(2/9)⌋. Ortalama getiri için t-istatistiği ve %95 güven aralığı.
- **PSR (olasılıksal Sharpe):** ansamblın kendi Sharpe'ının 0'dan büyük olma olasılığı; çarpıklık ve basıklık düzeltmeli. Bu, seçim riskinden **ayrı** raporlanır.

## 5. Bootstrap

Rastgele tohum: **20261105**. Bütün dağılımlar için ortanca, %5 ve %95 yüzdelikleri, ayrıca P(fark > 0) raporlanır.

**A — Strateji getirisi bootstrap'ı (destekleyici, karar ölçütü değil)**
- Stationary bootstrap (Politis–Romano), ortalama blok 7 / 14 / 30 gün, her biri 10.000 örnek.
- Ansambl ve bütün benchmark'ların günlük getirileri **aynı gün indeksleriyle birlikte** örneklenir.
- Ölçümler: CAGR, Sharpe, Sortino, Calmar, MDD ve benchmark farkları.
- Sınırlama: strateji kararlarını yeniden üretmez, sadece gerçekleşmiş getiri yolunun sırasını karıştırır.

**B — Fiyat yolu bootstrap'ı (karar ölçütü)**
- 4 saatlik mumlar, bir önceki kapanışa göre göreli (açılış, en yüksek, en düşük, kapanış) oranları olarak, **birlikte** örneklenir.
- Stationary bootstrap, ortalama blok **360 mum (ana senaryo)**, ayrıca 180 ve 540 mum.
- Kaynak havuz: ana ölçüm dönemindeki gerçek 4s mumlar. Yol uzunluğu: ana ölçüm dönemiyle aynı.
- Isınma: en uzun pencere ihtiyacına göre belirlenir. Max(360 kırılım, 540 oynaklık, 200 EMA) + 60 = **600 mum**, ölçüm başlangıcından hemen önceki gerçek veriden alınır.
- Ansambl ve B100, VM, WM her yolda baştan çalıştırılır: göstergeler, sinyaller, büyüklük, stoplar ve işlemler yeniden hesaplanır.
- Yol sayısı: **2.000**, ayrıca aynı tohumla ilk 1.000 yolun sonuçları. Monte Carlo belirsizliği: olasılıklar için √(p(1−p)/n); yüzdeliklerin kararlılığı 1.000 ile 2.000 karşılaştırılarak.
- **Tutarlılık kontrolleri:**
  - Her sentetik mumda en yüksek ≥ max(açılış, kapanış) ve en düşük ≤ min(açılış, kapanış).
  - Blok sınırlarındaki yapay fiyat boşlukları (açılış / önceki kapanış − 1) ayrıca ölçülür ve gerçek veriyle karşılaştırılır.
  - Sentetik ile gerçek yolların karşılaştırması:
    - oynaklık kümelenmesi (|getiri| otokorelasyonu, gecikme 1–10 ortalaması)
    - trend uzunlukları (20 günlük getiri işaretinin ortalama koşu uzunluğu)
    - MDD dağılımı
    - açılış boşlukları

## 6. Ezber riski — DSR ve etkin deneme sayısı

- Korelasyon matrisi: ölçüm dönemine hizalanmış günlük getiriler.
- Matrise giren seriler:
  - araştırmadaki 69 BTC strateji×ayar
  - önceki BTC turnuvalarının adayları: 126 ayar (`bot/candidates.py`) ve temkinli botun 54 ayarlık tablosu (`bot/backtest.py`). Bunlar sabit ayarla aynı dönemde yeniden simüle edilir.
- **Etkin boyut tahminleri** (gerçek bağımsız deneme sayısı değil, etkin boyut tahmini):
  - (1) **Ana tahmin:** özdeğer katılım oranı (Σλ)² / Σλ²
  - (2) Ortalama korelasyon: N / (1 + (N−1)·ρ̄)
  - (3) Hiyerarşik kümeleme (uzaklık 1−ρ, ortalama bağlantı), ρ > 0,7 eşiğinde küme sayısı
- **DSR** ayrı ayrı: N = 10, 20, 40, 69, N_eff(1), N_eff(2), N_eff(3) ve **N_toplam = 263**.
  - N_toplam: 69 + 126 + 54 + 30 coin turnuvasının 14 ayarı.
  - 30 coin botları çok varlıklı oldukları için korelasyon matrisine giremez; sadece deneme sayısına eklenir.
- Başarısız olanlar dahil bütün denemeler sayılır.
- Ansambl için iki ayrı değerlendirme:
  - (a) Kendi sabit kurallı performansı (PSR, HAC)
  - (b) Adaylar arasından seçilmiş olmasının yarattığı seçim riski (DSR, PBO)

## 7. Gecikmeli dolum

- **Geçmiş test:** Sinyale dayalı dolumlar (girişler, orta nokta çıkışı, süre çıkışı) bir sonraki 4s mumun açılışından **+15, +30 ve +60 dakika** sonraki fiyattan yapılır. Ana kaynak **1 dakikalık** Binance verisi: o dakikada kapanan 1 dakikalık mumun kapanışı. Ek kontrol olarak 15 dakikalık mumlar kullanılır.
- Stop dolumları gecikmeli sayılmaz; gerçek bota geçildiğinde borsada bekleyen stop emri olarak çalışacaklar.
- Fiyat farkı ayrı bir kalem olarak raporlanır. Komisyon ve kayma ayrı uygulanır ve **iki kez sayılmaz**: kayma yalnızca bir kez, dolum fiyatına uygulanır.
- **Canlı kâğıt test (bu sürümden itibaren, yalnızca yeni işlemler):**
  - Dolum referansı, çalışma anındaki **son kapanmış 1 dakikalık mumun kapanışı** olur.
  - Kaydedilenler: sinyal zamanı, çalışma zamanı, veri zamanı, 1 dakikalık mumun zaman damgası, referans fiyat, 4s mum açılışı ve aradaki fark.
  - Raporda belirtilecek: "Bu bir simülasyondur; mum kapanış fiyatı gerçek işlem fiyatı değildir."
  - Önceki işlemler değiştirilmez; kural değişikliği tarihi raporda yazılır.

## 8. Pozisyon taşıma testi

- **Ansambl:** ayar seçimi olmadığı için 2022-11 → 2026-10 boyunca **tek ve kesintisiz** simülasyon; yapay pencere kapanışı yok.
- **Ayar seçen stratejiler** (araştırmadaki 1s ve 4s adaylar):
  - A = pencere sonunda kapat (mevcut)
  - B = açık pozisyon taşınır ve açıldığı penceredeki ayarlarla yönetilir; yeni ayarlar yalnızca yeni girişlerde geçerli olur
- A ve B aynı tablolarda karşılaştırılır.

## 9. Günlük rejim analizi

Her gün d için, yalnızca d−1'e kadarki günlük kapanışlarla:

- **Yön:**
  - Yükseliş: kapanış > EMA200 ve EMA50(d−1) − EMA50(d−11) > 0
  - Düşüş: kapanış < EMA200 ve bu eğim < 0
  - Diğer durumlar: Yatay/kararsız
- **Oynaklık:** 30 günlük gerçekleşen oynaklık, son 365 günün 30 günlük oynaklıklarının ortancasına göre:
  - > 1,25× ise yüksek
  - < 0,80× ise düşük
  - arada ise normal
- Her rejim için raporlananlar:
  - gün sayısı ve ayrı dönem (ardışık blok) sayısı
  - toplam log getiri, Sharpe, rejim günleri birleştirilerek MDD
  - o rejimde açılan işlem sayısı
  - piyasada kalma oranı, ortalama BTC ağırlığı
- B100 ile yan yana gösterilir.

## 10. Volatilite hedefi karşılaştırması

Aynı ansambl kuralları, aynı veri, maliyet ve risk sınırlarıyla **%20, %30, %40** yıllık hedef. Ağırlık her zaman ≤ %99. Hepsi ana dönemde ve B bootstrap'ında (360 mum, 2.000 yol) raporlanır. "En istikrarlı" sonucu; bootstrap Calmar ortancası ve %5 yüzdeliği ile MDD'nin %95 yüzdeliğine göre değerlendirilir.

**Not:** Bu karşılaştırma bilgi amaçlıdır. Ön kayıttaki karar **yalnızca %40 hedefli mevcut ansambl** için verilir. Farklı bir hedefe geçmek yeni bir ön kayıt gerektirir.

## 11. Gerçek paraya geçiş için ön kayıtlı eşikler

Karar kaynağı: B bootstrap'ı, 360 mum blok, 2.000 yol. A bootstrap'ı yalnızca destekleyicidir; iki sonuç tek orana birleştirilmez.

| # | Şart | Eşik |
|---|---|---|
| 1 | P(Sharpe_ansambl − Sharpe_B100 > 0) | ≥ %90 |
| 2 | P(Calmar_ansambl − Calmar_VM > 0) | ≥ %90 |
| 3 | P(Sharpe_ansambl − Sharpe_WM > 0) | ≥ %90 |
| 4 | P(MDD_ansambl < MDD_B100) | ≥ %90 |
| 5 | Ana dönemde 2× maliyetle toplam net getiri | > 0 |
| 6 | 2018–2022 stres testinde MDD | ≤ %40, özsermaye hiçbir an başlangıcın %50'sinin altına inmez |
| 7 | Canlı kâğıt test | En az **12 ay VE en az 20 tamamlanmış işlem** (hangisi daha geç biterse) |
| 8 | Operasyonel doğruluk | Canlı işlemler aynı veriyle geçmiş test motorunda birebir üretilebilir. Açık pozisyon, stop, veri kesintisi, yeniden başlatma ve günlük kayıp senaryoları test edilmiş. |

Bootstrap sonuçlarında başarı oranının yanında farkın ortancası ve %5–%95 aralığı da verilir.
Bütün şartlar sağlanmadan gerçek paraya geçilmez. Şartlar sağlansa bile bu bir kâr garantisi değildir; sadece bir geçiş filtresidir.

## 12. Raporlama

- Sonuçlar `results/DOGRULAMA.md` ve `results/dogrulama.json` dosyalarında, tek bir karşılaştırma tablosuyla verilir.
- Şu sorular hesaplanmış sonuçlarla yanıtlanır:
  - Ansambl BTC/nakit benchmark'larından üstün mü?
  - Daha düşük düşüş, daha düşük sermaye ağırlığından mı kaynaklanıyor?
  - Avantaj bootstrap'ta korunuyor mu?
  - Rejimlere dayanıklı mı?
  - %20/30/40 hedeflerinden hangisi daha istikrarlı?
  - 2018–2022'de nasıl davranıyor?
  - Gerçek para testine geçmek için kanıt yeterli mi?
- Hesaplanamayan ya da doğrulanamayan her şey açıkça belirtilir.
