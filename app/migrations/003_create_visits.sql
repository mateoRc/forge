CREATE TABLE visits (
    id INTEGER PRIMARY KEY,
    visited_at TEXT NOT NULL,
    visitor_id TEXT NOT NULL
);
CREATE INDEX visits_visited_at_idx ON visits (visited_at);
CREATE INDEX visits_visitor_id_idx ON visits (visitor_id);
