import json
import pickle
import sys
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "src"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from hormiguero.engine.model.hybrid import HybridModel
from hormiguero.engine.scenarios import SCENARIOS
from hormiguero.schemas.config import AntConfig, NestConfig, PredatorConfig, SimulationConfig
from hormiguero.schemas.events import EventInfo, EventStatus

OUTPUT = ROOT / "docs" / "informe"
FIGURES = OUTPUT / "figuras"
SEEDS = list(range(1, 6))
TICKS = 20_000
SAMPLE_EVERY = 10
CACHE = Path(tempfile.gettempdir()) / "hormiguero_results.pkl"
XTICKS = [0, 5000, 10000, 15000, 20000]

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_SECONDARY = "#52514e"
GRID = "#e4e3df"
BLUE, ORANGE, AQUA, YELLOW = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"

NAMES = {
    "baseline": "Colonia base",
    "drought": "Sequía prolongada",
    "flood": "Inundación",
    "predator_invasion": "Invasión de depredadores",
}
EVENT_LABELS = {"drought": "sequía", "flood": "inundación", "predator_invasion": "oleada de depredadores"}
CAUSES = [("old_age", "Vejez", BLUE), ("starvation", "Hambre", ORANGE), ("predator", "Depredadores", AQUA), ("flood", "Inundación", YELLOW)]


def simulate(args: tuple[str, int]) -> dict:
    scenario_id, seed = args
    scenario = SCENARIOS[scenario_id]
    model = HybridModel(scenario.config, seed)
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
    population = [model.colony.size]
    stocks = []
    for _ in range(TICKS):
        model.step()
        for event in events:
            if event.status is EventStatus.SCHEDULED and model.tick >= event.start_tick:
                event.status = EventStatus.ACTIVE
                model.start_event(event)
            elif event.status is EventStatus.ACTIVE and model.tick >= event.end_tick:
                event.status = EventStatus.FINISHED
                model.end_event(event)
        population.append(model.colony.size)
        if model.tick % SAMPLE_EVERY == 0:
            stocks.append([model.nest.stocks.food, model.nest.stocks.eggs, model.nest.stocks.larvae, model.nest.stocks.workers])
        if model.colony.size == 0:
            break
    tracker = model.resilience
    recoveries = [tracker.recovery(event) for event in events if event.status is not EventStatus.SCHEDULED]
    return {
        "scenario": scenario_id,
        "seed": seed,
        "population": population,
        "stocks": stocks,
        "alive": model.colony.size > 0,
        "final": model.colony.size,
        "peak": tracker.peak_population,
        "min": tracker.min_population,
        "mean_efficiency": tracker.mean_efficiency,
        "delivered": model.food_delivered_total,
        "deaths": model.deaths.model_dump(),
        "windows": [(event.start_tick, event.end_tick) for event in events],
        "recoveries": [
            {"before": r.population_before, "minimum": r.min_population_during, "ticks": r.recovery_ticks} for r in recoveries
        ],
    }


def measure_tick_time() -> float:
    config = SimulationConfig(
        ants=AntConfig(initial_workers=2000, max_ants=2000),
        predators=PredatorConfig(initial_count=50),
        nest=NestConfig(initial_food=1000.0),
    )
    model = HybridModel(config, 1)
    for _ in range(20):
        model.step()
    started = time.perf_counter()
    for _ in range(200):
        model.step()
    return (time.perf_counter() - started) / 200 * 1000


def style() -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": SURFACE,
            "axes.facecolor": SURFACE,
            "savefig.facecolor": SURFACE,
            "axes.edgecolor": GRID,
            "axes.labelcolor": INK_SECONDARY,
            "axes.titlecolor": INK,
            "axes.titlesize": 10,
            "axes.labelsize": 9,
            "xtick.color": INK_SECONDARY,
            "ytick.color": INK_SECONDARY,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "text.color": INK,
            "axes.grid": True,
            "grid.color": GRID,
            "grid.linewidth": 0.8,
            "axes.axisbelow": True,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "font.family": "DejaVu Sans",
            "legend.frameon": False,
            "legend.fontsize": 8,
        }
    )


