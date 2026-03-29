from contextlib import contextmanager
from io import BytesIO
from odoo.http import Dispatcher, request
from .context import odoo_env_ctx
from .error_handlers import convert_exception_to_status_body

class FastApiDispatcher(Dispatcher):
    """The Odoo Dispatcher that routes requests to FastAPI."""
    routing_type = "fastapi"

    @classmethod
    def is_compatible_with(cls, request):
        return True

    def dispatch(self, endpoint, args):
        self.request.params = {}
        environ = self._get_environ()
        path = environ["PATH_INFO"]
        
        # Find the configured FastAPI endpoint record
        endpoint_rec = request.env["fastapi.endpoint"].sudo()._get_endpoint(path)
        if not endpoint_rec:
            return self.request.make_response("Not Found", status=404)

        # Correctly set SCRIPT_NAME and PATH_INFO for FastAPI
        root_path = endpoint_rec.root_path
        environ["SCRIPT_NAME"] = environ.get("SCRIPT_NAME", "") + root_path
        environ["PATH_INFO"] = path[len(root_path):]
        if not environ["PATH_INFO"].startswith("/"):
            environ["PATH_INFO"] = "/" + environ["PATH_INFO"]

        app = endpoint_rec._get_app_wrapper()
        uid = endpoint_rec.user_id.id
        
        data = BytesIO()
        self.inner_exception = None

        with self._manage_odoo_env(uid):
            for chunk in app(environ, self._make_response):
                data.write(chunk)
            
            if self.inner_exception:
                raise self.inner_exception
                
            return self.request.make_response(
                data.getvalue(), headers=self.headers, status=self.status
            )

    def handle_error(self, exc):
        status_code, body = convert_exception_to_status_body(exc)
        return self.request.make_json_response(body, status=status_code)

    def _make_response(self, status_mapping, headers_tuple, content):
        self.status = status_mapping[:3]
        self.headers = headers_tuple
        if isinstance(content, tuple) and len(content) == 3 and isinstance(content[1], Exception):
            self.inner_exception = content[1]

    def _get_environ(self):
        try:
            httprequest = self.request.httprequest._HTTPRequest__wrapped
        except AttributeError:
            httprequest = self.request.httprequest
        
        environ = httprequest.environ
        stream = httprequest._get_stream_for_parsing()
        if hasattr(stream, "seekable") and stream.seekable():
            stream.seek(0)
        environ["wsgi.input"] = stream
        return environ

    @contextmanager
    def _manage_odoo_env(self, uid=None):
        env = request.env(user=uid) if uid else request.env
        token = odoo_env_ctx.set(env)
        try:
            yield
            env.flush_all()
        finally:
            odoo_env_ctx.reset(token)
