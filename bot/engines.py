"""Motor seçimi: 'trend' (strategy.py + signals.py), 'grid' (grid.py) veya 'ensemble' (ensemble.py)."""
from . import ensemble, grid, strategy


def get(params):
    e = params.get("engine")
    return grid if e == "grid" else ensemble if e == "ensemble" else strategy
