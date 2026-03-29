"""Main controller for Payment Third Party API - FastAPI endpoint registration."""
import logging
from odoo import fields, models
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..routers.payment_router import create_payment_router
from odoo.addons.fastapi_v19_authentication.routers.auth_router import create_auth_router

_logger = logging.getLogger(__name__)


class PaymentThirdPartyEndpoint(models.Model):
    """Extend fastapi.endpoint to register Payment Third Party API."""
    
    _inherit = 'fastapi.endpoint'
    
    # Add new app_type option
    app_type = fields.Selection(
        selection_add=[('payment_third_party', 'Payment Third Party API')],
        ondelete={'payment_third_party': 'cascade'},
    )
    
    def _get_app_wrapper(self):
        """Override to return our custom FastAPI app for payment_third_party."""
        if self.app_type == 'payment_third_party':
            return self._get_payment_third_party_app()
        return super()._get_app_wrapper()
    
    def _get_payment_third_party_app(self):
        """Build and return the FastAPI app for Payment Third Party API."""
        from odoo.addons.fastapi_base_v19.middleware import ASGIMiddleware
        
        app = FastAPI(
            title="Payment Third Party API",
            description="Create payments and authenticate clients",
            version="1.0.0",
        )
        
        # Add CORS middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Create and include routers
        registry = self.env.registry
        uid = self.user_id.id or self.env.uid
        context = dict(self.env.context or {})
        
        # Auth Router (/login) - from shared module
        app.include_router(create_auth_router(registry, uid, context))
        
        # Payment Router (/receive)
        app.include_router(create_payment_router(registry, uid, context))
        
        _logger.info(
            "Initialized Payment Third Party API with Auth at %s",
            self.root_path
        )
        
        return ASGIMiddleware(app)
