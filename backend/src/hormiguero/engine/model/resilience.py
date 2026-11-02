from dataclasses import dataclass

from hormiguero.schemas.events import EventInfo
from hormiguero.schemas.metrics import RecoveryInfo


@dataclass
class EventTrace:
    population_before: float
    min_population: float
    ended_tick: int | None = None
    recovery_ticks: int | None = None


class ResilienceTracker:
    def __init__(self) -> None:
        self.tick = 0
        self.population = 0.0
        self.peak_population = 0.0
        self.min_population: float | None = None
        self.min_population_tick = 0
        self.efficiency_sum = 0.0
        self.samples = 0
        self.traces: dict[str, EventTrace] = {}

    def record(self, tick: int, population: float, efficiency: float) -> None:
        self.tick = tick
        self.population = population
        self.peak_population = max(self.peak_population, population)
        if self.min_population is None or population < self.min_population:
            self.min_population = population
            self.min_population_tick = tick
        self.efficiency_sum += efficiency
        self.samples += 1
        for trace in self.traces.values():
            if trace.ended_tick is None:
                trace.min_population = min(trace.min_population, population)
            elif trace.recovery_ticks is None and population >= trace.population_before:
                trace.recovery_ticks = tick - trace.ended_tick

    def start_event(self, event: EventInfo, population: float) -> None:
        self.traces[event.id] = EventTrace(population_before=population, min_population=population)

    def end_event(self, event: EventInfo) -> None:
        trace = self.traces.get(event.id)
        if trace is None or trace.ended_tick is not None:
            return
        trace.ended_tick = self.tick
        trace.min_population = min(trace.min_population, self.population)
        if self.population >= trace.population_before:
            trace.recovery_ticks = 0

    @property
    def mean_efficiency(self) -> float:
        return self.efficiency_sum / self.samples if self.samples else 0.0

    def recovery(self, event: EventInfo) -> RecoveryInfo:
        trace = self.traces.get(event.id)
        if trace is None:
            return RecoveryInfo(
                event_id=event.id,
                population_before=self.population,
                min_population_during=self.population,
                recovery_ticks=None,
            )
        return RecoveryInfo(
            event_id=event.id,
            population_before=trace.population_before,
            min_population_during=trace.min_population,
            recovery_ticks=trace.recovery_ticks,
        )
