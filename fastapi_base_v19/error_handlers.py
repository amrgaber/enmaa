from fastapi import status
from odoo.exceptions import AccessDenied, AccessError, MissingError, UserError, ValidationError

def convert_exception_to_status_body(exc: Exception) -> tuple[int, dict]:
    """Maps Odoo exceptions to HTTP status codes."""
    body = {"detail": str(exc)}
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    if isinstance(exc, AccessDenied | AccessError):
        status_code = status.HTTP_403_FORBIDDEN
    elif isinstance(exc, MissingError):
        status_code = status.HTTP_404_NOT_FOUND
        body = {"detail": "Record not found"}
    elif isinstance(exc, UserError):
        status_code = status.HTTP_400_BAD_REQUEST
    elif isinstance(exc, ValidationError):
        status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    
    return status_code, body
