"""Payment router for Third Party API."""
from fastapi import APIRouter, Depends
from odoo import api

from ..schemas import CreatePaymentRequest, CreatePaymentResponse
from odoo.addons.fastapi_v19_authentication.core.auth import create_jwt_auth_dependency, create_rate_limit_dependency
from ..core.constants import SERVICE_PAYMENT

def create_payment_router(registry, uid, context):
    router = APIRouter(prefix="/receive", tags=["Payments"])
    
    # Create dependencies
    jwt_auth = create_jwt_auth_dependency(registry, uid, context)
    rate_limit = create_rate_limit_dependency(registry, uid, context)

    @router.post(
        "", 
        response_model=CreatePaymentResponse,
        dependencies=[Depends(jwt_auth), Depends(rate_limit)]
    )
    def receive_payment(request: CreatePaymentRequest):
        """
        Create a new customer payment in Odoo.
        """
        with registry.cursor() as cr:
            env = api.Environment(cr, uid, context)
            service = env[SERVICE_PAYMENT]
            result = service.create_payment_from_api(request.dict())
            return result

    return router
