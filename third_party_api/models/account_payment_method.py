"""Extend account.payment.method.line with reference field for third-party API."""
from odoo import fields, models


class AccountPaymentMethodLine(models.Model):
    """Extend account.payment.method.line with a reference field."""

    _inherit = ['account.payment.method.line', 'mail.thread']

    reference = fields.Char(
        string='Reference',
        index=True,
        help='Reference for third-party API mapping',
        tracking=True,
    )
