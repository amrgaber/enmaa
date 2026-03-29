"""FastAPI router for invoice creation endpoint."""
import logging
from fastapi import APIRouter, Depends, status, Request
from odoo import api

from ..schemas import CreateInvoiceRequest, CreateInvoiceResponse
from ..core.constants import SERVICE_INVOICE
from odoo.addons.fastapi_v19_authentication.core.auth import create_jwt_auth_dependency, create_rate_limit_dependency

_logger = logging.getLogger(__name__)


def create_account_move_router(registry, uid, context):
    """
    Create and return the account move API router.
    
    Args:
        registry: Odoo registry
        uid: User ID for running operations
        context: Odoo context dict
    
    Returns:
        FastAPI APIRouter instance
    """
    router = APIRouter(
        tags=["Invoice"],
    )
    
    # Create authentication and rate limit dependencies
    jwt_auth = create_jwt_auth_dependency(registry, uid, context)
    rate_limit = create_rate_limit_dependency(registry, uid, context)
    
    @router.post(
        "/account_move",
        response_model=CreateInvoiceResponse,
        status_code=status.HTTP_201_CREATED,
        summary="Create Customer Invoice",
        description="Create a customer invoice from third-party system data",
        dependencies=[Depends(rate_limit), Depends(jwt_auth)],
    )
    def create_invoice(request: CreateInvoiceRequest):
        """
        Create a customer invoice.
        
        This endpoint:
        - Creates or finds customer by third_party_id
        - Creates or finds products by third_party_id
        - Validates account/analytic exist (no auto-create)
        - Creates the invoice with provided data
        
        Requires Bearer token authentication.
        """
        try:
            with registry.cursor() as cr:
                env = api.Environment(cr, uid, context)
                
                invoice_service = env[SERVICE_INVOICE]
                result = invoice_service.create_invoice_from_api(request.model_dump())
                
                if result.get('success'):
                    cr.commit()
                    _logger.info(
                        "Invoice created via API: %s",
                        result.get('invoice_name')
                    )
                else:
                    cr.rollback()
                    _logger.warning(
                        "Invoice creation failed: %s",
                        result.get('error')
                    )
                
                return result
                
        except Exception as e:
            _logger.error("Error in create_invoice endpoint: %s", str(e))
            return CreateInvoiceResponse(
                success=False,
                error=f"Internal error: {str(e)}"
            )
    
    return router
