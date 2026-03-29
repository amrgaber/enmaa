"""Extend account.move with additional fields for third-party API."""

from odoo import fields, models


class AccountMove(models.Model):
    """Extend account.move with additional fields for API integration."""

    _inherit = "account.move"

    # Facility Type - reference to analytic plan (searched by code)
    facility_type_id = fields.Many2one(
        comodel_name="account.analytic.plan",
        string="Facility Type",
        help="Analytic Plan linked to this invoice (searched by code in API)",
        tracking=True,
    )

    # Payout Number - reference to analytic account
    payout_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="Payout",
        help="Analytic Account for payout tracking",
        tracking=True,
    )

    # Contract Number
    contract_no = fields.Char(
        string="Contract No",
        help="Contract number from third-party system",
        tracking=True,
    )

    # Invoice Reference
    invoice_reference = fields.Char(
        string="Invoice Reference",
        help="Unique reference for the invoice from third-party system",
        tracking=True,
    )

    # E-Invoice Number
    e_invoice_number = fields.Char(
        string="E-Invoice Number",
        help="Electronic invoice number from third-party system",
        tracking=True,
    )
