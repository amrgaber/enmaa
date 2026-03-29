"""Extend product.template with analytic plan field for third-party API."""
from odoo import fields, models


class ProductTemplate(models.Model):
    """Extend product.template with analytic plan reference."""

    _inherit = 'product.template'

    # Analytic Plan - for matching products in API
    analytic_plan_id = fields.Many2one(
        comodel_name='account.analytic.plan',
        string='Analytic Plan',
        help='Analytic Plan associated with this product for API integration',
        tracking=True,
    )

    # Internal Reference for API lookup
    internal_ref = fields.Char(
        string='Internal Reference',
        help='Unique internal reference for product lookup in third-party API',
        index=True,
        tracking=True,
    )
