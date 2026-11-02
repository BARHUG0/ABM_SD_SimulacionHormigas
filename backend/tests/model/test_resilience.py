from hormiguero.engine.model.resilience import ResilienceTracker
from hormiguero.schemas.events import EventInfo, EventStatus, PerturbationType


def make_event(event_id="evt_1", start=10, duration=5):
    return EventInfo(
        id=event_id,
        type=PerturbationType.DROUGHT,
        intensity=0.5,
        duration=duration,
        start_tick=start,
        end_tick=start + duration,
        region=None,
        predator_count=None,
        status=EventStatus.ACTIVE,
    )


def test_tracks_peak_minimum_and_mean_efficiency():
    tracker = ResilienceTracker()
    for tick, (population, efficiency) in enumerate([(100, 0.0), (120, 0.2), (80, 0.4), (90, 0.6)]):
        tracker.record(tick, population, efficiency)
    assert tracker.peak_population == 120
    assert tracker.min_population == 80
    assert tracker.min_population_tick == 2
    assert abs(tracker.mean_efficiency - 0.3) < 1e-12


def test_event_recovery_counts_ticks_after_the_end():
    tracker = ResilienceTracker()
    event = make_event()
    tracker.record(9, 100, 0.0)
    tracker.start_event(event, 100)
    for tick, population in zip(range(10, 15), [90, 70, 60, 65, 75]):
        tracker.record(tick, population, 0.0)
    tracker.record(15, 80, 0.0)
    tracker.end_event(event)
    for tick, population in zip(range(16, 20), [90, 99, 100, 130]):
        tracker.record(tick, population, 0.0)
    info = tracker.recovery(event)
    assert info.population_before == 100
    assert info.min_population_during == 60
    assert info.recovery_ticks == 3


def test_recovery_is_none_when_population_never_returns():
    tracker = ResilienceTracker()
    event = make_event()
    tracker.record(9, 100, 0.0)
    tracker.start_event(event, 100)
    tracker.record(10, 50, 0.0)
    tracker.end_event(event)
    for tick in range(11, 30):
        tracker.record(tick, 60, 0.0)
    assert tracker.recovery(event).recovery_ticks is None


def test_recovery_is_zero_when_population_already_recovered_at_the_end():
    tracker = ResilienceTracker()
    event = make_event()
    tracker.record(9, 100, 0.0)
    tracker.start_event(event, 100)
    tracker.record(10, 120, 0.0)
    tracker.end_event(event)
    assert tracker.recovery(event).recovery_ticks == 0


def test_minimum_stops_updating_after_the_event_ends():
    tracker = ResilienceTracker()
    event = make_event()
    tracker.start_event(event, 100)
    tracker.record(10, 80, 0.0)
    tracker.end_event(event)
    tracker.record(11, 10, 0.0)
    assert tracker.recovery(event).min_population_during == 80
    assert tracker.min_population == 10