def padded(runs: list[dict]) -> np.ndarray:
    matrix = np.zeros((len(runs), TICKS + 1))
    for row, run in enumerate(runs):
        matrix[row, : len(run["population"])] = run["population"]
    return matrix


def plot_population(grouped: dict[str, list[dict]]) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(7.4, 5.0), sharex=True, sharey=True)
    ticks = np.arange(TICKS + 1)
    top = max(padded(runs).max() for runs in grouped.values()) * 1.08
    for axis, (scenario_id, runs) in zip(axes.flat, grouped.items()):
        matrix = padded(runs)
        for start, end in runs[0]["windows"]:
            axis.axvspan(start, end, color=INK_SECONDARY, alpha=0.12, linewidth=0)
            axis.text(
                (start + end) / 2, top * 0.97, EVENT_LABELS[scenario_id], ha="center", va="top", fontsize=7.5, color=INK_SECONDARY
            )
        axis.fill_between(ticks, matrix.min(axis=0), matrix.max(axis=0), color=BLUE, alpha=0.14, linewidth=0)
        axis.plot(ticks, matrix.mean(axis=0), color=BLUE, linewidth=2, solid_capstyle="round")
        axis.set_title(NAMES[scenario_id], loc="left")
        axis.set_ylim(0, top)
        axis.set_xlim(0, TICKS)
        axis.set_xticks(XTICKS)
    for axis in axes[1]:
        axis.set_xlabel("Tick")
    for axis in axes[:, 0]:
        axis.set_ylabel("Hormigas vivas")
    fig.tight_layout()
    fig.savefig(FIGURES / "poblacion.pdf")
    plt.close(fig)


def plot_nest(run: dict) -> None:
    stocks = np.array(run["stocks"])
    ticks = np.arange(1, len(stocks) + 1) * SAMPLE_EVERY
    fig, (top, bottom) = plt.subplots(2, 1, figsize=(7.4, 4.8), sharex=True)
    top.plot(ticks, stocks[:, 0], color=BLUE, linewidth=2, solid_capstyle="round")
    top.set_ylabel("Comida en el nido")
    top.set_title("Reserva de comida", loc="left")
    series = [(3, "Obreras (agentes vivos)", BLUE), (2, "Larvas", ORANGE), (1, "Huevos", AQUA)]
    for column, label, color in series:
        bottom.plot(ticks, stocks[:, column], color=color, linewidth=2, solid_capstyle="round", label=label)
    bottom.set_ylabel("Individuos")
    bottom.set_xlabel("Tick")
    bottom.set_title("Población por etapa", loc="left")
    bottom.legend(loc="center right", ncol=1)
    for axis in (top, bottom):
        axis.set_xlim(0, TICKS)
        axis.set_xticks(XTICKS)
    fig.tight_layout()
    fig.savefig(FIGURES / "nido.pdf")
    plt.close(fig)


def plot_deaths(grouped: dict[str, list[dict]]) -> None:
    fig, axis = plt.subplots(figsize=(7.4, 2.9))
    labels = list(grouped)
    left = np.zeros(len(labels))
    for key, name, color in CAUSES:
        values = np.array([np.mean([run["deaths"][key] for run in grouped[scenario]]) for scenario in labels])
        axis.barh(
            range(len(labels)), values, left=left, height=0.5, color=color, edgecolor=SURFACE, linewidth=1.5, label=name
        )
        left += values
    for row, total in enumerate(left):
        axis.text(total + 12, row, f"{total:.0f}", va="center", fontsize=8, color=INK_SECONDARY)
    axis.set_yticks(range(len(labels)), [NAMES[scenario] for scenario in labels])
    axis.invert_yaxis()
    axis.set_xlabel("Muertes acumuladas en 20 000 ticks (media de 5 semillas)")
    axis.grid(axis="y", visible=False)
    axis.set_xlim(0, left.max() * 1.1)
    axis.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=4, columnspacing=1.6)
    fig.tight_layout()
    fig.savefig(FIGURES / "muertes.pdf")
    plt.close(fig)


