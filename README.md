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

All three endpoints require `Authorization: Bearer <FORGE_AUTH_TOKEN>`.
`GET /healthz` remains public for container health checks. In the standard
Compose deployment Forge has no published host port; the direct examples
below apply only when running Forge separately for development.

Record events:

```sh
curl -i -X POST http://localhost:8082/events \
  -H "Authorization: Bearer $FORGE_AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"service":"vault","event":"command.executed","name":"grep","duration_ms":8,"exit_code":0}'

curl -i -X POST http://localhost:8082/events \
  -H "Authorization: Bearer $FORGE_AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"service":"atlas","event":"search.executed","name":"search","duration_ms":12,"exit_code":1}'
```

Read all metrics or filter by exact `service`, `event`, and `name` values:

```sh
curl -H "Authorization: Bearer $FORGE_AUTH_TOKEN" http://localhost:8082/summary
curl -H "Authorization: Bearer $FORGE_AUTH_TOKEN" \
  "http://localhost:8082/summary?service=vault"
curl -H "Authorization: Bearer $FORGE_AUTH_TOKEN" \
  "http://localhost:8082/summary?event=search.executed&name=search"
```

Render the dashboard with a bar width from 1 through 100:

```sh
curl -H "Authorization: Bearer $FORGE_AUTH_TOKEN" \
  http://localhost:8082/dashboard
curl -H "Authorization: Bearer $FORGE_AUTH_TOKEN" \
  "http://localhost:8082/dashboard?width=30&service=vault"
```

Unknown event types are accepted and aggregated, allowing producers and Forge
to be deployed independently.

Deployment requires `FORGE_AUTH_TOKEN`. Keep it in the deployment secret store
rather than the image or repository. Bearer authentication does not encrypt
traffic, so terminate TLS at the deployment ingress.

Build a version-labeled image:

```sh
docker build --build-arg VERSION=1.0.0 --tag forge:1.0.0 .
docker inspect forge:1.0.0 --format "{{ index .Config.Labels \"org.opencontainers.image.version\" }}"
```

## Test

```sh
docker build --target test .
```

Long-form documentation and the Forge roadmap are maintained in the sibling
`lab` repository under `content/docs/`.
