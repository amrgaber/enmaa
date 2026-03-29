import a2wsgi
import asyncio
from a2wsgi.asgi_typing import ASGIApp
from a2wsgi.wsgi_typing import Environ, StartResponse
from collections.abc import Iterable

class ASGIMiddleware(a2wsgi.ASGIMiddleware):
    """Wraps FastAPI ASGI app to be compatible with Odoo WSGI."""
    
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    def __call__(self, environ: Environ, start_response: StartResponse) -> Iterable[bytes]:
        # Ensure an event loop exists for this thread
        try:
            asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        return super().__call__(environ, start_response)
