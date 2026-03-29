"""Core constants for Payment Third Party API."""

# Service Names
SERVICE_PAYMENT = 'third.party.payment.service'

# Error Messages
ERROR_MSG_JOURNAL_NOT_FOUND = "Missing journal: Journal with third_party_id={} not found in Odoo"
ERROR_MSG_PAYMENT_METHOD_NOT_FOUND = "Validation missing: Payment method with third_party_id={} not found in Odoo"
ERROR_MSG_ANALYTIC_NOT_FOUND = "Validation missing: Analytic account with third_party_id={} not found in Odoo"
