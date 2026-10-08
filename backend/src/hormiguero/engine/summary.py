from hormiguero.engine.history import History
from hormiguero.schemas.events import EventInfo, EventStatus
from hormiguero.schemas.metrics import HistoryKey, RecoveryInfo, SurvivalSummary
from hormiguero.schemas.state import DeathsByCause


def _recovery(event: EventInfo, ticks: list[int], population: list[float]) -> RecoveryInfo:
    before = next((value for tick, value in zip(reversed(ticks), reversed(population)) if tick < event.start_tick), population[0])
    during = [value for tick, value in zip(ticks, population) if event.start_tick <= tick <= event.end_tick]
    recovery_ticks = next(
        (tick - event.end_tick for tick, value in zip(ticks, population) if tick >= event.end_tick and value >= before),
        None,
    )
    return RecoveryInfo(
        event_id=event.id,
        population_before=before,
        min_population_during=min(during, default=before),
        recovery_ticks=recovery_ticks,
    )


def survival_summary(
    history: History,
    events: list[EventInfo],
    collapse_tick: int | None,
    total_food_delivered: float,
    deaths: DeathsByCause,
) -> SurvivalSummary:
    ticks = list(history.ticks)
    population = history.values(HistoryKey.METRICS_ALIVE_ANTS)
    efficiency = history.values(HistoryKey.METRICS_FORAGING_EFFICIENCY)
    min_index = min(range(len(population)), key=population.__getitem__)
    started = [event for event in events if event.status in (EventStatus.ACTIVE, EventStatus.FINISHED)]
    return SurvivalSummary(
        ticks_elapsed=ticks[-1],
        colony_alive=collapse_tick is None,
        collapse_tick=collapse_tick,
        peak_population=max(population),
        min_population=population[min_index],
        min_population_tick=ticks[min_index],
        mean_foraging_efficiency=sum(efficiency) / len(efficiency),
        total_food_delivered=total_food_delivered,
        deaths=deaths,
        recoveries=[_recovery(event, ticks, population) for event in started],
    )
