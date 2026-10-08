from annotated_types import Ge, Le
from pydantic import BaseModel, ValidationError

from hormiguero.errors import conflict, unprocessable
from hormiguero.schemas.config import SimulationConfig
from hormiguero.schemas.parameters import ParameterSpec


def _build_specs() -> dict[str, ParameterSpec]:
    specs = {}
    for group, group_field in SimulationConfig.model_fields.items():
        group_model: type[BaseModel] = group_field.annotation
        for name, field in group_model.model_fields.items():
            bounds = {type(item): item for item in field.metadata}
            extra = field.json_schema_extra or {}
            key = f"{group}.{name}"
            specs[key] = ParameterSpec(
                key=key,
                group=group,
                name=name,
                description=field.description or "",
                type="int" if field.annotation is int else "float",
                default=field.default,
                minimum=bounds[Ge].ge,
                maximum=bounds[Le].le,
                unit=extra.get("unit", ""),
                live_editable=extra.get("live_editable", False),
            )
    return specs


PARAMETER_SPECS = _build_specs()


def apply_parameter_update(
    config: SimulationConfig, values: dict[str, float], allow_non_live: bool
) -> SimulationConfig:
    unknown = sorted(key for key in values if key not in PARAMETER_SPECS)
    if unknown:
        raise unprocessable("unknown_parameter", "Parámetros desconocidos", {"keys": unknown})
    locked = sorted(key for key in values if not PARAMETER_SPECS[key].live_editable)
    if locked and not allow_non_live:
        raise conflict(
            "parameter_requires_reset",
            "Estos parámetros solo se pueden cambiar antes de iniciar o tras un reset",
            {"keys": locked},
        )
    data = config.model_dump()
    for key, value in values.items():
        group, name = key.split(".")
        data[group][name] = value
    try:
        return SimulationConfig.model_validate(data)
    except ValidationError as error:
        raise unprocessable(
            "invalid_parameter", "Valores fuera de rango o inconsistentes", error.errors(include_url=False, include_context=False)
        ) from error


def requires_rebuild(values: dict[str, float]) -> bool:
    return any(not PARAMETER_SPECS[key].live_editable for key in values)
