"""Core constants for Third Party API."""

# Service Names
SERVICE_CUSTOMER = 'third.party.customer.service'
SERVICE_DEBTOR = 'third.party.debtor.service'
SERVICE_CONTACT = 'third.party.contact.service'
SERVICE_INVOICE = 'third.party.invoice.service'
SERVICE_PAYMENT = 'third.party.payment.service'

# Contact Types
CONTACT_TYPE_INVOICE = 'invoice'
CONTACT_TYPE_CONTACT = 'contact'

# Error Messages - Partner
ERROR_CUSTOMER_NOT_FOUND = "Customer with reference '{}' not found"
ERROR_COMPANY_NOT_FOUND = "Company with name '{}' not found"
ERROR_MISSING_REFERENCE = "Reference is required for customer lookup"
ERROR_MISSING_NAME = "Name is required"
ERROR_NO_PARTNER = "No valid partner found (provide debtor_id, customer_id, or contact_id)"

# Error Messages - Invoice
ERROR_FACILITY_TYPE_NOT_FOUND = "Facility type (analytic plan) with code '{}' not found"
ERROR_JOURNAL_NOT_FOUND = "Journal with code '{}' not found"
ERROR_PRODUCT_NOT_FOUND = "Product with name '{}' not found"

# Error Messages - Payment
ERROR_CHECK_STATUS_NOT_FOUND = "Check status with code '{}' not found"
ERROR_CHEQUE_TYPE_NOT_FOUND = "Cheque type with code '{}' not found"
ERROR_PAYOUT_NOT_FOUND = "Payout (analytic account) with code '{}' not found"
ERROR_CHEQUE_COLLECTION_NOT_FOUND = "Cheque collection with reference '{}' not found"

# Error Messages - General
ERROR_INTERNAL = "Internal server error: {}"

# Success Messages
SUCCESS_CUSTOMER_CREATED = "Customer created successfully"
SUCCESS_CUSTOMER_UPDATED = "Customer updated successfully"
SUCCESS_DEBTOR_CREATED = "Debtor contact created successfully"
SUCCESS_CONTACT_CREATED = "Contact created successfully"
SUCCESS_INVOICE_CREATED = "Customer invoice created successfully"
SUCCESS_PAYMENT_CREATED = "Payment created successfully"
SUCCESS_CREDIT_NOTE_CREATED = "Credit note created successfully"

# Error Messages - Credit Note
ERROR_INVOICE_NOT_FOUND = "Invoice with ID '{}' not found"
ERROR_INVOICE_NOT_POSTED = "Invoice with ID '{}' is not in posted state (current state: {})"
ERROR_INVOICE_WRONG_TYPE = "Invoice with ID '{}' is not a customer or vendor invoice (type: {})"

# Service Names - Credit Note
SERVICE_CREDIT_NOTE = 'third.party.invoice.service'
