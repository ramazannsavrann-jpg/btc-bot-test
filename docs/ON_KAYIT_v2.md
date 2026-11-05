# Ön Kayıt v2 — VM ile Kırılım Ansamblı: Ayı Piyasası Koruma Kuralı

**Durum:** Bu belge, kuralları hesaplayan kod yazılmadan ve hiçbir ayı dönemi sonucu hesaplanmadan önce yazıldı ve GitHub'a gönderildi. Sonradan değiştirilmez. Değişiklik gerekirse `ON_KAYIT_v3.md` eklenir ve raporda **"ön kayıt dışı"** diye işaretlenir.

**Kanıt:** Bu dosyanın SHA-256 özeti, commit hash'i, `on-kayit-v2` etiketi (tag) ve GitHub'ın sunucu tarafında kaydettiği push zamanı. Hepsi `docs/ON_KAYIT_v2_zaman.txt` dosyasında. `docs/ON_KAYIT_v1.md` ve v1'in kararları değişmez; bu belge onlara **ek**tir.

Hazırlayanlar: Claude (taslak), ChatGPT (denetim), proje sahibi (onay ve ek şartlar). Tarih: 2026-11-05.

---

## 0. Bu kural nedir, ne değildir

- Bu bir **istatistiksel üstünlük kanıtı değildir**. **Önceden belirlenmiş operasyonel tercih kuralıdır.** Kanıtlar eşitken hangi stratejinin varsayılan olacağını, sonuçları görmeden önce sabitler.
- v1 doğrulaması, ansambl ile oynaklık eşleştirilmiş BTC (VM) arasında istatistiksel olarak anlamlı bir fark bulamadı. Bu yüzden **basit olan VM varsayılan** kabul edilir. Ansambl, yalnızca aşağıdaki koruma şartlarını sağlarsa "ayı piyasası koruma alternatifi" olarak tercih edilir.
- Bu kural yalnızca araştırma ve kâğıt testteki **varsayılanı** belirler. Gerçek paraya geçiş için v1 §11'deki eşikler ve güvenlik kapıları (testnet, onay vb.) aynen geçerlidir. Bu kural onları gevşetmez.
- Canlı kâğıt botlar, kayıtları ve mevcut strateji kuralları bu belgeyle değişmez.

## 1. Dürüstlük notu: geçmiş veri keşifseldir

- Eşikler, v1'in **toplam dönem** sonuçları görüldükten sonra yazıldı. Ana dönemde ansambl MDD %22,9, VM %26,5 idi; 2018–22 stres testinde ansambl MDD %22,3 idi. BTC'nin büyük ayı piyasalarının tarihleri de genel olarak bilinen bilgilerdir.
- **Ayı dönemine özel** karşılaştırmalar (aşağıdaki §4–§5) henüz hiç hesaplanmadı.
- Bu nedenle geçmiş veriyle verilecek karar **keşifsel ve geçicidir**.
- **Temiz doğrulama** yalnızca bu belgenin sunucu zaman damgasından **sonraki** verilerle yapılır (§8).

## 2. Karşılaştırılan stratejiler

Kurallar ve sınırlar ortaktır:
- Hepsi spot, kaldıraçsız; ağırlık ≤ %99.
- Nakit getirisi %0.
- Hepsi aynı veri, aynı tarihler ve aynı maliyetlerle tek ve kesintisiz bir simülasyonda çalışır.

| Kod | Tanım | Rol |
|---|---|---|
| **ENS** | v1 §1'deki Kırılım Ansamblı (4s), %40 oynaklık hedefi, kurallar birebir aynı. Canlı test düşüş freni geçmiş testte kapalı. | Aday (koruma alternatifi) |
| **VM-A** | Bağımsız oynaklık hedefli BTC. Her UTC gününün son 4s kapanışında hedef ağırlık w* = min(0,99 ; 0,40 / σ). σ, **ENS ile aynı tahminci**: son 540 adet 4s getirinin (90 gün) yıllıklanmış standart sapması (×√2190), yalnızca o ana kadarki veriyle. \|w* − w_mevcut\| > 0,05 ise işlem bir sonraki 4s mumun açılışında yapılır. w_mevcut, fiyat hareketiyle kendiliğinden kayan gerçek ağırlıktır. | **Varsayılan strateji** ve karar kuralındaki kıyas |
| **VM-B** | VM-A ile aynı, tek fark: σ son 180 adet 4s getiriden (30 gün). | Sağlamlık kontrolü; karara girmez |
| **VM-ref** | v1 §3'teki VM: w = min(1, σ_ens / σ_btc), 90 gün, eşik 0,05. | Yalnızca v1 ile bağlantı için; karara girmez |
| **B100** | %100 BTC al-tut | Bilgi |

