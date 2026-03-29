"""Main controller for Third Party API - FastAPI endpoint registration."""
import logging
from odoo import fields, models
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..routers.partner_router import create_partner_router
from odoo.addons.fastapi_v19_authentication.routers.auth_router import create_auth_router

_logger = logging.getLogger(__name__)


class ThirdPartyApiEndpoint(models.Model):
    """Extend fastapi.endpoint to register Third Party API."""

    _inherit = 'fastapi.endpoint'

    # Add new app_type option
    app_type = fields.Selection(
        selection_add=[('third_party_api', 'Third Party API')],
        ondelete={'third_party_api': 'cascade'},
    )

    def _get_app_wrapper(self):
        """Override to return our custom FastAPI app for third_party_api."""
        if self.app_type == 'third_party_api':
            return self._get_third_party_api_app()
        return super()._get_app_wrapper()

    def _get_third_party_api_app(self):
        """Build and return the FastAPI app for Third Party API."""
        from odoo.addons.fastapi_base_v19.middleware import ASGIMiddleware

        app = FastAPI(
            title="Third Party API",
            description="""
## Partner Management API

RESTful API for managing customers, debtors, and contacts from third-party systems.

### Authentication
All endpoints require a valid JWT Bearer token. Obtain a token via the `/login` endpoint.

### Endpoints Overview

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/login` | POST | Authenticate and get access token |
| `/customer` | POST | Create or update customer by reference |
| `/debtor` | POST | Create invoice contact under customer |
| `/contact` | POST | Create contact with optional company |

### Rate Limiting
All endpoints are rate-limited. Default: 30 requests per minute.
            """,
            version="1.0.0",
            docs_url="/docs",
            redoc_url="/redoc",
            openapi_url="/openapi.json",
        )

        # Add CORS middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Create context for routers
        registry = self.env.registry
        uid = self.user_id.id or self.env.uid
        context = dict(self.env.context or {})

        # Auth Router (/login) - from shared authentication module
        app.include_router(create_auth_router(registry, uid, context))

        # Partner Router (/customer, /debtor, /contact)
        app.include_router(create_partner_router(registry, uid, context))

        _logger.info(
            "Initialized Third Party API at %s",
            self.root_path
        )

        return ASGIMiddleware(app)
