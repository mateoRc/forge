CREATE INDEX events_recorded_at_idx ON events (recorded_at);
CREATE INDEX events_dimensions_idx ON events (service, event, name);
