import base64

import numpy as np

from hormiguero.schemas.state import FieldData, FieldLayer


def downsample_grid(values: np.ndarray, factor: int) -> np.ndarray:
    if factor == 1:
        return values
    height, width = values.shape[0] // factor, values.shape[1] // factor
    trimmed = values[: height * factor, : width * factor]
    return trimmed.reshape(height, factor, width, factor).mean(axis=(1, 3))


def encode_field(layer: FieldLayer, values: np.ndarray, downsample: int = 1, scale: float | None = None) -> FieldData:
    grid = downsample_grid(values, downsample)
    if scale is None:
        scale = float(grid.max()) if grid.size else 0.0
    normalized = np.clip(grid / scale, 0, 1) if scale > 0 else np.zeros_like(grid)
    data = np.round(normalized * 255).astype(np.uint8).tobytes()
    return FieldData(
        layer=layer,
        width=grid.shape[1],
        height=grid.shape[0],
        downsample=downsample,
        encoding="uint8_base64",
        scale=scale,
        data=base64.b64encode(data).decode("ascii"),
    )


def disk_mask(shape: tuple[int, int], x: int, y: int, radius: int) -> np.ndarray:
    rows, cols = np.ogrid[: shape[0], : shape[1]]
    return (cols - x) ** 2 + (rows - y) ** 2 <= radius**2


def stroke_mask(shape: tuple[int, int], cells: list[tuple[int, int]], radius: int) -> np.ndarray:
    mask = np.zeros(shape, dtype=bool)
    offsets = np.arange(-radius, radius + 1)
    brush = offsets[None, :] ** 2 + offsets[:, None] ** 2 <= radius**2
    for x, y in cells:
        top, left = y - radius, x - radius
        row_start, col_start = max(top, 0), max(left, 0)
        row_end, col_end = min(y + radius + 1, shape[0]), min(x + radius + 1, shape[1])
        mask[row_start:row_end, col_start:col_end] |= brush[
            row_start - top : row_end - top, col_start - left : col_end - left
        ]
    return mask
