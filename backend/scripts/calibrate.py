import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hormiguero.engine.model.hybrid import HybridModel
from hormiguero.engine.scenarios import SCENARIOS
from hormiguero.schemas.events import EventInfo, EventStatus

SEEDS = range(1, 6)
TICKS = int(os.environ.get("CALIBRATE_TICKS", 20_000))


def run(args: tuple[str, int, int]) -> dict:
    scenario_id, seed, ticks = args
    scenario = SCENARIOS[scenario_id]
    config = scenario.config
    model = HybridModel(config, seed)
    events = [
        EventInfo(
            id=f"evt{index}",
            type=event.type,
            intensity=event.intensity,
            duration=event.duration,
            region=event.region,
            start_tick=event.start_tick or 1,
            end_tick=(event.start_tick or 1) + event.duration,
            predator_count=event.predator_count,
            status=EventStatus.SCHEDULED,
        )
        for index, event in enumerate(scenario.events)
    ]
    initial = model.colony.size
    population = [initial]
    for _ in range(ticks):
        model.step()
        for event in events:
            if event.status is EventStatus.SCHEDULED and model.tick >= event.start_tick:
                event.status = EventStatus.ACTIVE
                model.start_event(event)
            elif event.status is EventStatus.ACTIVE and model.tick >= event.end_tick:
                event.status = EventStatus.FINISHED
                model.end_event(event)
        population.append(model.colony.size)
        if model.colony.size == 0:
            break
    deaths = model.deaths
    total = sum(deaths.model_dump().values())
    recoveries = [model.resilience.recovery(event) for event in events if event.status is not EventStatus.SCHEDULED]
    drop = max((1 - r.min_population_during / r.population_before for r in recoveries if r.population_before), default=0.0)
    return {
        "alive": model.colony.size > 0,
        "initial": initial,
        "final": model.colony.size,
        "peak": max(population),
        "drop": drop,
        "recovered": all(r.recovery_ticks is not None for r in recoveries) if recoveries else None,
        "deaths": deaths,
        "predator_share": deaths.predator / total if total else 0.0,
    }


def criteria(scenario_id: str, results: list[dict]) -> tuple[str, bool]:
    survivors = sum(r["alive"] for r in results)
    if scenario_id == "baseline":
        ratios = [r["final"] / r["initial"] for r in results]
        ok = survivors == len(results) and all(1.2 <= ratio <= 5 for ratio in ratios)
        return "sobrevive y población final entre 1.2x y 5x", ok
    if scenario_id == "drought":
        recovered = sum(bool(r["recovered"]) for r in results)
        ok = all(r["drop"] >= 0.15 for r in results) and recovered >= 3
        return f"caída >= 15 % y recuperación en {recovered}/5 semillas (mínimo 3)", ok
    if scenario_id == "flood":
        ok = survivors == len(results) and all(r["deaths"].flood > 0 for r in results)
        return "deaths.flood > 0 y sobrevive", ok
    if scenario_id == "predator_invasion":
        kills = sum(r["deaths"].predator for r in results)
        total = sum(sum(r["deaths"].model_dump().values()) for r in results)
        share = kills / total if total else 0.0
        ok = share > 0.2 and survivors >= 3
        return f"deaths.predator = {share:.0%} de las muertes (mínimo 20 %) y sobrevive en {survivors}/5 semillas (mínimo 3)", ok
    return "sin criterio", True


def main() -> None:
    selected = sys.argv[1:] or list(SCENARIOS)
    with ProcessPoolExecutor() as pool:
        for scenario_id in selected:
            print(f"== {scenario_id}")
            results = list(pool.map(run, [(scenario_id, seed, TICKS) for seed in SEEDS]))
            for seed, r in zip(SEEDS, results):
                print(
                    f"seed {seed}: alive={r['alive']} pop {r['initial']}->{r['final']} (peak {r['peak']}) "
                    f"drop={r['drop']:.0%} recovered={r['recovered']} pred_share={r['predator_share']:.0%} "
                    f"deaths={r['deaths'].model_dump()}"
                )
            text, ok = criteria(scenario_id, results)
            print(f"-> {'OK' if ok else 'FALLA'}: {text}")


if __name__ == "__main__":
    main()
