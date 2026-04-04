import json
import logging

from odoo import http, SUPERUSER_ID
from odoo.api import Environment
from odoo.http import request, Response

_logger = logging.getLogger(__name__)


class WebhookController(http.Controller):

    @http.route(
        '/api/webhook',
        type='http',
        auth='none',
        methods=['POST'],
        csrf=False,
    )
    def receive_webhook(self, **kwargs):
        try:
            raw = request.httprequest.get_data(as_text=True)
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            _logger.warning("Webhook received invalid JSON")
            return Response(
                json.dumps({'status': 'error', 'message': 'Invalid JSON'}),
                status=400,
                content_type='application/json',
            )

        event = payload.get('event', 'unknown')
        source_ip = request.httprequest.remote_addr

        try:
            db_registry = request.registry
            with db_registry.cursor() as cr:
                env = Environment(cr, SUPERUSER_ID, {})
                env['webhook.log'].create({
                    'name': event,
                    'source_ip': source_ip,
                    'http_method': 'POST',
                    'payload': json.dumps(payload, ensure_ascii=False),
                    'state': 'success',
                })

            _logger.info("Webhook received: event=%s from %s", event, source_ip)
            return Response(
                json.dumps({'status': 'ok', 'event': event}),
                status=200,
                content_type='application/json',
            )

        except Exception as e:
            _logger.error("Webhook processing failed: %s", e)
            return Response(
                json.dumps({'status': 'error', 'message': 'Internal error'}),
                status=500,
                content_type='application/json',
            )
