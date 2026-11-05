# BTC Botları — Turnuva + 1 Haftalık Kâğıt Test

Gerçek BTC fiyatıyla, **sanal 100$** kullanan al-sat botu testi.
Gerçek para, Binance hesabı veya API anahtarı **kullanılmaz**.

📄 **Canlı rapor (tüm botlar):** [results/RAPOR.md](results/RAPOR.md)
🔬 **Araştırma turnuvası (4 yıl, walk-forward, PBO/Deflated Sharpe):** [results/ARASTIRMA.md](results/ARASTIRMA.md)
🏆 **BTC turnuvası (2 yıl):** [results/TURNUVA.md](results/TURNUVA.md)
🪙 **30 coin turnuvası (2 yıl):** [results/COIN_TURNUVA.md](results/COIN_TURNUVA.md)
📊 **Temkinli botun geçmiş testi:** [results/temkinli/GECMIS_TEST.md](results/temkinli/GECMIS_TEST.md)

## Nasıl çalışır?
- GitHub Actions her ~15 dakikada bir `python -m bot.main` çalıştırır.
- İlk çalıştırmada son 24 ayın verisiyle geçmiş test yapılır ve ayarlar seçilir.
- Sonra bot 7 gün boyunca saatlik mumlarla sanal alım-satım yapar, her şeyi `results/` klasörüne yazar.
- 7 gün dolunca test kendiliğinden biter.

## Strateji (kısaca)
- Sadece BTC yükseliş trendindeyken alır (EMA50 ve fiyat EMA200 üstünde).
- Giriş: RSI geri çekilmeden dönünce, ya da (ayar açıksa) 24 saatlik zirve kırılınca.
- Çıkış: ATR'ye göre stop ve hedef, kâr gelince stop yukarı taşınır, 72 saatte süre stopu.
- Risk: işlem başına hesabın en fazla %1,5'i; art arda 3 kayıpta 24 saat mola; %10 düşüşte tamamen durur.
- Kaldıraç yok. Komisyon %0,1 + kayma %0,05 hesaba katılır.

## Testi yeniden başlatmak
`results/state.json` dosyasını silmen yeterli (geçmiş testi de yenilemek için `results/backtest.json` ve `results/params.json`'u da sil).

## Turnuva
`bot/candidates.py` içindeki 23 aday (Donchian, Supertrend, UT Bot, Bollinger dip, RSI(2), Squeeze,
Aktif Trend, Freqtrade BinH+Cluc, EMA 9/21 15dk, Grid Bot, Gece saati kontrolü, haber/duygu freni eklenmiş 3 bot, Aşırı korkuda dip alımı, Takoz/üçgen, İkili dip, Ters OBO, Boğa bayrağı, Yatay direnç, Fincan-kulp, Formasyon Avcısı ve frenli hâli) 24 aylık gerçek
Binance verisinde yarışır. Ayarlar ilk %70'te seçilir, sıralama hiç görülmemiş son %30'a ve
2 kat komisyonlu dayanıklılık testine göre yapılır. İlk 3 bot, temkinli botla birlikte canlı kâğıt teste girer.
Turnuvayı yeniden yapmak için `results/turnuva.json` ve `results/secilen_botlar.json` silinir.

## 30 Coin Botları
`bot/multi.py`: Binance'te hacimce en büyük 30 coini her saat tarar. Akıllı Skor modu her coine trend,
göreceli güç, momentum, kırılım, formasyon (ikili dip, ters OBO, yatay direnç, fincan-kulp, takoz/üçgen),
hacim patlaması ve RSI'dan 8 üzerinden puan verir. BTC yön filtresi, FOMC/CPI freni, Korku & Açgözlülük
freni, coin başına ATR stop + iz süren stop, en fazla N pozisyon. Küçük coinlerde kayma daha yüksek hesaplanır.
Geçmiş testte coin listesi Kasım 2024 hacmine göre seçilir (bugünün kazananlarını seçip sonucu şişirmemek için).

## Araştırma turnuvası (ChatGPT denetimi sonrası)
`bot/research.py`: 48 ay BTC verisi, 12 ay eğitim / 3 ay sınav kayan walk-forward, pencere bazında piyasa
rejimi, günlük özsermaye ölçümleri (Sharpe, Sortino, Calmar, CAGR, exposure, PF, beklenti), 1×–3× maliyet
eğrisi, tüm aday×ayarlarla PBO (CSCV) ve kazanan için Deflated Sharpe. Yeni adaylar: volatilite hedefli
zaman serisi momentumu, Zarattini tipi kırılım + orta nokta çıkış, 20/40/60 gün kırılım ansamblı,
Donchian 4s + ADX / MACD / KAMA / momentum / Ichimoku filtreleri. Yeniden yapmak için `results/arastirma.json` silinir.
