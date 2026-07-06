CREATE TABLE events (
    id INTEGER PRIMARY KEY,
    recorded_at TEXT NOT NULL,
    service TEXT NOT NULL,
    event TEXT NOT NULL,
    name TEXT NOT NULL,
    duration_ms INTEGER NOT NULL CHECK (duration_ms >= 0),
    exit_code INTEGER NOT NULL
);