def number(value: float, digits: int = 0) -> str:
    return f"{value:,.{digits}f}".replace(",", "\\,")


def write_tables(grouped: dict[str, list[dict]], tick_ms: float) -> None:
    rows_summary = []
    rows_deaths = []
    for scenario_id, runs in grouped.items():
        alive = sum(run["alive"] for run in runs)
        drops = [
            max((1 - r["minimum"] / r["before"] for r in run["recoveries"] if r["before"]), default=0.0) for run in runs
        ]
        recovered = sum(all(r["ticks"] is not None for r in run["recoveries"]) for run in runs) if runs[0]["recoveries"] else None
        rows_summary.append(
            " & ".join(
                [
                    NAMES[scenario_id],
                    f"{alive}/{len(runs)}",
                    number(np.mean([run["final"] for run in runs])),
                    number(np.mean([run["peak"] for run in runs])),
                    "--" if not runs[0]["recoveries"] else f"{np.mean(drops) * 100:.0f}\\,\\%",
                    "--" if recovered is None else f"{recovered}/{len(runs)}",
                    number(np.mean([run["delivered"] for run in runs])),
                ]
            )
            + r" \\"
        )
        rows_deaths.append(
            " & ".join(
                [NAMES[scenario_id]]
                + [number(np.mean([run["deaths"][key] for run in runs])) for key, _, _ in CAUSES]
            )
            + r" \\"
        )
    kills = sum(run["deaths"]["predator"] for run in grouped["predator_invasion"])
    totals = sum(sum(run["deaths"].values()) for run in grouped["predator_invasion"])
    flood_deaths = [run["deaths"]["flood"] for run in grouped["flood"]]
    content = [
        r"\newcommand{\tablaresumen}{" + "\n" + "\n".join(rows_summary) + "\n}",
        r"\newcommand{\tablamuertes}{" + "\n" + "\n".join(rows_deaths) + "\n}",
        rf"\newcommand{{\msportick}}{{{tick_ms:.1f}}}",
        rf"\newcommand{{\comparteinvasion}}{{{kills / totals * 100:.0f}}}",
        rf"\newcommand{{\muertesinundacionmin}}{{{min(flood_deaths)}}}",
        rf"\newcommand{{\muertesinundacionmax}}{{{max(flood_deaths)}}}",
    ]
    (OUTPUT / "tablas.tex").write_text("\n".join(content) + "\n", encoding="utf-8")


def main() -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    style()
    if CACHE.exists() and "--fresh" not in sys.argv:
        results = pickle.loads(CACHE.read_bytes())
    else:
        jobs = [(scenario_id, seed) for scenario_id in NAMES for seed in SEEDS]
        with ProcessPoolExecutor() as pool:
            results = list(pool.map(simulate, jobs))
        CACHE.write_bytes(pickle.dumps(results))
    grouped = {scenario_id: [run for run in results if run["scenario"] == scenario_id] for scenario_id in NAMES}
    tick_ms = measure_tick_time()
    plot_population(grouped)
    plot_nest(grouped["baseline"][0])
    plot_deaths(grouped)
    write_tables(grouped, tick_ms)
    summary = {
        scenario_id: [{k: v for k, v in run.items() if k not in ("population", "stocks")} for run in runs]
        for scenario_id, runs in grouped.items()
    }
    (OUTPUT / "resultados.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Listo: {len(results)} corridas, {tick_ms:.1f} ms por tick")


if __name__ == "__main__":
    main()
