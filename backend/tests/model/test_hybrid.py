import time

import numpy as np

from hormiguero.engine.model.hybrid import HybridModel
from hormiguero.engine.parameters import apply_parameter_update
from hormiguero.engine.simulation import Simulation
from hormiguero.schemas.config import AntConfig, NestConfig, PredatorConfig, SimulationConfig
from hormiguero.schemas.events import EventInfo, EventStatus, PerturbationType
from hormiguero.schemas.simulation import ControlAction, ControlRequest


def make_event(event_type, **fields):
    return EventInfo(
        id=fields.pop("id", "evt_1"),
        type=event_type,
        intensity=fields.pop("intensity", 0.7),
        duration=fields.pop("duration", 100),
        start_tick=fields.pop("start_tick", 10),
        end_tick=fields.pop("end_tick", 110),
        region=fields.pop("region", None),
        predator_count=fields.pop("predator_count", None),
        status=EventStatus.ACTIVE,
    )


def test_population_invariants_hold_every_tick():
    model = HybridModel(SimulationConfig(), seed=3)
    for _ in range(2000):
        model.step()
        frame = model.frame([])
        assert model.nest.stocks.workers == model.colony.size
        assert frame.metrics.alive_ants == model.colony.size
        assert frame.metrics.foragers_active == model.colony.size - frame.metrics.ants_in_nest


def test_deaths_never_decrease():
    model = HybridModel(SimulationConfig(), seed=5)
    previous = 0
    for _ in range(600):
        model.step()
        total = sum(model.deaths.model_dump().values())
        assert total >= previous
        previous = total


def test_same_seed_produces_identical_frames():
    def run():
        model = HybridModel(SimulationConfig(), seed=11)
        model.paint_obstacles([(60, 60), (70, 62)], 3, True)
        model.add_food(40, 40, 5, 300.0)
        drought = make_event(PerturbationType.DROUGHT, start_tick=100, end_tick=400, duration=300)
        for _ in range(500):
            model.step()
            if model.tick == 100:
                model.start_event(drought)
        return model.frame([drought.id]).model_dump()

    assert run() == run()


def test_live_nest_parameter_changes_next_tick():
    config = SimulationConfig()
    model = HybridModel(config, seed=1)
    for _ in range(5):
        model.step()
    before = model.frame([]).nest.flows.egg_laying
    model.config = apply_parameter_update(config, {"nest.max_egg_laying_rate": 2.0}, allow_non_live=False)
    model.step()
    after = model.frame([]).nest.flows.egg_laying
    assert after > before * 2


def test_predator_wave_respects_limit_and_removes_its_predators():
    config = SimulationConfig(predators=PredatorConfig(initial_count=1, max_predators=6))
    model = HybridModel(config, seed=2)
    wave = make_event(PerturbationType.PREDATOR_WAVE, predator_count=20)
    model.start_event(wave)
    assert len(model.predators) == 6
    model.step()
    model.end_event(wave)
    assert len(model.predators) == 1
    assert wave.id not in model.wave_predators


def test_user_predators_are_added_and_removed():
    model = HybridModel(SimulationConfig(predators=PredatorConfig(initial_count=0)), seed=2)
    ids = model.add_predators(30, 30, 3)
    assert len(ids) == len(set(ids)) == 3
    assert all(abs(model.predators[i].x - 30) < 10 for i in ids)
    assert model.remove_predator(ids[0]) is True
    assert model.remove_predator(ids[0]) is False


def test_frame_fields_are_consistent_with_model_state():
    model = HybridModel(SimulationConfig(), seed=4)
    for _ in range(50):
        model.step()
    frame = model.frame(["x"])
    assert frame.active_event_ids == ["x"]
    assert len(frame.ants.ids) == model.colony.size
    assert frame.metrics.food_in_world == model.world.food_in_world
    assert frame.nest.stocks.workers == model.colony.size


def test_summary_minimum_is_exact_after_history_compaction():
    from hormiguero.engine.history import History

    simulation = Simulation("sim_test", "test", SimulationConfig(), seed=1, scenario=None)
    simulation.history = History(capacity=8)
    observed = [simulation.model.colony.size]
    for _ in range(300):
        simulation.control(ControlRequest(action=ControlAction.STEP, steps=1))
        observed.append(simulation.model.colony.size)
    assert simulation.history.resolution > 1
    summary = simulation.summary()
    assert summary.min_population == min(observed)
    assert summary.peak_population == max(observed)
    assert summary.min_population_tick == observed.index(min(observed))


def test_full_tick_stays_under_fifteen_milliseconds():
    config = SimulationConfig(
        ants=AntConfig(initial_workers=2000, max_ants=2000),
        predators=PredatorConfig(initial_count=50),
        nest=NestConfig(initial_food=1000.0),
    )
    model = HybridModel(config, seed=1)
    for _ in range(20):
        model.step()
    started = time.perf_counter()
    for _ in range(200):
        model.step()
    average = (time.perf_counter() - started) / 200
    assert average < 0.015, f"{average * 1000:.1f} ms por tick"
