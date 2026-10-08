import csv
import io
from collections import deque

from hormiguero.schemas.metrics import HistoryKey, HistoryResponse
from hormiguero.schemas.state import FrameData

HISTORY_LENGTH = 20_000
METRIC_KEYS = ("alive_ants", "foragers_active", "ants_in_nest", "predators", "food_in_world", "food_delivered_total", "foraging_efficiency")


def history_row(frame: FrameData) -> dict[HistoryKey, float]:
    row = {HistoryKey(f"stocks.{name}"): value for name, value in frame.nest.stocks}
    row |= {HistoryKey(f"flows.{name}"): value for name, value in frame.nest.flows}
    row |= {HistoryKey(f"metrics.{name}"): float(getattr(frame.metrics, name)) for name in METRIC_KEYS}
    row[HistoryKey.NEST_FORAGER_FRACTION] = frame.nest.forager_fraction
    return row


class History:
    def __init__(self, length: int = HISTORY_LENGTH):
        self.ticks: deque[int] = deque(maxlen=length)
        self.series: dict[HistoryKey, deque[float]] = {key: deque(maxlen=length) for key in HistoryKey}

    def append(self, tick: int, frame: FrameData) -> None:
        self.ticks.append(tick)
        for key, value in history_row(frame).items():
            self.series[key].append(value)

    def values(self, key: HistoryKey) -> list[float]:
        return list(self.series[key])

    def query(
        self, keys: list[HistoryKey] | None, from_tick: int = 0, to_tick: int | None = None, every: int = 1
    ) -> HistoryResponse:
        selected_keys = keys or list(HistoryKey)
        ticks = list(self.ticks)
        upper = to_tick if to_tick is not None else (ticks[-1] if ticks else 0)
        indices = [i for i, tick in enumerate(ticks) if from_tick <= tick <= upper][::every]
        series = {key.value: [self.series[key][i] for i in indices] for key in selected_keys}
        return HistoryResponse(keys=selected_keys, ticks=[ticks[i] for i in indices], series=series)

    def to_csv(self) -> str:
        buffer = io.StringIO()
        writer = csv.writer(buffer, lineterminator="\n")
        writer.writerow(["tick", *(key.value for key in HistoryKey)])
        columns = [list(self.series[key]) for key in HistoryKey]
        for index, tick in enumerate(self.ticks):
            writer.writerow([tick, *(column[index] for column in columns)])
        return buffer.getvalue()
