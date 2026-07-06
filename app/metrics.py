from collections import Counter
from collections import deque
from dataclasses import dataclass, field
from statistics import median
from threading import Lock

from app.models import Event, Summary

MAX_DURATION_SAMPLES = 2048


@dataclass(frozen=True)
class EventKey:
    service: str
    event: str
    name: str


@dataclass
class EventMetrics:
    requests: int = 0
    errors: int = 0
    duration_ms: int = 0
    durations: deque[int] = field(
        default_factory=lambda: deque(maxlen=MAX_DURATION_SAMPLES)
    )

    def record(self, event: Event) -> None:
        self.requests += 1
        self.errors += int(event.exit_code != 0)
        self.duration_ms += event.duration_ms
        self.durations.append(event.duration_ms)


class Metrics:
    def __init__(self) -> None:
        self._lock = Lock()
        self._events: dict[EventKey, EventMetrics] = {}

    def record(self, event: Event) -> None:
        with self._lock:
            key = EventKey(event.service, event.event, event.name)
            values = self._events.setdefault(key, EventMetrics())
            values.record(event)

    def summary(
        self,
        service: str | None = None,
        event: str | None = None,
        name: str | None = None,
    ) -> Summary:
        with self._lock:
            requests = 0
            errors = 0
            duration_ms = 0
            durations: list[int] = []
            services: Counter[str] = Counter()
            commands: Counter[str] = Counter()

            for key, values in self._events.items():
                if service is not None and key.service != service:
                    continue
                if event is not None and key.event != event:
                    continue
                if name is not None and key.name != name:
                    continue
                requests += values.requests
                errors += values.errors
                duration_ms += values.duration_ms
                durations.extend(values.durations)
                services[key.service] += values.requests
                commands[key.name] += values.requests

            average = duration_ms / requests if requests else 0.0
            median_duration = median(durations) if durations else 0.0
            return Summary(
                requests=requests,
                errors=errors,
                avg_ms=round(average, 2),
                median_ms=round(median_duration, 2),
                services=dict(services.most_common()),
                commands=dict(commands.most_common()),
            )

    def reset(self) -> None:
        with self._lock:
            self._events.clear()
