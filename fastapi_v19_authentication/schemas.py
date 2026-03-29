"""Pydantic schemas for FastAPI V19 Authentication."""
from pydantic import BaseModel


class LoginRequest(BaseModel):
    """Request body for client credentials login."""
    client_id: str
    client_secret: str


class LoginResponse(BaseModel):
    """Response for successful login."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    expires_in_minutes: int  # minutes (for backward compatibility)
