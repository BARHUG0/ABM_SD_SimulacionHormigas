from dataclasses import dataclass


@dataclass
class NestReport:
    new_workers: int = 0
    starvation_deaths: int = 0
