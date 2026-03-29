"""Extend account.journal with reference field for third-party API."""
from odoo import fields, models


class AccountJournal(models.Model):
    """Extend account.journal with reference field for API lookup."""

    _inherit = 'account.journal'

    # Reference field for API lookup
    reference = fields.Char(
        string='Reference',
        index=True,
        help='Unique reference for API lookup',
        tracking=True,
    )

    _sql_constraints = [
        ('reference_unique', 'UNIQUE(reference)', 'Journal reference must be unique!'),
    ]
