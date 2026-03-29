"""Extend account.analytic.plan with code field for third-party API."""
from odoo import fields, models


class AccountAnalyticPlan(models.Model):
    """Extend account.analytic.plan with code field for API lookup."""

    _inherit = ['account.analytic.plan', 'mail.thread', 'mail.activity.mixin']

    # Reference field for API lookup
    reference = fields.Char(
        string='Reference',
        index=True,
        help='Unique reference for API lookup (facility type)',
        tracking=True,
    )

    _sql_constraints = [
        ('reference_unique', 'UNIQUE(reference)', 'Analytic Plan reference must be unique!'),
    ]
