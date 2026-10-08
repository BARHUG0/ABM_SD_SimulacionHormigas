import csv
import io

from hormiguero.schemas.metrics import HistoryKey, HistoryResponse
from hormiguero.schemas.state import FrameData

HISTORY_CAPACITY = 20_000
METRIC_KEYS = ("alive_ants", "foragers_active", "ants_in_nest", "predators", "food_in_world", "food_delivered_total", "foraging_efficiency")


def history_row(frame: FrameData) -> dict[HistoryKey, float]:
    row = {HistoryKey(f"stocks.{name}"): value for name, value in frame.nest.stocks}
    row |= {HistoryKey(f"flows.{name}"): value for name, value in frame.nest.flows}
    row |= {HistoryKey(f"metrics.{name}"): float(getattr(frame.metrics, name)) for name in METRIC_KEYS}
    row |= {HistoryKey(f"deaths.{name}"): float(value) for name, value in frame.metrics.deaths}
    row[HistoryKey.NEST_FORAGER_FRACTION] = frame.nest.forager_fraction
    return row


class History:
    def __init__(self, capacity: int = HISTORY_CAPACITY):
        self.capacity = capacity
        self.resolution = 1
        self.ticks: list[int] = []
        self.series: dict[HistoryKey, list[float]] = {key: [] for key in HistoryKey}

    def append(self, tick: int, frame: FrameData) -> None:
        if tick % self.resolution:
            return
        if len(self.ticks) >= self.capacity:
            self._compact()
            if tick % self.resolution:
                return
        self.ticks.append(tick)
        for key, value in history_row(frame).items():
            self.series[key].append(value)

    def _compact(self) -> None:
        self.resolution *= 2
        kept = [index for index, tick in enumerate(self.ticks) if tick % self.resolution == 0]
        self.ticks = [self.ticks[index] for index in kept]
        self.series = {key: [values[index] for index in kept] for key, values in self.series.items()}

    def values(self, key: HistoryKey) -> list[float]:
        return list(self.series[key])

    def query(
        self, keys: list[HistoryKey] | None, from_tick: int = 0, to_tick: int | None = None, every: int = 1
    ) -> HistoryResponse:
        selected_keys = keys or list(HistoryKey)
        upper = to_tick if to_tick is not None else (self.ticks[-1] if self.ticks else 0)
        indices = [i for i, tick in enumerate(self.ticks) if from_tick <= tick <= upper][::every]
        series = {key.value: [self.series[key][i] for i in indices] for key in selected_keys}
        return HistoryResponse(
            keys=selected_keys, resolution=self.resolution, ticks=[self.ticks[i] for i in indices], series=series
        )

    def to_csv(self) -> str:
        buffer = io.StringIO()
        writer = csv.writer(buffer, lineterminator="\n")
        writer.writerow(["tick", *(key.value for key in HistoryKey)])
        columns = [self.series[key] for key in HistoryKey]
        for index, tick in enumerate(self.ticks):
            writer.writerow([tick, *(column[index] for column in columns)])
        return buffer.getvalue()
