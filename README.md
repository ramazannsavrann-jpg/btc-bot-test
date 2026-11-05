# BTC Bot — 1 Haftalık Kâğıt Test

Gerçek BTC fiyatıyla, **sanal 100$** kullanan al-sat botu testi.
Gerçek para, Binance hesabı veya API anahtarı **kullanılmaz**.

📄 **Canlı rapor:** [results/RAPOR.md](results/RAPOR.md)
📊 **Geçmiş test (2 yıl):** [results/GECMIS_TEST.md](results/GECMIS_TEST.md)

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
