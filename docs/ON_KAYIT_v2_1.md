# Ön Kayıt v2.1: v2'ye kesinleştirme eki

**Durum:** `docs/ON_KAYIT_v2.md`'ye ektir. v2'yi değiştirmez, yalnızca belirsiz kalan dört noktayı kesinleştirir. Bu belge ile v2 çelişirse bu belge geçerlidir. Hesap kodu yazılmadan ve hiçbir v2 sonucu hesaplanmadan önce gönderildi. `docs/ON_KAYIT_v1.md` değişmez.

**Kanıt:** SHA-256, commit ve GitHub sunucu push zamanı; hepsi `docs/ON_KAYIT_v2_1_zaman.txt` dosyasında.

**Eşikler değişmedi.** §6'daki 10 puan, %25, en az 3 dönemde en az 2/3 ve CAGR farkı en fazla 2 puan kuralları aynen geçerli.

Neden gerekli oldu: v2'yi denetlerken dört eksik bulundu.
- §8 ön kayıt saatini kesen mumu açıkça dışlamıyordu.
- §4 eksik veri ve fiyat eşitliği kurallarını yazmıyordu.
- §2 oynaklığın tam formülünü ve iki stratejinin pozisyon güncelleme farkını belgelemiyordu.
- "Nihai karar" ile "geçici varsayılan" ayrımı yeterince açık değildi.

---

## 1. Temiz (ileri) veri başlangıcı (v2 §8'i kesinleştirir)

- **T_kayıt:** v2 ve v2.1'in GitHub sunucu push zamanlarından **daha geç olanı** (`ON_KAYIT_v2_1_zaman.txt`).
- **Kesen mumlar tamamen dışarıda:** Açılış zamanı T_kayıt'tan önce olan bir mum, kapanışı sonra olsa bile **temiz sayılmaz**. Bu kural 1s, 4s ve gün mumlarının hepsi için geçerli.
- **Performans başlangıcı:** Açılışı T_kayıt'tan sonra olan **ilk tam UTC günü**, 00:00:00 UTC. T_kayıt 2026-11-05 içinde olduğu için bu **2026-11-06 00:00:00 UTC**'dir.
  - Başlangıç özsermayesi, o günün ilk 4s mumunun açılış fiyatıyla değerlenir ve 1'e eşitlenir.
  - Performansa yalnızca bu andan sonraki fiyat değişimleri girer.
- **Geçmiş veri yalnızca ısınma içindir.** T_kayıt öncesi ve performans başlangıcı öncesi veriler sadece göstergeleri, oynaklık tahminini ve strateji durumunu hazırlar. Getiri, MDD, CAGR, işlem başarısı veya ayı dönemi ölçümüne **girmez**.
- **Başlangıç durumu:**
  - **Ana hesap:** Simülasyon kesintisiz akar; ısınmadan devreden açık pozisyonlar, canlı bir sistemde olacağı gibi korunur. Ama başlangıç anındaki piyasa değeriyle sıfırlanır; önceki kâr veya zararları performansa girmez.
  - **Bilgi amaçlı:** Her iki strateji nakitte başlar. Bu hesap karara girmez.
- **İleri ayı dönemi:**
  - Zirve, 2017-08-17'den beri **tüm geçmişin** en yüksek günlük kapanışıdır; zirve tanımı için geçmiş fiyat kullanılır.
  - Bir dönemin ileri karara girmesi için t0'ın (yeni tüm zamanların zirvesi) performans başlangıcında veya sonrasında olması gerekir.
  - T_kayıt anında devam eden su altı dönemi, sonradan −%40'ı geçse bile **ileri karara girmez**; yalnızca gözlem olarak raporlanır.

## 2. Ayı döneminin kesin tanımı (v2 §4'ü kesinleştirir)

- **Fiyat:** Binance spot **BTCUSDT**, `data.binance.vision` arşivi.
  - 2025 ve sonrası dosyalardaki mikrosaniye zaman damgaları milisaniyeye çevrilir.
  - Fiyatlar dosyadaki ondalık metin olarak okunur ve kesin ondalık aritmetikle karşılaştırılır. Kayan nokta yuvarlaması eşitlik kararını etkilemez.
- **Günlük kapanış C_d:** Açılış zamanı **23:00:00 UTC** olan 1s mumun kapanışı (kapanış anı 23:59:59.999 UTC). Bu, Binance 1 günlük mum kapanışıyla aynıdır.
  - O 1s mum yoksa günün kapanışı **yoktur**. Gün tanımda atlanır, doldurulmaz, uydurulmaz. Atlanan günler raporda listelenir.
