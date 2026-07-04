from pydantic import BaseModel, Field


class Event(BaseModel):
    service: str = Field(min_length=1)
    event: str = Field(min_length=1)
    name: str = Field(min_length=1)
    duration_ms: int = Field(ge=0)
    exit_code: int


class Summary(BaseModel):
    requests: int
    errors: int
    avg_ms: float
    median_ms: float
    services: dict[str, int]
    commands: dict[str, int]
