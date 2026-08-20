# System Architecture

## Runtime Flow

```text
Flutter
  -> Express / BMKG service -> BMKG public forecast
  -> Express / rule engine -> crop recommendation + 4-week calendar
  -> Express visual proxy -> private FastAPI -> mock or SD 1.5 + LoRA provider
  <- Express image proxy <- private generated PNG
  <- recommendation remains independent from visual success
```

1. Flutter collects land type, water availability, and previous crop.
2. Express obtains the available BMKG horizon, exposes timestamp/cache/coverage,
   maps complete precipitation data to a rule category, and executes the
   deterministic decision table.
3. Flutter stores last-known weather/recommendation data locally and renders the
   recommendation before any image request.
4. If requested, Flutter sends the already recommended crop and context to the
   Express visual proxy. Express authenticates, rate-limits, and forwards it to
   private FastAPI. FastAPI builds the prompt and generates only a visual.
5. Express streams the PNG back through its public `/api/visual/images` route;
   Flutter never receives the private inference host or token.
6. Visual failure is isolated and never changes or deletes the recommendation.

Pilot tools may instead send a bounded direct prompt. That compatibility mode
is not used by Flutter, records separate provenance, and does not select a crop
recommendation.

## Ownership Boundaries

| Component | Owns | Does not own |
| --- | --- | --- |
| BMKG service | forecast parsing, cache, stale fallback, rain coverage | crop decision |
| Rule engine | deterministic crop priority and reason | image generation |
| Express visual proxy | client access control, private inference call, PNG delivery | prompt/model execution |
| FastAPI | prompt construction and visual generation | agronomic recommendation |
| Flutter repository | backend calls, local cache, history | inference host credentials |
| LoRA | visual style/subject adaptation | weather prediction or rule replacement |

## Data and Research Boundaries

SQLite schema exists in the Node backend, while the current mobile workflow
uses SharedPreferences for bounded local cache/history. Dataset raw files remain
immutable. Dataset review, final training, and 72/72 visual review are complete.
Public-only crop images are not represented as local Aikmel evidence.

## Deployment Profiles

- `mock`: CPU-safe development; generated placeholders are marked non-research.
- `development`: Express and mock FastAPI on the workstation; Android emulator
  reaches them through `10.0.2.2`.
- `controlled GPU test`: Express and private FastAPI share a RunPod Secure
  Cloud Pod; only Express port 3000 is exposed through HTTPS. Flutter receives
  one backend URL and a short-lived client token.
- `public production`: requires real user identity, durable rate limiting,
  monitoring, and secret management beyond the controlled thesis profile.
