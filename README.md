# StoryNook API Template (Python 3.11 + Docker + GCP)

Minimal starter API with:
- FastAPI on Python 3.11
- Bearer token auth (single token check)
- Two tokens: one for dev and one for prod
- Docker image for Cloud Run
- Cloud Build deployment file

## Current Template Endpoints

- `GET /healthz` public healthcheck
- `GET /api/v1/template/ping` public template check
- `POST /api/v1/template/protected` protected template endpoint

Swagger docs are at `/docs`.

## How Token Auth Works

- Set `APP_ENV=dev` or `APP_ENV=prod`
- API chooses token automatically:
  - `dev` uses `DEV_API_TOKEN`
  - `prod` uses `PROD_API_TOKEN`
- Send token in header:

```bash
Authorization: Bearer YOUR_TOKEN
```

## Local Run (without Docker)

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8080
```

## Local Run (Docker)

```bash
docker build -t storynook-api:local .
docker run --rm -p 8080:8080 \
  -e APP_ENV=dev \
  -e DEV_API_TOKEN="dev-local-token" \
  -e PROD_API_TOKEN="prod-local-token" \
  storynook-api:local
```

## Test Protected Template Endpoint

```bash
TOKEN="dev-local-token"

curl -X POST http://localhost:8080/api/v1/template/protected \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"sample":"value"}'
```

## Deploy to Cloud Run via Cloud Build

This repo is set for GitHub-triggered Cloud Build. You do not need to run deploy commands manually.

### 1) In Google Cloud Console (one-time)

- Enable APIs: Cloud Run, Cloud Build, Artifact Registry, Secret Manager
- Create Artifact Registry docker repo named `storynook` in `us-central1`
- Create Secret Manager secret named `storynook-prod-api-token`
- Add the production token value as secret version
- Grant Cloud Run runtime service account access to that secret (`Secret Manager Secret Accessor`)

### 2) Create Cloud Build Trigger (GitHub)

- Go to Cloud Build -> Triggers -> Create Trigger
- Connect your GitHub repo
- Trigger type: push to your deployment branch (for example `main`)
- Config type: `Cloud Build configuration file`
- Config location: `cloudbuild.yaml`

### 3) Trigger Substitutions (in UI)

Set these substitutions in the trigger:

- `_PROJECT_ID=storynook-491620`
- `_SERVICE_NAME=storynook-api`
- `_REGION=us-central1`
- `_REPOSITORY=storynook`
- `_IMAGE_NAME=storynook-api`
- `_APP_ENV=prod`
- `_PROD_API_TOKEN_SECRET=storynook-prod-api-token`

Do not place raw token values in substitutions or in GitHub.

## Environment Variables

- `APP_NAME` default `StoryNook API`
- `API_V1_PREFIX` default `/api/v1`
- `APP_ENV` values `dev` or `prod`
- `DEV_API_TOKEN` required when `APP_ENV=dev`
- `PROD_API_TOKEN` required when `APP_ENV=prod` (recommended from Secret Manager)
- `CORS_ORIGINS` default `["*"]`

## Next Step

Add your real endpoints under the template router and protect them with `Depends(require_api_token)`.
