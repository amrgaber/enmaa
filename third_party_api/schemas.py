from pydantic import BaseModel, Field
from typing import Optional, Union, Any, List


# =============================================================================
# CUSTOMER SCHEMAS
# =============================================================================


class CustomerRequest(BaseModel):
    """Request body for customer create/update endpoint.

    Searches by reference:
    - If customer exists: updates with provided data
    - If not exists: creates new customer
    """

    reference: str = Field(
        ..., min_length=1, description="Unique reference identifier for the customer"
    )
    name: str = Field(..., min_length=1, description="Customer name")
    tax_id: Optional[str] = Field(
        default=None, alias="taxid", description="Tax identification number (VAT)"
    )
    city: Optional[str] = Field(default=None, description="City name")
    country: Optional[str] = Field(default=None, description="Country name or code")
    street: Optional[str] = Field(default=None, description="Street address")

    class Config:
        populate_by_name = True


class CustomerResponse(BaseModel):
    """Response for customer create/update endpoint."""

    success: bool
    message: Optional[str] = None
    customer_id: Optional[int] = None
    customer_name: Optional[str] = None
    reference: Optional[str] = None
    action: Optional[str] = Field(default=None, description="'created' or 'updated'")
    error: Optional[str] = None


# =============================================================================
# DEBTOR SCHEMAS
# =============================================================================


class DebtorRequest(BaseModel):
    """Request body for debtor (invoice contact) creation.

    Creates a contact with type='invoice' linked to an existing customer.
    Customer is found by reference.
    """

    reference: str = Field(
        ..., min_length=1, description="Reference of the parent customer (company)"
    )
    name: str = Field(..., min_length=1, description="Name of the debtor contact")
    tax_id: Optional[str] = Field(
        default=None, alias="taxid", description="Tax identification number (VAT)"
    )
    city: Optional[str] = Field(default=None, description="City name")
    country: Optional[str] = Field(default=None, description="Country name or code")
    street: Optional[str] = Field(default=None, description="Street address")

    class Config:
        populate_by_name = True


class DebtorResponse(BaseModel):
    """Response for debtor creation endpoint."""

    success: bool
    message: Optional[str] = None
    debtor_id: Optional[int] = None
    debtor_name: Optional[str] = None
    parent_customer_id: Optional[int] = None
    parent_customer_name: Optional[str] = None
    error: Optional[str] = None


# =============================================================================
# CONTACT SCHEMAS
# =============================================================================


class ContactRequest(BaseModel):
    """Request body for contact creation.

    Creates a contact with type='contact'.
    If company ID/Reference is provided and found, links to that customer.
    Address fields are optional.
    """

    reference: str = Field(
        ..., min_length=1, description="Unique reference identifier for the contact"
    )
    name: str = Field(..., min_length=1, description="Contact name")
    company: Optional[int] = Field(
        default=None, description="Company Odoo ID to search and link (optional)"
    )
    city: Optional[str] = Field(default=None, description="City name")
    country: Optional[str] = Field(default=None, description="Country name or code")
    street: Optional[str] = Field(default=None, description="Street address")


class ContactResponse(BaseModel):
    """Response for contact creation endpoint."""

    success: bool
    message: Optional[str] = None
    contact_id: Optional[int] = None
    contact_name: Optional[str] = None
    reference: Optional[str] = None
    parent_company_id: Optional[int] = None
    parent_company_name: Optional[str] = None
    error: Optional[str] = None


# =============================================================================
# INVOICE SCHEMAS
# =============================================================================


class InvoiceLineRequest(BaseModel):
    """Invoice line data for customer invoice endpoint."""

    internal_ref: str = Field(
        ...,
        description="Product Internal Reference to search (must have matching analytic_plan)",
    )
    price: float = Field(..., ge=0, description="Unit price for this line")
    quantity: float = Field(default=1.0, ge=0, description="Quantity (default: 1)")


class CustomerInvoiceRequest(BaseModel):
    """Request body for customer invoice creation.

    Partner selection priority: debtor_id → customer_id → contact_id
    """

    invoice_reference: str = Field(
        ..., min_length=1, description="Unique reference identifier for the invoice"
    )
    # Partner identification (priority order)
    debtor_id: Optional[Union[int, str]] = Field(
        default=None, description="Debtor partner ID or Reference (highest priority)"
    )
    customer_id: Optional[Union[int, str]] = Field(
        default=None, description="Customer partner ID or Reference (second priority)"
    )
    contact_id: Optional[Union[int, str]] = Field(
        default=None, description="Contact partner ID or Reference (lowest priority)"
    )

    # Facility Type (analytic plan)
    facility_type_code: str = Field(
        ..., description="Code of the analytic plan (Facility Type)"
    )

    # Journal
    journal_code: str = Field(..., description="Journal code")

    # Dates
    invoice_date: str = Field(..., description="Invoice date (YYYY-MM-DD)")
    due_date: str = Field(..., description="Due date (YYYY-MM-DD)")

    # Contract number
    contract_number: Optional[str] = Field(default=None, description="Contract number")

    # Payout (analytic account)
    payout_name: str = Field(
        ..., description="Payout name (creates new analytic account if not exists)"
    )

    # Currency (optional)
    currency: Optional[str] = Field(
        default=None, description="Currency code (e.g., 'EGP', 'USD')"
    )

    # Move type
    move_type: Optional[str] = Field(
        default="out_invoice",
        description="Type of entry: 'out_invoice' (Customer Invoice) or 'out_refund' (Customer Credit Note). Defaults to 'out_invoice'.",
    )

    # E-Invoice Number
    e_invoice_number: Optional[str] = Field(
        default=None, description="Electronic invoice number from third-party system"
    )

    # Invoice lines
    lines: list[InvoiceLineRequest] = Field(
        ..., min_length=1, description="Invoice lines (at least one required)"
    )


