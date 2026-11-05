"""
Araştırma turnuvası adayları (sadece BTC, 1s ve 4s). 15 dakikalık ve grid botları burada yok:
araştırmalar ve önceki turnuva 15dk'nın komisyonu geçemediğini gösterdi; grid 1s mumla gerçekçi
simüle edilemiyor (ChatGPT denetimi: geliştirme önceliği düşük).
Ayar tabloları bilerek küçük tutuldu (ezber riskini azaltmak için).
"""
TREND_EXIT = {"tp_atr": 100.0, "be_atr": 0, "max_hold": 24 * 30}

RESEARCH = [
    # --- mevcut şampiyonlar ve rakipleri ---
    {"id": "temkinli", "title": "Temkinli Trend", "desc": "EMA50/200 trendinde RSI dönüşüyle alır; ATR stop/hedef.",
     "params": {"signal": "pullback", "interval": "1h"},
     "grid": {"rsi_entry": [30.0, 35.0], "tp_atr": [3.0, 4.0]}},
    {"id": "temkinli_4s", "title": "Temkinli Trend (4s)", "desc": "Temkinli Trend'in 4 saatlik mumlu hâli.",
     "params": {"signal": "pullback", "interval": "4h"},
     "grid": {"rsi_entry": [30.0, 35.0], "tp_atr": [3.0, 4.0]}},
    {"id": "donchian", "title": "Donchian + Chandelier", "desc": "N mumluk zirve kırılımı, EMA200 üstü; iz süren 3×ATR stop.",
     "params": {"signal": "donchian", "interval": "1h", "trend_filter": True, "atr_len": 22, "stop_atr": 3.0,
                "chandelier_atr": 3.0, **TREND_EXIT},
     "grid": {"dc_entry": [24, 48, 72], "dc_exit": [12, 24]}},
    {"id": "donchian_filtre", "title": "Donchian + Haber/Duygu Freni",
     "desc": "Donchian; FOMC/CPI civarında ve aşırı açgözlülükte alım yok.",
     "params": {"signal": "donchian", "interval": "1h", "trend_filter": True, "atr_len": 22, "stop_atr": 3.0,
                "chandelier_atr": 3.0, "event_pause": True, **TREND_EXIT},
     "grid": {"dc_entry": [24, 48, 72], "fg_max": [75, 90]}},
    {"id": "donchian_4s", "title": "Donchian (4s)", "desc": "Donchian kırılımı 4 saatlik mumlarda (daha az işlem).",
     "params": {"signal": "donchian", "interval": "4h", "trend_filter": True, "atr_len": 22, "stop_atr": 3.0,
                "chandelier_atr": 3.0, **TREND_EXIT},
     "grid": {"dc_entry": [20, 30, 55], "dc_exit": [10, 20]}},
    {"id": "supertrend_4s", "title": "Supertrend (4s)", "desc": "Supertrend yukarı dönünce al, aşağı dönünce sat; EMA200 filtresi.",
     "params": {"signal": "supertrend", "interval": "4h", "trend_filter": True, "stop_atr": 3.0, **TREND_EXIT},
     "grid": {"st_mult": [2.0, 3.0, 4.0]}},
    {"id": "aktif", "title": "Aktif Trend", "desc": "Trendde RSI dönüşü veya 24 saatlik zirve kırılımı.",
     "params": {"signal": "pullback", "interval": "1h", "breakout_len": 24},
     "grid": {"rsi_entry": [35.0, 40.0], "tp_atr": [2.0, 3.0]}},
    {"id": "formasyon", "title": "Formasyon Avcısı", "desc": "İkili dip, ters OBO, direnç, fincan-kulp, takoz kırılımları.",
     "params": {"signal": "pattern", "patterns": ["ikili_dip", "ters_obo", "bayrak", "direnc", "fincan_kulp", "takoz"],
                "interval": "1h", "stop_atr": 2.0, "chandelier_atr": 3.0, "be_atr": 0, "max_hold": 120},
     "grid": {"pivot_k": [3, 5], "tp_atr": [3.0, 100.0]}},
    # --- ChatGPT önerisi: volatilite hedefli zaman serisi momentumu ---
    {"id": "tsmom", "title": "Zaman Serisi Momentum (vol. hedefli)",
     "desc": "Günde bir kez bakar: son N günün getirisi pozitifse tutar, negatife dönünce satar. Pozisyon "
             "büyüklüğü oynaklığa göre ayarlanır (hedef yıllık oynaklık / gerçekleşen oynaklık).",
     "params": {"signal": "tsmom", "interval": "1h", "vol_target": 0.4, "stop_atr": 6.0, "chandelier_atr": 0,
                **TREND_EXIT},
     "grid": {"mom_days": [20, 30, 60], "vol_target": [0.3, 0.5]}},
    {"id": "tsmom_trend", "title": "Zaman Serisi Momentum + EMA200",
     "desc": "TSMOM, ek olarak fiyat 4s EMA200 üstündeyken.",
     "params": {"signal": "tsmom", "interval": "4h", "trend_filter": True, "vol_target": 0.4, "stop_atr": 6.0,
                **TREND_EXIT},
     "grid": {"mom_days": [20, 30, 60], "vol_target": [0.3, 0.5]}},
    # --- araştırma ajanı + ChatGPT önerileri (4 saatlik) ---
    {"id": "kirilim_orta", "title": "Kırılım + Orta Nokta Çıkış (4s)",
     "desc": "Kapanış son N mumun en yüksek kapanışını geçince alır; N mumluk en yüksek/en düşük kapanışın "
             "orta noktası (sadece yukarı taşınır) kırılınca satar. İsteğe bağlı oynaklık hedefli büyüklük.",
     "params": {"signal": "breakout_mid", "interval": "4h", "stop_atr": 6.0, "vol_days": 90, **TREND_EXIT,
                "max_hold": 24 * 120},
     "grid": {"bo_len": [120, 240, 360], "vol_target": [0, 0.4]}},
    {"id": "kirilim_ansambl", "title": "Kırılım Ansamblı 20/40/60 gün (4s)",
     "desc": "Aynı kırılım stratejisinin 20, 40 ve 60 günlük üç kopyası, her biri paranın 1/3'üyle; "
             "oynaklık hedefli büyüklük (yıllık %40). Tek ayara bahis yapmaz.",
     "params": {"engine": "ensemble", "signal": "breakout_mid", "interval": "4h", "stop_atr": 6.0,
                "vol_days": 90, "vol_target": 0.4, **TREND_EXIT, "max_hold": 24 * 120,
                "subs": [{"bo_len": 120}, {"bo_len": 240}, {"bo_len": 360}]},
     "grid": {}},
    {"id": "donchian_4s_ch", "title": "Donchian + Chandelier 84 (4s)",
     "desc": "Donchian 4s; iz süren stop = girişten beri zirve − k×ATR(84).",
     "params": {"signal": "donchian", "interval": "4h", "trend_filter": True, "atr_len": 84, "stop_atr": 3.5,
                "dc_entry": 30, "dc_exit": 20, **TREND_EXIT},
     "grid": {"chandelier_atr": [3.0, 3.5, 4.0]}},
]

# Donchian 4s üzerinde tek tek indikatör filtreleri (sinyal değil, filtre olarak)
_FILTERS = [
    ("adx", "ADX > 20", {"f_adx": 20}),
    ("macd", "MACD > 0", {"f_macd": True}),
    ("kama", "KAMA yükseliyor", {"f_kama": True}),
    ("mom", "30 gün momentum > 0 ve SMA40 üstü", {"f_mom_days": 30, "f_sma_days": 40}),
    ("bulut", "Ichimoku bulutu üstü", {"f_cloud": True}),
]
for fid, ftitle, fparams in _FILTERS:
    RESEARCH.append({
        "id": f"donchian_4s_{fid}", "title": f"Donchian (4s) + {ftitle}",
        "desc": f"Donchian 4s kırılımı; sadece {ftitle} iken alır.",
        "params": {"signal": "donchian", "interval": "4h", "trend_filter": True, "atr_len": 22, "stop_atr": 3.0,
                   "chandelier_atr": 3.0, "dc_exit": 20, **TREND_EXIT, **fparams},
        "grid": {"dc_entry": [20, 55]},
    })
