from contextvars import ContextVar
from odoo.api import Environment

# Holds the Odoo Environment for the current FastAPI request
odoo_env_ctx: ContextVar[Environment] = ContextVar("odoo_env_ctx")
