"""
Giriş noktası:  python -m bot.main
  1) results/backtest.json yoksa: 24 aylık geçmiş testi yapar, ayarları seçer (bir kere).
  2) Canlı kâğıt testini bir adım ilerletir ve results/RAPOR.md'yi günceller.
"""
from __future__ import annotations

import os
import sys

from . import backtest, data, paper

OUT = os.environ.get("BOT_OUT", "results")


def main():
    os.makedirs(OUT, exist_ok=True)
    if not os.path.exists(os.path.join(OUT, "backtest.json")):
        print("Geçmiş test başlıyor...")
        candles, src = data.history(24)
        print(f"{len(candles)} mum alındı ({src})")
        res, params = backtest.run_backtest(candles, src, OUT)
        print("Görülmemiş dönem:", res["gorulmemis_donem"])
        print("Haftalık 100$:", res["haftalik_100_dolar_bot"])

    st_old = paper.load_json(os.path.join(OUT, "state.json"))
    if st_old and st_old.get("finished"):
        print("7 günlük test bitti; yapılacak bir şey yok. (İstersen Actions'tan iş akışını kapatabilirsin.)")
        return 0
    candles, src = data.recent(1000, prefer=(st_old or {}).get("source"))
    st = paper.run(candles, src, OUT)
    print(f"Kâğıt test: bakiye={paper.S.equity(st, st['last_price']):.2f}$ "
          f"işlem={len(st['trades'])} bitti={st['finished']} kaynak={src}")


if __name__ == "__main__":
    sys.exit(main())
