from collections import Counter
from threading import Lock

from app.models import Event, Summary


class Metrics:
    def __init__(self) -> None:
        self._lock = Lock()
        self._requests = 0
        self._errors = 0
        self._duration_ms = 0
        self._services: Counter[str] = Counter()
        self._commands: Counter[str] = Counter()

    def record(self, event: Event) -> None:
        with self._lock:
            self._requests += 1
            self._errors += int(event.exit_code != 0)
            self._duration_ms += event.duration_ms
            self._services[event.service] += 1
            self._commands[event.name] += 1

    def summary(self) -> Summary:
        with self._lock:
            average = (
                self._duration_ms / self._requests if self._requests else 0.0
            )
            return Summary(
                requests=self._requests,
                errors=self._errors,
                avg_ms=round(average, 2),
                services=dict(self._services.most_common()),
                commands=dict(self._commands.most_common()),
            )

    def reset(self) -> None:
        with self._lock:
            self._requests = 0
            self._errors = 0
            self._duration_ms = 0
            self._services.clear()
            self._commands.clear()

