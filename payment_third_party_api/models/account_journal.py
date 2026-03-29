from odoo import fields, models

class AccountJournal(models.Model):
    _inherit = 'account.journal'

    third_party_id = fields.Integer(
        string='Third Party ID',
        index=True,
        copy=False,
    )
    
    _sql_constraints = [
        ('third_party_id_unique', 'unique(third_party_id)', 'Third Party ID must be unique per journal!')
    ]
