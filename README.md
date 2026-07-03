# Forge

Forge receives telemetry from Vaultsh and Atlas, aggregates metrics in memory,
and renders text summaries.

## Run locally

Run Forge with the other services through the sibling `lab` repository:

```sh
cd ../lab
docker compose up --build
```

Forge is private in the standard Compose stack. Run it separately on port 8082
for direct API development.

Other endpoints:

- `POST /events`
- `GET /summary`
- `GET /dashboard`

The dashboard renders request totals, error rate, latency, service traffic, and
popular commands as compact terminal-friendly ASCII output.

## Test

```sh
docker build --target test .
```

Architecture and roadmap documentation lives in the sibling `lab` repository.
