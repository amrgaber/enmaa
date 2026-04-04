import json

from odoo import fields, models


class WebhookLog(models.Model):
    _name = 'webhook.log'
    _description = 'Webhook Log'
    _order = 'received_at desc'

    name = fields.Char(string='Event', readonly=True)
    source_ip = fields.Char(string='Source IP', readonly=True)
    http_method = fields.Char(string='Method', readonly=True)
    payload = fields.Text(string='JSON Payload', readonly=True)
    received_at = fields.Datetime(
        string='Received At',
        default=fields.Datetime.now,
        readonly=True,
    )
    state = fields.Selection(
        [('success', 'Success'), ('error', 'Error')],
        string='Status',
        default='success',
        readonly=True,
    )
    error_message = fields.Text(string='Error', readonly=True)

    def action_view_formatted_json(self):
        """Pretty-print the JSON payload for easy reading."""
        self.ensure_one()
        try:
            formatted = json.dumps(json.loads(self.payload), indent=2, ensure_ascii=False)
        except (json.JSONDecodeError, TypeError):
            formatted = self.payload
        return {
            'type': 'ir.actions.act_window',
            'name': f'Payload: {self.name}',
            'res_model': 'webhook.log',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }
