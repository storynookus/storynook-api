from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.template import router as template_router
from app.core.config import settings

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz", tags=["Health"])
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(template_router, prefix=settings.api_v1_prefix)
