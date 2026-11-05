# BTC Botları — Turnuva + 1 Haftalık Kâğıt Test

Gerçek BTC fiyatıyla, **sanal 100$** kullanan al-sat botu testi.
Gerçek para, Binance hesabı veya API anahtarı **kullanılmaz**.

📄 **Canlı rapor (tüm botlar):** [results/RAPOR.md](results/RAPOR.md)
🏆 **Turnuva (11 strateji, 2 yıl):** [results/TURNUVA.md](results/TURNUVA.md)
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
