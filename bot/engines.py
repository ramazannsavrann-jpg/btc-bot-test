"""Motor seçimi: 'trend' (strategy.py + signals.py) veya 'grid' (grid.py)."""
from . import grid, strategy


def get(params):
    return grid if params.get("engine") == "grid" else strategy
