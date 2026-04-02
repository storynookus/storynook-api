# StoryNook API

FastAPI service for story generation and continuation using Vertex AI (Gemini + Imagen), with Docker and Cloud Run deployment support.

## Tech Stack

- Python 3.10+
- FastAPI
- Vertex AI Gemini (`gemini-2.5-flash`)
- Imagen (`imagen-4.0-generate-001`)
- Docker + Cloud Build + Cloud Run

## Available Endpoints

### Public

- `GET /healthz`
- `GET /api/v1/template/ping`

### Protected (Bearer token)

- `GET /health`
- `GET /endpoints`
- `POST /api/v1/template/protected`
- `POST /generate-story`
- `POST /continue-story`

Swagger docs: `/docs`

## Environment Variables

Core app settings:

- `APP_NAME` (default: `StoryNook API`)
- `API_V1_PREFIX` (default: `/api/v1`)
- `APP_ENV` (`dev` or `prod`)
- `DEV_API_TOKEN`
- `PROD_API_TOKEN`
- `CORS_ORIGINS` (JSON list, example: `["*"]`)

Story generation settings:

- `GCP_PROJECT` (default: `storynook-491620`)
- `GCP_LOCATION` (Gemini region, default: `us-east1`)
- `IMAGEN_LOCATION` (Imagen region, default: `us-central1`)
- `IMAGE_GENERATION_DELAY_SECONDS` (default: `3`)
- `IMAGE_WORKERS` (default: `1`)

Notes:

- Story endpoints work with defaults if these vars are not set.
- In production, set `GCP_PROJECT` and regions explicitly to avoid surprises between environments.

## Run Locally

### 1) Start in dev mode

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8080
```

Dev server will be available at `http://localhost:8080`.

### 2) Verify it is running

```bash
curl http://localhost:8080/healthz
```

## Run with Docker

```bash
docker build -t storynook-api:local .
docker run --rm -p 8080:8080 \
  -e APP_ENV=dev \
  -e DEV_API_TOKEN=dev-local-token \
  -e PROD_API_TOKEN=prod-local-token \
  -e GCP_PROJECT=storynook-491620 \
  -e GCP_LOCATION=us-east1 \
  -e IMAGEN_LOCATION=us-central1 \
  storynook-api:local
```

## Sample Requests

```bash
BASE_URL=http://localhost:8080
TOKEN=dev-change-this-token
```

If you changed `DEV_API_TOKEN` in `.env`, set `TOKEN` to that value.

Health checks:

```bash
curl -X GET "$BASE_URL/healthz"
curl -X GET "$BASE_URL/health" \
  -H "Authorization: Bearer $TOKEN"
curl -X GET "$BASE_URL/endpoints" \
  -H "Authorization: Bearer $TOKEN"
```

Template ping:

```bash
curl -X GET "$BASE_URL/api/v1/template/ping"
```

Template protected:

```bash
curl -X POST "$BASE_URL/api/v1/template/protected" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"sample":"value"}'
```

Generate story (single child):

```bash
curl -X POST "$BASE_URL/generate-story" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "childName": "Liam",
    "childAge": "7",
    "interests": "space adventure",
    "moral": "kindness",
    "customPrompt": "Include a friendly moon dragon",
    "language": "English",
    "pageCount": 5
  }'
```

Generate story (multi-kid):

```bash
curl -X POST "$BASE_URL/generate-story" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "childAge": "8",
    "interests": "jungle mystery",
    "moral": "collaboration",
    "language": "English",
    "pageCount": 6,
    "kidsData": [
      { "name": "Ava" },
      { "name": "Noah" }
    ]
  }'
```

Continue story:

```bash
curl -X POST "$BASE_URL/continue-story" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "currentPage": 3,
    "currentText": "Liam and the moon dragon found a glowing map under the starlight tree.",
    "kidInput": "They should follow the map into a cave of singing crystals.",
    "childName": "Liam",
    "moral": "courage"
  }'
```

## Cloud Build / Cloud Run

Deployment is defined in `cloudbuild.yaml`:

- Builds and pushes Docker image to Artifact Registry
- Deploys to Cloud Run
- Sets runtime env var `APP_ENV`
- Injects `PROD_API_TOKEN` from Secret Manager

If you want explicit runtime config for story generation, add these in deploy env vars:

- `GCP_PROJECT`
- `GCP_LOCATION`
- `IMAGEN_LOCATION`
- `IMAGE_GENERATION_DELAY_SECONDS`
- `IMAGE_WORKERS`