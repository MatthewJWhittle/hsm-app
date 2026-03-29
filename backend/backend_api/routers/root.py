"""Root and health endpoints."""

from fastapi import APIRouter

router = APIRouter(tags=["meta"])


@router.get("/")
async def root():
    return {"message": "Welcome to HSM Visualiser API"}


@router.get("/health")
async def health_check():
    return {"status": "healthy"}
