"""FastAPI router for authentication (Client Credentials)."""
import logging
from fastapi import APIRouter, status, HTTPException
from odoo import api

from ..schemas import LoginRequest, LoginResponse
from ..core.auth import authenticate_client, generate_access_token
from ..core.constants import DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES, PARAM_KEY_ACCESS_EXPIRE_MIN

_logger = logging.getLogger(__name__)


def create_auth_router(registry, uid, context):
    """
    Create and return the authentication API router.
    """
    router = APIRouter(
        prefix="/login",
        tags=["Authentication"],
    )
    
    @router.post(
        "",
        response_model=LoginResponse,
        summary="Client Credentials Login",
        description="Exchange Client ID and Client Secret for an Access Token",
    )
    def login(request: LoginRequest):
        try:
            with registry.cursor() as cr:
                env = api.Environment(cr, uid, context)
                
                # Validate credentials
                if not authenticate_client(env, request.client_id, request.client_secret):
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid Client ID or Client Secret",
                    )
                
                # Generate token (linked to the configured user for this endpoint)
                access_token = generate_access_token(env, user_id=uid)
                
                # Get expiry in seconds
                expire_min = int(env['ir.config_parameter'].sudo().get_param(
                    PARAM_KEY_ACCESS_EXPIRE_MIN,
                    default=str(DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES)
                ))
                
                return LoginResponse(
                    access_token=access_token,
                    token_type="bearer",
                    expires_in=expire_min * 60,
                    expires_in_minutes=expire_min
                )
                
        except HTTPException:
            raise
        except Exception as e:
            _logger.error("Login error: %s", str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Internal server error during login: {str(e)}",
            )
    
    return router
