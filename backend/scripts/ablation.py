import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

SOURCE = Path(sys.argv[1])
CONFIG = sys.argv[2]
sys.path.insert(0, str(SOURCE))

from hormiguero.engine.model.hybrid import HybridModel
from hormiguero.schemas.config import SimulationConfig

TICKS = 20_000
SEEDS = range(1, 6)


def load_config() -> SimulationConfig:
    if CONFIG == "default":
        return SimulationConfig()
    return SimulationConfig.model_validate_json(Path(CONFIG).read_text(encoding="utf-8"))


def run(seed: int) -> dict:
    model = HybridModel(load_config(), seed)
    peak = model.colony.size
    collapse = None
    for _ in range(TICKS):
        model.step()
        peak = max(peak, model.colony.size)
        if model.colony.size == 0:
            collapse = model.tick
            break
    return {
        "seed": seed,
        "alive": collapse is None,
        "collapse_tick": collapse,
        "final": model.colony.size,
        "peak": peak,
        "delivered": model.food_delivered_total,
    }


if __name__ == "__main__":
    with ProcessPoolExecutor() as pool:
        print(json.dumps(list(pool.map(run, SEEDS))))