- **Zirve:** P_d = 2017-08-17'den d gününe kadar (d dahil) en yüksek C.
- **Su altı dönemi:** Kapanışın P'nin altında kaldığı ilk günden başlar. Kapanışın tekrar **P'ye eşit veya üstünde** olduğu ilk günde (o gün dahil) biter.
- **t0:** Dönemden önceki, C = P olan **son** gün.
- **t1:** Dönem içindeki en düşük C. Eşitlikte en erken gün.
- **t2:** C ≥ C_t0 olan ilk gün.
- **Büyük ayı dönemi:** C_t1 / C_t0 − 1 ≤ **−0,40**, kesin ondalıkla.
- **Tamamlanmış:** t2 mevcut ve t2, değerlendirme döneminin son günü veya öncesinde.
  - Geçmiş değerlendirmede son gün 2026-10-31.
  - İleri değerlendirmede raporun hazırlandığı günden önceki son tam UTC günü.
- t0 ölçüm başlangıcından önceyse dönem sayılmaz: geçmiş için 2017-12-01, ileri için performans başlangıcı.

## 3. ENS ve VM-A: eşitlenen ve bilerek farklı bırakılan kurallar (v2 §2'yi kesinleştirir)

Aşağıdaki ENS kuralları mevcut koddan (`bot/strategy.py`, `bot/signals.py`, `bot/ensemble.py`) birebir alınmıştır. VM-A aynı yapı taşlarını kullanır.

**Eşit olanlar**

| Kalem | ENS ve VM-A (ortak) |
|---|---|
| Veri | Aynı BTCUSDT 4s mumları (1s'ten UTC'ye hizalı birleştirme) |
| Oynaklık σ | Son **540** adet 4s mumun **basit getirisi** (C_i / C_{i−1} − 1). **Bölen n** olan standart sapma × √2190. Yalnızca o mumun kapanışına kadarki veri kullanılır. 540 getiri birikmeden σ yoktur ve pozisyon açılmaz. |
| Hedef ağırlık | min(0,99 ; 0,40 / σ) |
| Karar ve dolum zamanı | Karar 4s mum kapanışında, işlem **bir sonraki 4s mumun açılışında** |
| Alış maliyeti | Fiyat × (1 + 0,0005) kayma. Komisyon, işlem tutarı × 0,001; tutar, komisyon dahil nakdi aşmayacak şekilde ölçeklenir. |
| Satış maliyeti | Fiyat × (1 − 0,0005) kayma. Komisyon, brüt tutar × 0,001. |
| 2× maliyet | Kayma 0,001, komisyon 0,002; ikisi için de aynı. |
| Kaldıraç ve borç | Yok. Nakit hiçbir zaman eksiye düşmez, ağırlık ≤ %99. |
| Nakit getirisi | %0 |
| Hesap düşüş freni | Her ikisinde de **kapalı** (canlı kâğıt testteki %10 fren geçmiş hesaplara girmez) |
| Özsermaye ölçümü | Her UTC gününün son 4s kapanışında piyasa değeri |

**Bilerek farklı bırakılanlar** (stratejinin kendisi olan farklar; eşitlenirse karşılaştırılan şey değişir)

| Kalem | ENS | VM-A |
|---|---|---|
| Ne zaman pozisyonda | Yalnızca kırılım sinyali varken. 3 alt sistem, her biri sermayenin 1/3'ü. | σ tanımlı olduğu sürece her zaman |
| Ağırlık güncelleme | Ağırlık **yalnızca girişte** hesaplanır. Pozisyon süresince adet sabittir, yeniden dengelenmez. | Her UTC gününün son 4s kapanışında hedef yeniden hesaplanır. \|hedef − gerçek ağırlık\| > 0,05 ise yeniden dengelenir. |
| Çıkış ve risk kuralları | Orta nokta çıkışı, giriş − 6×ATR(14) stopu, 120 günlük süre stopu, 3 ardışık kayıpta 24 saat mola | Yok; tek risk sınırı ağırlık tavanı ve oynaklık hedefi |
| Stop dolumu | Mevcut motorun davranışı birebir (v1 ile aynı), kayma ve komisyon dahil | Uygulanmaz |

## 4. Nihai karar ve gözlem ayrımı (v2 §6 ve §8'i kesinleştirir)

- **Nihai karar**, yalnızca **ileri (temiz) veride en az 3 tamamlanmış büyük ayı dönemi** oluştuğunda, v2 §6 şartlarıyla verilir.
- **Geçmiş veri sonucu** (2017-12-01 → 2026-10-31) **geçici varsayılandır**. Keşifseldir, nihai karar değildir. n < 3 ise geçici varsayılan da VM-A'dır.
- İleri veride 3 tamamlanmış dönemden önceki bütün sonuçlar, 1 veya 2 tamamlanmış dönem dahil, **yalnızca gözlemdir**. Ne nihai kararı ne de geçici varsayılanı değiştirir.
- Yalnızca bilgi için: BTC'nin 2017'den bu yana yaklaşık 9 yılında bu tanıma uyan birkaç büyük dönem yaşandı. Dolayısıyla nihai karar **yıllar sürebilir**. Bu süre boyunca karar kuralı, eşikler ve VM varyantları değiştirilmez.
- Bu kural istatistiksel üstünlük kanıtı değil, önceden belirlenmiş operasyonel tercih kuralıdır (v2 §0). Gerçek paraya geçiş v1 §11 ve güvenlik kapılarına bağlıdır.
