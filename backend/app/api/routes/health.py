"""Health check endpoint.

Simple liveness probe used by the frontend (and any future monitoring
tooling) to confirm the API process is up and responding.
"""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def get_health() -> dict[str, str]:
    """Return a static health payload."""
    return {
        "status": "healthy",
        "service": "AI Fleet Management API",
    }
