# Forge

The Python/FastAPI telemetry service used by Vaultsh and Atlas. Backend Lab
owns its
[architecture and roadmap](https://github.com/mateoRc/lab/tree/main/content/docs).

## Develop

Run the integrated stack:

```sh
cd ../lab
docker compose up --build
```

For direct API development, run the application directly and set
`FORGE_AUTH_TOKEN`. The container listens on port 8080.

Persistence is enabled when `FORGE_DATABASE_PATH` points to a file. Production
mounts that file on the `forge_data` Docker volume. Optional limits are
`FORGE_RETENTION_DAYS` (default `365`) and `FORGE_MAX_DATABASE_BYTES` (default
`268435456`, or 256 MiB). Without a database path, direct development uses an
in-memory database.

`GET /dashboard` and `GET /summary` default to the last 24 hours. Pass
`hours=168` or `hours=720` for 7 or 30 days, or `window=all` for all retained
events. Unknown command names (exit code 127) are excluded from command
rankings by default; `include_invalid=true` includes them. Request and error
totals always include those events. The all-time range is limited by retention
and database-size settings.

Vaultsh sends a browser-generated UUID on each page load through `/api/visit`.
Forge stores visit timestamps and UUIDs in SQLite. `unique_visitors` in the
summary and dashboard counts distinct UUIDs in the selected time window.
Refreshing a page keeps the same ID; clearing site storage or using another
browser creates a new one. Visits follow the same retention and database-size
limits as events, and are excluded from request and command totals.

## Test

```sh
docker build --target test .
```