Karar **yalnızca ENS ile VM-A** arasında verilir. VM-B ve VM-ref sonuçları ne olursa olsun kararı değiştirmez; yalnızca raporlanır.

## 3. Veri, dönem ve maliyet

- **Kaynak:** v1 §2 ile aynı. Binance spot BTCUSDT, `data.binance.vision`; 1s mumlar UTC'ye hizalı 4s mumlara birleştirilir. Günlük kapanış, her UTC gününün son 4s mum kapanışıdır.
- **Simülasyon:** 2017-08-17'den (BTCUSDT başlangıcı) başlar.
- **Ölçüm:** **2017-12-01 00:00 UTC → 2026-10-31 23:59 UTC**. Arada en az 600 adet 4s mumluk ısınma vardır (v1 §5'teki en uzun pencere ihtiyacı).
- **Maliyet:**
  - **1×:** komisyon %0,10 + kayma %0,05, her alış ve satışta. VM için yeniden dengeleme tutarı üzerinden.
  - **2×:** komisyon %0,20 + kayma %0,10.
  - **İki kat maliyet testi zorunludur:** §6'daki her şart iki maliyet düzeyinde de ayrı ayrı sağlanmalıdır.

## 4. Büyük ayı dönemlerinin mekanik tanımı

Tanım yalnızca BTC günlük kapanışından mekanik olarak çıkar; elle dönem seçilmez.

1. **Zirve:** P_d = o güne kadarki en yüksek günlük kapanış (tüm zamanların zirvesi).
2. **Su altı dönemi:** Kapanışın P_d'nin altında kaldığı kesintisiz günler. Zirve gününden sonraki ilk günde başlar, kapanış eski zirveye ilk kez eşit veya üstüne çıktığı gün biter.
3. Su altı dönemindeki en derin düşüş (C_d / P_d − 1) **≤ −%40** ise bu bir **büyük ayı dönemidir**.
4. Her dönem için üç tarih:
   - **t0 (zirve):** dönemden önceki zirve günü
   - **t1 (dip):** dönemdeki en düşük kapanış günü (eşitlikte ilk gün)
   - **t2 (toparlanma):** kapanışın t0 kapanışına ilk kez ulaştığı gün
5. **Tamamlanmış dönem:** t2 ≤ 2026-10-31. Tamamlanmamış dönem raporlanır ama **sayılmaz**.
6. t0, ölçüm başlangıcından (2017-12-01) önceyse dönem sayılmaz. Isınması bitmemiş bir strateji karşılaştırılmaz.
7. Bir uzun ayı piyasası tek dönemdir. Alt dönemlere bölünüp çok sayıda bağımsız test gibi gösterilmez.

## 5. Dönem içi ölçümler (aynı başlangıç ve bitiş tarihleri)

Her dönemde ENS, VM-A, VM-B, VM-ref ve B100 **aynı tarihlerde** karşılaştırılır. Her stratejinin günlük özsermayesi t0 kapanışında 1'e eşitlenir.

- **Ayı aşaması [t0, t1]:**
  - **MDD_X:** X'in pencere içindeki en büyük düşüşü, pencere başından itibaren günlük özsermaye üzerinden.
  - Pencere getirisi.
- **Toparlanma aşaması [t1, t2]:**
  - Her stratejinin getirisi, R_X.
  - **Kaçırılan getiri** = R_VM-A − R_ENS (yüzde puan). Ayrıca (1 + R_ENS) / (1 + R_VM-A) katılım oranı ve B100'e göre aynı iki ölçüm.
  - Bu ölçüm **ayrıca raporlanır**. Karara dolaylı olarak §6'daki CAGR şartıyla girer.
- **Tam döngü [t0, t2]:** getiri ve MDD.
- Dönem başına işlem sayısı, piyasada kalma oranı ve ortalama BTC ağırlığı.

## 6. Karar kuralı

Bir dönem için **koruma şartı**, iki koşulun ikisi de sağlanırsa geçilir:

- (a) MDD_VM-A − MDD_ENS ≥ **10 yüzde puan**
- (b) (MDD_VM-A − MDD_ENS) / MDD_VM-A ≥ **%25** (göreli düşüş azaltımı)

Bu şart her dönemde ayrı ayrı değerlendirilir.

**ENS'nin "koruma alternatifi" olarak tercih edilmesi için aşağıdakilerin HEPSİ gerekir:**

| # | Şart |
|---|---|
| 1 | Tamamlanmış büyük ayı dönemi sayısı **n ≥ 3** |
| 2 | Koruma şartını geçen dönem sayısı ≥ ⌈2n/3⌉ (n = 3 için en az 2) |
| 3 | Tüm ölçüm döneminde (2017-12-01 → 2026-10-31) **CAGR_VM-A − CAGR_ENS ≤ 2 yüzde puan**. CAGR = (son / ilk)^(365,25 / gün) − 1. |
| 4 | 1–3 numaralı şartlar **hem 1× hem 2× maliyette** sağlanır. Şart 2'de, iki maliyet düzeyinde de geçen dönemler sayılır. |

**Sonuç:**
- **n < 3:** "Yetersiz kanıt." Karar verilmez, **VM-A varsayılan kalır**.
- **n ≥ 3, ama şartlardan biri bile sağlanmıyor:** **VM-A varsayılan** kalır.
- **Hepsi sağlanıyor:** ENS, ayı piyasası koruma alternatifi olarak tercih edilir. Geçmiş veriyle bu sonuç **keşifsel ve geçicidir** (§1); temiz doğrulama §8'e göre yapılır.
- Eşikler sonuçlar görüldükten sonra **değiştirilmez**. Sınırda kalan bir sonuç (örneğin 9,8 puan) şartı sağlamamış sayılır.

## 7. Çoklu test düzeltmesi

- Bu belge en fazla **3 VM varyantı** tanımlar (VM-A, VM-B, VM-ref). Yeni varyant eklemek yeni bir ön kayıt gerektirir.
- Deneme sayısı N_toplam = 263 (v1) + 3 = **266**. Başarısız olanlar dahil tüm denemeler sayılır.
- ENS ve VM-A için DSR şu deneme sayılarıyla raporlanır:
  - N_toplam = 266
  - VM varyantlarının eklendiği korelasyon matrisinden yeniden hesaplanan N_eff (v1 §6'daki üç yöntem)
- DSR **bilgi amaçlıdır**; §6'daki karar kuralı operasyonel olduğu için DSR'ye bağlı değildir. Ama düşük DSR raporda açıkça yazılır.

## 8. Temiz (ileriye dönük) doğrulama

- **Temiz veri:** `docs/ON_KAYIT_v2_zaman.txt`'deki sunucu zamanından sonra oluşan tüm BTCUSDT mumları.
- ENS ve VM-A kuralları tamamen sabit ve deterministik. Bu yüzden ileri dönem sonuçları, yeni bir canlı bot olmadan da aynı kurallarla, geriye bakma olmadan hesaplanabilir. Canlı kâğıt testteki ENS botu ek bir karşılaştırma kaynağıdır.
- **İleri karar** yalnızca t0'ı temiz dönemde olan ayı dönemleriyle verilir. Aynı §4 tanımı ve aynı §6 eşikleri kullanılır, tek fark: n ≥ 1 tamamlanmış dönemle **geçici gözlem**, n ≥ 3 ile **karar**.
- İleri veri birikene kadar varsayılan, §6'nın geçmiş veri sonucudur. O sonuç da keşifseldir.
- Ara raporlar her 6 ayda bir: o ana kadarki ileri dönem CAGR, MDD ve varsa tamamlanmamış ayı dönemi ölçümleri. Ara raporlar karar değiştirmez.

## 9. Raporlama

- Sonuçlar `results/ON_KAYIT_v2_SONUC.md` ve `.json` dosyalarına yazılır.
- Rapor şunları içerir:
  - Bulunan bütün su altı dönemlerinin tablosu, büyük olanlar ve tamamlanmış olanlar işaretli
  - Her dönem ve her strateji için §5 ölçümleri, 1× ve 2× maliyette
  - §6 şartlarının tek tek geçti/kaldı tablosu ve sonuç cümlesi
  - §7 DSR değerleri
  - Hesaplanamayan veya doğrulanamayan her şey
- Raporun ilk satırı: **"Bu bir istatistiksel üstünlük kanıtı değil, önceden belirlenmiş operasyonel tercih kuralının sonucudur. Geçmiş veri sonucu keşifseldir."**
- Hesap kodu bu belgeden **sonra**, ayrı bir commit olarak eklenir. Kod bu belgeyle çelişirse belge geçerlidir ve çelişki raporda yazılır.
