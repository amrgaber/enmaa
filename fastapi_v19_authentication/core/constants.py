"""Core constants for FastAPI V19 Authentication."""

# JWT Configuration
DEFAULT_JWT_ALGORITHM = "HS256"
DEFAULT_JWT_SECRET = "fastapi-v19-auth-secret-key-change-in-production"
DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES = 60

# System Parameters
PARAM_KEY_JWT_SECRET = "fastapi_v19_auth.jwt_secret_key"
PARAM_KEY_ACCESS_EXPIRE_MIN = "fastapi_v19_auth.access_token_expire_minutes"
PARAM_KEY_CLIENT_ID = "fastapi_v19_auth.client_id"
PARAM_KEY_CLIENT_SECRET = "fastapi_v19_auth.client_secret"

# Rate Limiting
DEFAULT_RATE_LIMIT_MAX = 30  # requests per window
DEFAULT_RATE_LIMIT_WINDOW_SECONDS = 60  # 1 minute window
PARAM_KEY_RATE_LIMIT = "fastapi_v19_auth.rate_limit.max"
PARAM_KEY_RATE_LIMIT_WINDOW = "fastapi_v19_auth.rate_limit.window_seconds"
RATE_LIMIT_KEY_PREFIX = "fastapi_v19_auth_ratelimit"

# Token Types
TOKEN_TYPE_ACCESS = "access"

# Error Messages
ERROR_MSG_INVALID_TOKEN = "Invalid or expired token"
ERROR_MSG_INVALID_CREDENTIALS = "Invalid client credentials"
