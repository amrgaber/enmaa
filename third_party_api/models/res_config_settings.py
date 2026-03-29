"""Res Config Settings extension for Sarwa API configuration."""
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    """Add Sarwa API settings to Accounting configuration."""

    _inherit = 'res.config.settings'

    sarwa_base_url = fields.Char(
        string='Sarwa API Base URL',
        config_parameter='third_party_api.sarwa_base_url',
    )
    sarwa_username = fields.Char(
        string='Sarwa API Username',
        config_parameter='third_party_api.sarwa_username',
    )
    sarwa_password = fields.Char(
        string='Sarwa API Password',
        config_parameter='third_party_api.sarwa_password',
    )
