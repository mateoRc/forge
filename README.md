# Forge

Forge is the lightweight telemetry and ASCII dashboard service for Vault and
Atlas. It receives HTTP events, aggregates metrics in memory, and renders
operational summaries.

## Run locally

Run Forge with the other services through the sibling `lab` repository:

```sh
cd ../lab
docker compose up --build
```

Verify the service:

```sh
curl http://localhost:8082/healthz
```

The response is `200 OK` with the body `ok`.

Other endpoints:

- `POST /events`
- `GET /summary`
- `GET /dashboard`

## Test

```sh
docker build --target test .
```

Long-form documentation and the Forge roadmap are maintained in the sibling
`lab` repository under `content/docs/`.
