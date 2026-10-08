from hormiguero.schemas.common import ApiModel


class CatalogEntry(ApiModel):
    value: str
    label: str
    unit: str


class Catalog(ApiModel):
    series: list[CatalogEntry]
    layers: list[CatalogEntry]
    ant_roles: list[CatalogEntry]
    ant_states: list[CatalogEntry]
    predator_states: list[CatalogEntry]
    predator_sources: list[CatalogEntry]
    perturbations: list[CatalogEntry]
