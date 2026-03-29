from typing import Annotated
from odoo.api import Environment
from fastapi import Depends
from .context import odoo_env_ctx

def odoo_env() -> Environment:
    """FastAPI Dependency to get the Odoo Environment."""
    return odoo_env_ctx.get()

def authenticated_partner(env: Annotated[Environment, Depends(odoo_env)]) -> 'res.partner':
    """Returns the partner associated with the current Odoo user."""
    return env.user.partner_id
