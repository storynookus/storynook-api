from typing import Any

from fastapi import APIRouter, Depends, status

from app.api.deps import require_api_token

router = APIRouter(prefix="/template", tags=["Template"])


@router.get("/ping")
def public_ping() -> dict[str, str]:
    return {"message": "Template API is running"}


@router.post("/protected", status_code=status.HTTP_200_OK, dependencies=[Depends(require_api_token)])
def protected_template_post(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "received": payload,
        "note": "Hello from the protected template endpoint! This is where you can implement your business logic.",
    }
