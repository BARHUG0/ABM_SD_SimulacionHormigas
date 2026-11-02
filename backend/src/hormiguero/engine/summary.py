from hormiguero.engine.model.resilience import ResilienceTracker
from hormiguero.schemas.events import EventInfo, EventStatus
from hormiguero.schemas.metrics import SurvivalSummary
from hormiguero.schemas.state import DeathsByCause


def survival_summary(
    current_tick: int,
    tracker: ResilienceTracker,
    events: list[EventInfo],
    collapse_tick: int | None,
    total_food_delivered: float,
    deaths: DeathsByCause,
) -> SurvivalSummary:
    started = [event for event in events if event.status in (EventStatus.ACTIVE, EventStatus.FINISHED)]
    return SurvivalSummary(
        ticks_elapsed=current_tick,
        colony_alive=collapse_tick is None,
        collapse_tick=collapse_tick,
        peak_population=tracker.peak_population,
        min_population=tracker.min_population if tracker.min_population is not None else 0.0,
        min_population_tick=tracker.min_population_tick,
        mean_foraging_efficiency=tracker.mean_efficiency,
        total_food_delivered=total_food_delivered,
        deaths=deaths,
        recoveries=[tracker.recovery(event) for event in started],
    )
