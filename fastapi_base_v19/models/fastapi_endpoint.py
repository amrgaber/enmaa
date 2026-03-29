from odoo import api, fields, models, http
from fastapi import FastAPI, APIRouter
from ..middleware import ASGIMiddleware
import logging

_logger = logging.getLogger(__name__)

class FastapiEndpoint(models.Model):
    _name = 'fastapi.endpoint'
    _description = 'FastAPI Endpoint Configuration'

    name = fields.Char(required=True)
    root_path = fields.Char(required=True, help="E.g. /my_api")
    user_id = fields.Many2one('res.users', string="Run as User", default=lambda self: self.env.user)
    app_type = fields.Selection([('demo', 'Demo API')], required=True, default='demo')

    _sql_constraints = [
        ('root_path_unique', 'unique(root_path)', 'Root path must be unique!')
    ]

    @api.model
    def _get_endpoint(self, path):
        """Finds the endpoint record for a given path."""
        # Search for longest matching root_path
        endpoints = self.search([]).sorted(key=lambda r: len(r.root_path), reverse=True)
        for ep in endpoints:
            if path.startswith(ep.root_path):
                return ep
        return False

    def action_open_docs(self):
        """Opens the FastAPI documentation in a new tab."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f"{self.root_path}/docs",
            'target': 'new',
        }

    def _get_app_wrapper(self):
        """Returns the FastAPI app wrapped in ASGI Middleware."""
        app = FastAPI(title=self.name)
        
        # Here you would normally include routers based on app_type
        if self.app_type == 'demo':
            router = APIRouter()
            @router.get("/hello")
            def hello():
                return {"message": "Hello from Odoo 19 Standalone FastAPI!"}
            app.include_router(router)
            
        return ASGIMiddleware(app)

class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _serve_fallback(cls):
        """
        Intercept 404s and check if the path belongs to a FastAPI endpoint.
        """
        path = http.request.httprequest.path
        endpoint_rec = http.request.env['fastapi.endpoint'].sudo()._get_endpoint(path)
        if endpoint_rec:
            _logger.info("Routing %s to FastAPI endpoint: %s", path, endpoint_rec.name)
            from ..fastapi_dispatcher import FastApiDispatcher
            # Switch to FastAPI dispatcher
            http.request.dispatcher = FastApiDispatcher(http.request)
            # Dispatch manually
            return http.request.dispatcher.dispatch(None, {})
        
        return super()._serve_fallback()
