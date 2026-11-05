"""
Turnuva adayları. Kaynaklar: bilimsel çalışmalar (trend/kırılım + iz süren ATR stopu en güçlü kanıt),
TradingView'in en popüler topluluk göstergeleri, Freqtrade topluluk botları, ve kontrol stratejileri.
Her aday küçük bir ayar tablosuyla gelir; ayar sadece eğitim döneminde seçilir.

Ortak işlem yönetimi (strategy.py): işlem başına %1,5 risk, komisyon+kayma, %10 düşüş freni (canlı).
"""
TREND_EXIT = {"tp_atr": 100.0, "be_atr": 0, "max_hold": 240}   # hedef yok; çıkış iz süren stop/sinyal

CANDIDATES = [
    {
        "id": "donchian",
        "title": "Donchian Kırılım + Chandelier",
        "desc": "Fiyat son N saatin zirvesini kırınca ve EMA200 üstündeyken alır; girişten beri zirve − 3×ATR "
                "iz süren stop veya kanal dibi kırılınca satar. Bilimsel kanıtı en güçlü aile.",
        "params": {"signal": "donchian", "interval": "1h", "trend_filter": True, "atr_len": 22,
                   "stop_atr": 3.0, "chandelier_atr": 3.0, **TREND_EXIT},
        "grid": {"dc_entry": [24, 48, 72], "dc_exit": [12, 24]},
    },
    {
        "id": "supertrend",
        "title": "Supertrend + EMA200",
        "desc": "TradingView Supertrend yukarı dönünce (fiyat EMA200 üstündeyse) alır, aşağı dönünce satar.",
        "params": {"signal": "supertrend", "interval": "1h", "trend_filter": True, "stop_atr": 3.0, **TREND_EXIT},
        "grid": {"st_mult": [2.0, 3.0, 4.0], "st_len": [10, 14]},
    },
    {
        "id": "ut_bot",
        "title": "UT Bot Alerts + EMA200",
        "desc": "TradingView'in en popüler sinyal aracı: fiyat ATR iz süren stop çizgisini yukarı kesince alır, "
                "aşağı kesince satar.",
        "params": {"signal": "ut_bot", "interval": "1h", "trend_filter": True, "stop_atr": 3.0, **TREND_EXIT},
        "grid": {"ut_key": [1.0, 2.0, 3.0], "ut_atr": [10, 14]},
    },
    {
        "id": "bb_dip",
        "title": "Bollinger + RSI Dip Alımı",
        "desc": "Yükseliş trendinde fiyat alt Bollinger bandının altına ve RSI 30'un altına düşünce alır, "
                "orta banda dönünce satar.",
        "params": {"signal": "bb_revert", "interval": "1h", "bb_trend": True, "stop_atr": 2.5,
                   "tp_atr": 100.0, "be_atr": 0, "max_hold": 48},
        "grid": {"bb_k": [2.0, 2.5], "bb_rsi": [30.0, 35.0, 40.0]},
    },
    {
        "id": "rsi2",
        "title": "Connors RSI(2) Geri Çekilme",
        "desc": "Fiyat SMA200 üstündeyken RSI(2) çok düşünce (kısa sert düşüş) alır, fiyat 5'li ortalamanın "
                "üstüne çıkınca satar. Sık işlem yapar.",
        "params": {"signal": "rsi2", "interval": "1h", "stop_atr": 3.0, "tp_atr": 100.0, "be_atr": 0,
                   "max_hold": 24},
        "grid": {"rsi2_entry": [5.0, 10.0, 15.0], "exit_len": [5, 10]},
    },
    {
        "id": "squeeze",
        "title": "Squeeze Momentum (LazyBear)",
        "desc": "Bollinger bandı Keltner kanalına sıkışıp patlayınca, momentum yukarıysa alır; momentum "
                "zayıflayınca satar.",
        "params": {"signal": "squeeze", "interval": "1h", "stop_atr": 2.0, "chandelier_atr": 2.0, **TREND_EXIT},
        "grid": {"sq_min_bars": [3, 6], "sq_kc": [1.5, 2.0]},
    },
    {
        "id": "pullback_aktif",
        "title": "Aktif Trend (RSI + Kırılım)",
        "desc": "Temkinli botun sık işlem yapan hâli: trendde RSI dönüşü veya 24 saatlik zirve kırılımında alır.",
        "params": {"signal": "pullback", "interval": "1h", "breakout_len": 24},
        "grid": {"rsi_entry": [35.0, 40.0, 45.0], "tp_atr": [2.0, 3.0]},
    },
    {
        "id": "binh_cluc",
        "title": "BinH + Cluc (Freqtrade)",
        "desc": "Freqtrade topluluğunun ünlü dip alıcısı: 15 dakikada sert düşüşte Bollinger altından alır, "
                "kârdayken orta banda dönünce satar; %5 stop / %5 hedef.",
        "params": {"signal": "binh_cluc", "interval": "15m", "stop_pct": 0.05, "tp_pct": 0.05,
                   "be_atr": 0, "max_hold": 72},
        "grid": {},
    },
    {
        "id": "ema_cross_15m",
        "title": "EMA 9/21 Hızlı (15dk)",
        "desc": "15 dakikalık mumlarda EMA9, EMA21'i yukarı kesince alır, aşağı kesince satar. Çok sık işlem; "
                "komisyonun etkisini gösterir.",
        "params": {"signal": "ema_cross", "interval": "15m", "stop_atr": 2.0, "tp_atr": 4.0, "max_hold": 48},
        "grid": {"x_fast": [9, 12], "x_slow": [21, 26]},
    },
    {
        "id": "grid",
        "title": "Grid Bot 7/24",
        "desc": "Binance Spot Grid gibi: fiyatın ±%X aralığına kademeler kurar, düşüşte parça parça alır, "
                "bir üst kademede satar. Yatay piyasada sürekli işlem yapar.",
        "params": {"engine": "grid", "interval": "15m"},
        "grid": {"n_levels": [8, 12], "range_pct": [0.03, 0.05]},
    },
    {
        "id": "late_utc",
        "title": "Gece Saati Etkisi (kontrol)",
        "desc": "Araştırmalardaki 'BTC gece 22:00–00:00 UTC yükselir' etkisi: trend yukarıysa 22:00'de alır, "
                "00:00'da satar. Karşılaştırma için.",
        "params": {"signal": "late_utc", "interval": "1h", "stop_atr": 3.0, "tp_atr": 100.0, "be_atr": 0,
                   "max_hold": 3},
        "grid": {},
    },
    # ---- haber / duygu filtreleri ve formasyon (5 Kasım eklemesi) ----
    {
        "id": "donchian_filtre",
        "title": "Donchian + Haber/Duygu Freni",
        "desc": "Donchian kırılım botu; ama faiz kararı/enflasyon açıklamasına 4 saat kala ve sonrası 4 saat "
                "işlem açmaz, Korku & Açgözlülük endeksi çok yüksekken almaz.",
        "params": {"signal": "donchian", "interval": "1h", "trend_filter": True, "atr_len": 22,
                   "stop_atr": 3.0, "chandelier_atr": 3.0, "event_pause": True, **TREND_EXIT},
        "grid": {"dc_entry": [24, 48, 72], "dc_exit": [12, 24], "fg_max": [75, 90]},
    },
    {
        "id": "aktif_filtre",
        "title": "Aktif Trend + Haber/Duygu Freni",
        "desc": "Aktif Trend botu; büyük ekonomik açıklamalar civarında ve aşırı açgözlülükte alım yapmaz.",
        "params": {"signal": "pullback", "interval": "1h", "breakout_len": 24, "event_pause": True},
        "grid": {"rsi_entry": [35.0, 40.0, 45.0], "tp_atr": [2.0, 3.0], "fg_max": [75, 90]},
    },
    {
        "id": "grid_olay",
        "title": "Grid Bot + Olay Freni",
        "desc": "Grid botu; faiz kararı ve enflasyon açıklaması civarında yeni kademe alımı yapmaz "
                "(sert tek yönlü hareketlere yakalanmamak için).",
        "params": {"engine": "grid", "interval": "15m", "event_pause": True},
        "grid": {"n_levels": [8, 12], "range_pct": [0.03, 0.05]},
    },
    {
        "id": "fear_dip",
        "title": "Aşırı Korkuda Dip Alımı",
        "desc": "Korku & Açgözlülük endeksi çok düşükken (herkes korkarken) fiyat 20'lik ortalamanın üstüne "
                "dönünce alır; iz süren 3×ATR stopla çıkar.",
        "params": {"signal": "fear_dip", "interval": "1h", "stop_atr": 3.0, "chandelier_atr": 3.0, **TREND_EXIT},
        "grid": {"fg_buy": [20, 25, 30, 40]},
    },
    {
        "id": "wedge",
        "title": "Takoz / Üçgen Kırılımı",
        "desc": "Son iki tepe ve iki dipten çizilen daralan formasyonun (düşen takoz, simetrik/yükselen üçgen) "
                "üst çizgisi kırılınca alır; isteğe bağlı hacim onayı.",
        "params": {"signal": "wedge", "interval": "1h", "stop_atr": 2.0, "chandelier_atr": 3.0,
                   "be_atr": 0, "max_hold": 120},
        "grid": {"pivot_k": [3, 5], "vol_confirm": [False, True], "tp_atr": [3.0, 100.0]},
    },
]
