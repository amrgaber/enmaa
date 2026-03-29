from odoo import fields, models


class AccountAccount(models.Model):
    _inherit = 'account.account'

    third_party_id = fields.Integer(
        string='Third Party ID',
        index=True,
        copy=False,
        help='Unique identifier from third-party system'
    )

    _sql_constraints = [
        ('third_party_id_unique', 
         'UNIQUE(third_party_id)', 
         'Third Party ID must be unique!')
    ]
