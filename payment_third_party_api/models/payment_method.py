from odoo import fields, models

class PaymentMethod(models.Model):
    _inherit = 'payment.method'

    third_party_id = fields.Integer(
        string='Third Party ID',
        index=True,
        copy=False,
    )
    
    _sql_constraints = [
        ('third_party_id_unique', 'unique(third_party_id)', 'Third Party ID must be unique per payment method!')
    ]
