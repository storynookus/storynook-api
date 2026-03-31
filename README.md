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

Check notion for deployment instuction