class CustomerInvoiceResponse(BaseModel):
    """Response for customer invoice creation endpoint."""

    success: bool
    message: Optional[str] = None
    invoice_id: Optional[int] = None
    invoice_name: Optional[str] = None
    partner_id: Optional[int] = None
    partner_name: Optional[str] = None
    payout_id: Optional[int] = None
    payout_name: Optional[str] = None
    invoice_reference: Optional[str] = None
    error: Optional[str] = None


# =============================================================================
# PAYMENT SCHEMAS
# =============================================================================


class PaymentRequest(BaseModel):
    """Request body for payment creation.

    Partner selection for check_name: debtor_id → customer_id → contact_id
    """

    # Partner identification for check_name (priority order)
    debtor_id: Optional[Union[int, str]] = Field(
        default=None,
        description="Debtor partner ID or Reference for check name (highest priority)",
    )
    customer_id: Union[int, str] = Field(
        ...,
        description="Customer partner ID or Reference (Required, used for check name and as payment partner)",
    )
    contact_id: Optional[Union[int, str]] = Field(
        default=None,
        description="Contact partner ID or Reference for check name (lowest priority)",
    )

    # Contract number
    contract_number: Optional[str] = Field(default=None, description="Contract number")

    # Dates
    invoice_date: str = Field(
        ..., description="Invoice date / Receive date (YYYY-MM-DD)"
    )
    due_date: str = Field(..., description="Due date (YYYY-MM-DD)")

    # Customer (payment partner - fallback name search)
    customer_name: Optional[str] = Field(
        default=None,
        description="Customer name to search as payment partner (fallback)",
    )

    # Memo
    memo: Optional[str] = Field(default=None, description="Payment memo/reference")

    # Cheque number
    cheque_number: Optional[str] = Field(default=None, description="Cheque number")

    # Bank Cheque
    bank_cheque: Optional[str] = Field(
        default=None, description="Bank cheque identifier"
    )

    # Amount
    amount: float = Field(..., gt=0, description="Payment amount")

    # Check status (by code)
    check_status_code: str = Field(..., description="Check status code")

    # Payout (analytic account by name/code)
    payout_name: Optional[str] = Field(
        default=None,
        description="Payout name (searched first, creates if not found if facility_type_code provided)",
    )
    payout_code: Optional[str] = Field(
        default=None, description="Payout analytic account code (fallback search)"
    )

    # Facility Type (required for creating new payout)
    facility_type_code: Optional[str] = Field(
        default=None,
        description="Code of the analytic plan (required if creating new payout)",
    )

    # Cheque type (by code)
    cheque_type_code: str = Field(..., description="Cheque type code")

    # Journal code
    journal_code: str = Field(..., description="Journal code")

    # Currency (optional)
    currency: Optional[str] = Field(
        default=None, description="Currency code (e.g., 'EGP', 'USD')"
    )

    # Payment Method (optional code)
    payment_method_code: Optional[str] = Field(
        default=None, description="Reference code for the payment method on the journal"
    )

    # Cheque Location (by reference in cheque collection)
    cheque_location_reference: Optional[str] = Field(
        default=None,
        description="Reference to search in cheque collection for cheque location name",
    )


class PaymentResponse(BaseModel):
    """Response for payment creation endpoint."""

    success: bool
    message: Optional[str] = None
    payment_id: Optional[int] = None
    payment_name: Optional[str] = None
    partner_id: Optional[int] = None
    partner_name: Optional[str] = None
    check_name: Optional[str] = None
    contract_number: Optional[str] = None
    bank_cheque: Optional[str] = None
    state: Optional[str] = None
    error: Optional[str] = None


class PaymentStatusUpdateRequest(BaseModel):
    """Request body for updating payment check status."""

    payment_id: int = Field(..., description="Odoo ID of the payment to update")
    check_status_code: str = Field(
        ..., description="Check status code to search and apply"
    )


class PaymentStatusUpdateResponse(BaseModel):
    """Response for payment status update endpoint."""

    success: bool
    message: Optional[str] = None
    payment_id: Optional[int] = None
    new_status: Optional[str] = None
    error: Optional[str] = None


# =============================================================================
# CREDIT NOTE SCHEMAS
# =============================================================================


class CreditNoteRequest(BaseModel):
    """Request body for credit note creation from an existing invoice."""

    invoice_id: int = Field(..., description="Odoo ID of the posted invoice to reverse")
    journal_code: str = Field(..., description="Journal code (reference) to use for the credit note")
    reason: Optional[str] = Field(default=None, description="Reason displayed on the credit note")


class CreditNoteResponse(BaseModel):
    """Response for credit note creation endpoint."""

    success: bool
    message: Optional[str] = None
    credit_note_id: Optional[int] = None
    credit_note_name: Optional[str] = None
    original_invoice_id: Optional[int] = None
    original_invoice_name: Optional[str] = None
    reversal_date: Optional[str] = None
    error: Optional[str] = None
