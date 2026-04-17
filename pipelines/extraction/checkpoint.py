from dataclasses import dataclass


@dataclass(slots=True)
class ExtractionCheckpoint:
    entity_name: str
    last_value: str | None = None
