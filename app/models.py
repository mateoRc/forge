from pydantic import BaseModel, ConfigDict, Field

MAX_DURATION_MS = 24 * 60 * 60 * 1000
MAX_EXIT_CODE = 255


class Event(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    service: str = Field(
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$",
    )
    event: str = Field(
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$",
    )
    name: str = Field(
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$",
    )
    duration_ms: int = Field(ge=0, le=MAX_DURATION_MS)
    exit_code: int = Field(ge=0, le=MAX_EXIT_CODE)


class Summary(BaseModel):
    window_hours: int
    requests: int
    errors: int
    avg_ms: float
    median_ms: float
    p95_ms: float
    services: dict[str, int]
    commands: dict[str, int]
    retained_events: int
    oldest_event_age_days: int | None
    database_bytes: int | None
    database_max_bytes: int
