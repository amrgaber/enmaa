"""JWT Authentication utilities for FastAPI V19 Authentication."""
import jwt
import logging
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Callable
from collections import defaultdict

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from odoo import api

from .constants import (
    TOKEN_TYPE_ACCESS,
    DEFAULT_JWT_ALGORITHM,
    DEFAULT_JWT_SECRET,
    PARAM_KEY_JWT_SECRET,
    DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES,
    PARAM_KEY_ACCESS_EXPIRE_MIN,
    PARAM_KEY_CLIENT_ID,
    PARAM_KEY_CLIENT_SECRET,
    DEFAULT_RATE_LIMIT_MAX,
    DEFAULT_RATE_LIMIT_WINDOW_SECONDS,
    PARAM_KEY_RATE_LIMIT,
    PARAM_KEY_RATE_LIMIT_WINDOW,
    RATE_LIMIT_KEY_PREFIX,
    ERROR_MSG_INVALID_TOKEN,
)

_logger = logging.getLogger(__name__)

# FastAPI security scheme for Bearer token
security = HTTPBearer()

# Simple in-memory rate limit storage (for production, use Redis)
_rate_limit_store: Dict[str, list] = defaultdict(list)


def get_jwt_secret(env) -> str:
    """Get JWT secret from system parameters or default."""
    try:
        return env['ir.config_parameter'].sudo().get_param(
            PARAM_KEY_JWT_SECRET,
            default=DEFAULT_JWT_SECRET
        )
    except Exception:
        return DEFAULT_JWT_SECRET


def generate_access_token(env, user_id: int, partner_id: Optional[int] = None, email: Optional[str] = None) -> str:
    """
    Generate a JWT access token.
    """
    secret_key = get_jwt_secret(env)
    expire_minutes = int(env['ir.config_parameter'].sudo().get_param(
        PARAM_KEY_ACCESS_EXPIRE_MIN,
        default=str(DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES)
    ))
    expire = datetime.utcnow() + timedelta(minutes=expire_minutes)
    
    payload = {
        "user_id": user_id,
        "partner_id": partner_id,
        "email": email,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": TOKEN_TYPE_ACCESS
    }
    
    return jwt.encode(payload, secret_key, algorithm=DEFAULT_JWT_ALGORITHM)


def authenticate_client(env, client_id: str, client_secret: str) -> bool:
    """
    Verify client credentials against system parameters.
    """
    config_client_id = env['ir.config_parameter'].sudo().get_param(PARAM_KEY_CLIENT_ID)
    config_client_secret = env['ir.config_parameter'].sudo().get_param(PARAM_KEY_CLIENT_SECRET)
    
    if not config_client_id or not config_client_secret:
        _logger.warning("Client ID or Secret not configured in system parameters")
        return False
        
    return client_id == config_client_id and client_secret == config_client_secret


def validate_token(token: str, env) -> Optional[Dict[str, Any]]:
    """
    Validate JWT token and return payload.
    """
    try:
        secret_key = get_jwt_secret(env)
        payload = jwt.decode(token, secret_key, algorithms=[DEFAULT_JWT_ALGORITHM])
        
        # Check token type
        if payload.get("type") != TOKEN_TYPE_ACCESS:
            _logger.warning("Token type mismatch")
            return None
        
        return payload
    
    except jwt.ExpiredSignatureError:
        _logger.warning("Token has expired")
        return None
    except jwt.InvalidTokenError as e:
        _logger.warning("Invalid token: %s", str(e))
        return None
    except Exception as e:
        _logger.error("Error validating token: %s", str(e))
        return None


def create_jwt_auth_dependency(registry, uid, context) -> Callable:
    """
    Factory function to create a JWT authentication dependency.
    """
    def jwt_auth(
        credentials: HTTPAuthorizationCredentials = Depends(security)
    ) -> Dict[str, Any]:
        """
        FastAPI dependency to authenticate requests using JWT tokens.
        """
        try:
            with registry.cursor() as cr:
                env = api.Environment(cr, uid, context)
                
                payload = validate_token(credentials.credentials, env)
                
                if not payload:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail=ERROR_MSG_INVALID_TOKEN,
                        headers={"WWW-Authenticate": "Bearer"},
                    )
                
                user_id = payload.get("user_id")
                if not user_id:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid token payload",
                        headers={"WWW-Authenticate": "Bearer"},
                    )
                
                _logger.debug("Auth successful for user %d", user_id)
                
                return {
                    "user_id": int(user_id),
                    "partner_id": payload.get("partner_id"),
                    "email": payload.get("email"),
                    "token_payload": payload
                }
        
        except HTTPException:
            raise
        except Exception as e:
            _logger.error("Authentication error: %s", str(e))
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    return jwt_auth


def create_rate_limit_dependency(registry, uid, context) -> Callable:
    """
    Factory function to create a rate limiting dependency.
    """
    def rate_limit(
        credentials: HTTPAuthorizationCredentials = Depends(security)
    ) -> None:
        """
        FastAPI dependency to enforce rate limiting.
        """
        try:
            with registry.cursor() as cr:
                env = api.Environment(cr, uid, context)
                
                # Get rate limit settings
                max_requests = int(env['ir.config_parameter'].sudo().get_param(
                    PARAM_KEY_RATE_LIMIT,
                    default=str(DEFAULT_RATE_LIMIT_MAX)
                ))
                window_seconds = int(env['ir.config_parameter'].sudo().get_param(
                    PARAM_KEY_RATE_LIMIT_WINDOW,
                    default=str(DEFAULT_RATE_LIMIT_WINDOW_SECONDS)
                ))
                
                # Use token as rate limit key
                key = f"{RATE_LIMIT_KEY_PREFIX}:{credentials.credentials[:20]}"
                current_time = time.time()
                
                # Clean old entries
                _rate_limit_store[key] = [
                    t for t in _rate_limit_store[key]
                    if current_time - t < window_seconds
                ]
                
                # Check limit
                if len(_rate_limit_store[key]) >= max_requests:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="Rate limit exceeded. Please try again later.",
                    )
                
                # Record request
                _rate_limit_store[key].append(current_time)
        
        except HTTPException:
            raise
        except Exception as e:
            _logger.error("Rate limit check error: %s", str(e))
            # Don't block on rate limit errors
            pass
    
    return rate_limit
