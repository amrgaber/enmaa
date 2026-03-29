"""Main controller for Account Third Party API - FastAPI endpoint registration."""
import logging
from odoo import fields, models
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..routers.account_move_router import create_account_move_router
from odoo.addons.fastapi_v19_authentication.routers.auth_router import create_auth_router

_logger = logging.getLogger(__name__)


class AccountThirdPartyEndpoint(models.Model):
    """Extend fastapi.endpoint to register Account Third Party API."""
    
    _inherit = 'fastapi.endpoint'
    
    # Add new app_type option
    app_type = fields.Selection(
        selection_add=[('account_third_party', 'Account Third Party API')],
        ondelete={'account_third_party': 'cascade'},
    )
    
    def _get_app_wrapper(self):
        """Override to return our custom FastAPI app for account_third_party."""
        if self.app_type == 'account_third_party':
            return self._get_account_third_party_app()
        return super()._get_app_wrapper()
    
    def _get_account_third_party_app(self):
        """Build and return the FastAPI app for Account Third Party API."""
        from odoo.addons.fastapi_base_v19.middleware import ASGIMiddleware
        
        app = FastAPI(
            title="Account Third Party API",
            description="Create invoices and authenticate clients",
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
        
        # Invoice Router (/account_move)
        app.include_router(create_account_move_router(registry, uid, context))
        
        _logger.info(
            "Initialized Account Third Party API with Auth at %s",
            self.root_path
        )
        
        return ASGIMiddleware(app)
