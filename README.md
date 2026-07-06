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

## Test

```sh
docker build --target test .
```
