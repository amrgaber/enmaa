"""FastAPI router for partner management endpoints."""
import logging
from fastapi import APIRouter, Depends, status, HTTPException
from odoo import api

from ..schemas import (
    CustomerRequest,
    CustomerResponse,
    DebtorRequest,
    DebtorResponse,
    ContactRequest,
    ContactResponse,
    CustomerInvoiceRequest,
    CustomerInvoiceResponse,
    PaymentRequest,
    PaymentResponse,
    PaymentStatusUpdateRequest,
    PaymentStatusUpdateResponse,
    CreditNoteRequest,
    CreditNoteResponse,
)
from ..core.constants import (
    SERVICE_CUSTOMER,
    SERVICE_DEBTOR,
    SERVICE_CONTACT,
    SERVICE_INVOICE,
    SERVICE_PAYMENT,
)
from odoo.addons.fastapi_v19_authentication.core.auth import (
    create_jwt_auth_dependency,
    create_rate_limit_dependency,
)

_logger = logging.getLogger(__name__)


def create_partner_router(registry, uid, context):
    """
    Create and return the partner management API router.

    Args:
        registry: Odoo registry
        uid: User ID for running operations
        context: Odoo context dict

    Returns:
        FastAPI APIRouter instance with all partner endpoints
    """
    router = APIRouter(
        tags=["Partners"],
    )

    # Create authentication and rate limit dependencies
    jwt_auth = create_jwt_auth_dependency(registry, uid, context)
    rate_limit = create_rate_limit_dependency(registry, uid, context)

    # =========================================================================
    # CUSTOMER ENDPOINT
    # =========================================================================
    @router.post(
        "/customer",
        response_model=CustomerResponse,
        status_code=status.HTTP_200_OK,
        summary="Create or Update Customer",
        description="""
Create or update a customer by reference.

**Logic:**
- Searches for existing customer by `reference`
- If found: updates customer with provided data
- If not found: creates new customer with provided data

**Required Fields:**
- `reference`: Unique identifier for the customer
- `name`: Customer name

**Optional Fields:**
- `taxid`: Tax ID / VAT number
- `city`: City name
- `country`: Country name or ISO code
- `street`: Street address
        """,
        dependencies=[Depends(rate_limit), Depends(jwt_auth)],
    )
    def create_or_update_customer(request: CustomerRequest):
        """Create or update a customer based on reference."""
        try:
            with registry.cursor() as cr:
                env = api.Environment(cr, uid, context)

                service = env[SERVICE_CUSTOMER]
                result = service.create_or_update_customer(request.model_dump())

                if result.get('success'):
                    cr.commit()
                    _logger.info(
                        "Customer %s via API: %s (ID: %s)",
                        result.get('action'),
                        result.get('customer_name'),
                        result.get('customer_id'),
                    )
                else:
                    cr.rollback()
                    _logger.warning(
                        "Customer operation failed: %s",
                        result.get('error')
                    )

                return CustomerResponse(**result)

        except Exception as e:
            _logger.error("Error in customer endpoint: %s", str(e))
            return CustomerResponse(
                success=False,
                error=f"Internal error: {str(e)}"
            )

    # =========================================================================
    # DEBTOR ENDPOINT
    # =========================================================================
    @router.post(
        "/debtor",
        response_model=DebtorResponse,
        status_code=status.HTTP_201_CREATED,
        summary="Create Debtor Contact",
        description="""
Create an invoice contact (debtor) linked to an existing customer.

**Logic:**
- Searches for customer by `reference`
- If found: creates new contact with `type='invoice'` under that customer
- If not found: returns error

**Required Fields:**
- `reference`: Reference of the parent customer
- `name`: Name for the debtor contact

**Optional Fields:**
- `taxid`: Tax ID / VAT number
- `city`: City name
- `country`: Country name or ISO code
- `street`: Street address
        """,
        dependencies=[Depends(rate_limit), Depends(jwt_auth)],
    )
    def create_debtor(request: DebtorRequest):
        """Create a debtor (invoice contact) under an existing customer."""
        try:
            with registry.cursor() as cr:
                env = api.Environment(cr, uid, context)

                service = env[SERVICE_DEBTOR]
                result = service.create_debtor(request.model_dump())

                if result.get('success'):
                    cr.commit()
                    _logger.info(
                        "Debtor created via API: %s (ID: %s) under %s",
                        result.get('debtor_name'),
                        result.get('debtor_id'),
                        result.get('parent_customer_name'),
                    )
                else:
                    cr.rollback()
                    _logger.warning(
                        "Debtor creation failed: %s",
                        result.get('error')
                    )
                    # Return 404 if customer not found
                    if 'not found' in result.get('error', '').lower():
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail=result.get('error')
                        )

                return DebtorResponse(**result)

        except HTTPException:
            raise
        except Exception as e:
            _logger.error("Error in debtor endpoint: %s", str(e))
            return DebtorResponse(
                success=False,
                error=f"Internal error: {str(e)}"
            )

    # =========================================================================
    # CONTACT ENDPOINT
    # =========================================================================
    @router.post(
        "/contact",
        response_model=ContactResponse,
        status_code=status.HTTP_201_CREATED,
        summary="Create Contact",
        description="""
Create a contact with optional company linkage.

**Logic:**
- If `company` is provided: searches for company by Odoo ID
  - If found: creates contact under that company
  - If not found: creates standalone contact
- Creates contact with `type='contact'`

**Required Fields:**
- `reference`: Unique reference identifier for the contact
- `name`: Contact name

**Optional Fields:**
- `company`: Company Odoo ID to search and link
- `city`: City name
- `country`: Country name or ISO code
- `street`: Street address
        """,
        dependencies=[Depends(rate_limit), Depends(jwt_auth)],
    )
    def create_contact(request: ContactRequest):
        """Create a contact with optional company linkage."""
        try:
            with registry.cursor() as cr:
                env = api.Environment(cr, uid, context)

                service = env[SERVICE_CONTACT]
                result = service.create_contact(request.model_dump())

                if result.get('success'):
                    cr.commit()
                    _logger.info(
                        "Contact created via API: %s (ID: %s)%s",
                        result.get('contact_name'),
                        result.get('contact_id'),
                        f" under {result.get('parent_company_name')}"
                        if result.get('parent_company_name') else "",
                    )
                else:
                    cr.rollback()
                    _logger.warning(
                        "Contact creation failed: %s",
                        result.get('error')
                    )

                return ContactResponse(**result)

        except Exception as e:
            _logger.error("Error in contact endpoint: %s", str(e))
            return ContactResponse(
                success=False,
                error=f"Internal error: {str(e)}"
            )

    # =========================================================================
    # CUSTOMER INVOICE ENDPOINT
    # =========================================================================
    @router.post(
        "/invoice",
        response_model=CustomerInvoiceResponse,
        status_code=status.HTTP_201_CREATED,
        summary="Create Customer Invoice",
        description="""
Create a customer invoice with facility type, payout, and product lines.

**Partner Selection Priority:** `debtor_id` → `customer_id` → `contact_id`

**Required Fields:**
- `invoice_reference`: Unique reference identifier for the invoice
- At least one of: `debtor_id`, `customer_id`, `contact_id`
- `facility_type_code`: Code of the analytic plan (Facility Type)
- `journal_code`: Journal code
- `invoice_date`: Invoice date (YYYY-MM-DD)
- `due_date`: Due date (YYYY-MM-DD)
- `payout_name`: Payout name (creates new analytic account if not exists)
- `lines`: List of invoice lines with `product_name` and `price`

**Optional Fields:**
- `contract_number`: Contract number
- `currency`: Currency code (e.g., 'EGP', 'USD')

**Notes:**
- Products are matched by name and must have matching `analytic_plan_id`
- Tax is automatically removed from all lines
- Analytic distribution is set to 100% of the payout account
        """,
        dependencies=[Depends(rate_limit), Depends(jwt_auth)],
    )
    def create_customer_invoice(request: CustomerInvoiceRequest):
        """Create a customer invoice."""
        try:
            with registry.cursor() as cr:
                env = api.Environment(cr, uid, context)

                service = env[SERVICE_INVOICE]
                result = service.create_customer_invoice(request.model_dump())

                if result.get('success'):
                    cr.commit()
                    _logger.info(
                        "Invoice created via API: %s (ID: %s) for %s",
                        result.get('invoice_name'),
                        result.get('invoice_id'),
                        result.get('partner_name'),
                    )
                else:
                    cr.rollback()
                    _logger.warning(
                        "Invoice creation failed: %s",
                        result.get('error')
                    )
                    # Return appropriate error status
                    if 'not found' in result.get('error', '').lower():
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail=result.get('error')
                        )

                return CustomerInvoiceResponse(**result)

        except HTTPException:
            raise
        except Exception as e:
            _logger.error("Error in invoice endpoint: %s", str(e))
            return CustomerInvoiceResponse(
                success=False,
                error=f"Internal error: {str(e)}"
            )

    # =========================================================================
    # PAYMENT ENDPOINT
    # =========================================================================
    @router.post(
        "/payment",
        response_model=PaymentResponse,
        status_code=status.HTTP_201_CREATED,
        summary="Create Payment",
        description="""
Create a payment (receive) with cheque details.

**Check Name Priority:** `debtor_id` → `customer_id` → `contact_id`

**Required Fields:**
- `customer_id`: Customer partner ID or Reference (Required)
- `invoice_date`: Receive date (YYYY-MM-DD)
- `due_date`: Payment date (YYYY-MM-DD)
- `cheque_number`: Cheque number
- `amount`: Payment amount
- `check_status_code`: Check status code
- `payout_code`: Payout analytic account code
- `cheque_type_code`: Cheque type code
- `journal_code`: Journal code

**Optional Fields:**
- `contract_number`: Contract number
- `debtor_id`, `contact_id`: Partner IDs for check name
- `customer_name`: Customer name fallback search
- `memo`: Payment memo/reference
- `currency`: Currency code (e.g., 'EGP', 'USD')

**Date Mapping:**
- `invoice_date` (API) → `receive_date` (Custom, New Field)
- `due_date` (API) → `date` (Odoo Standard Payment Date)
        """,
        dependencies=[Depends(rate_limit), Depends(jwt_auth)],
    )
    def create_payment(request: PaymentRequest):
        """Create a payment."""
        try:
            with registry.cursor() as cr:
                env = api.Environment(cr, uid, context)

                service = env[SERVICE_PAYMENT]
                result = service.create_payment(request.model_dump())

                if result.get('success'):
                    cr.commit()
                    _logger.info(
                        "Payment created via API: %s (ID: %s) for %s - State: %s",
                        result.get('payment_name'),
                        result.get('payment_id'),
                        result.get('partner_name'),
                        result.get('state'),
                    )
                else:
                    cr.rollback()
                    _logger.warning(
                        "Payment creation failed: %s",
                        result.get('error')
                    )
                    # Return appropriate error status
                    if 'not found' in result.get('error', '').lower():
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail=result.get('error')
                        )

                return PaymentResponse(**result)

        except HTTPException:
            raise
        except Exception as e:
            _logger.error("Error in payment endpoint: %s", str(e))
            return PaymentResponse(
                success=False,
                error=f"Internal error: {str(e)}"
            )

    # =========================================================================
    # UPDATE PAYMENT STATUS ENDPOINT
    # =========================================================================
    @router.post(
        "/payment/status-update",
        response_model=PaymentStatusUpdateResponse,
        status_code=status.HTTP_200_OK,
        summary="Update Payment Check Status",
        description="""
Update the check status of an existing payment by searching for the status code.

**Required Fields:**
- `payment_id`: Odoo ID of the payment
- `check_status_code`: Code of the check status to apply
        """,
        dependencies=[Depends(rate_limit), Depends(jwt_auth)],
    )
    def update_payment_status(request: PaymentStatusUpdateRequest):
        """Update payment check status."""
        try:
            with registry.cursor() as cr:
                env = api.Environment(cr, uid, context)

                service = env[SERVICE_PAYMENT]
                result = service.update_payment_status(request.model_dump())

                if result.get('success'):
                    cr.commit()
                    _logger.info(
                        "Payment status updated via API: Payment ID %s -> Status %s",
                        result.get('payment_id'),
                        result.get('new_status'),
                    )
                else:
                    cr.rollback()
                    _logger.warning(
                        "Payment status update failed: %s",
                        result.get('error')
                    )
                    if 'not found' in result.get('error', '').lower():
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail=result.get('error')
                        )

                return PaymentStatusUpdateResponse(**result)

        except HTTPException:
            raise
        except Exception as e:
            _logger.error("Error in status update endpoint: %s", str(e))
            return PaymentStatusUpdateResponse(
                success=False,
                error=f"Internal error: {str(e)}"
            )

    # =========================================================================
    # CREDIT NOTE ENDPOINT
    # =========================================================================
    @router.post(
        "/invoice/credit-note",
        response_model=CreditNoteResponse,
        status_code=status.HTTP_201_CREATED,
        summary="Create Credit Note for Invoice",
        description="""
Create a credit note (reversal) for an existing posted invoice.

**Behavior:**
- Finds the invoice by `invoice_id`
- Validates it is in **posted** state
- Validates it is a **customer or vendor invoice** (out_invoice / in_invoice)
- Creates the credit note wizard with **reversal date = today**
- Executes the reversal (equivalent to clicking "Reverse" in the UI)

**Required Fields:**
- `invoice_id`: Odoo ID of the posted invoice to reverse

**Returns:**
- `credit_note_id`: ID of the created credit note
- `credit_note_name`: Name/reference of the credit note
- `original_invoice_id`: ID of the original invoice
- `original_invoice_name`: Name of the original invoice
- `reversal_date`: The reversal date used (today's date)
        """,
        dependencies=[Depends(rate_limit), Depends(jwt_auth)],
    )
    def create_credit_note(request: CreditNoteRequest):
        """Create a credit note for a posted invoice using today's date."""
        try:
            with registry.cursor() as cr:
                env = api.Environment(cr, uid, context)

                service = env[SERVICE_INVOICE]
                result = service.create_credit_note(request.model_dump())

                if result.get('success'):
                    cr.commit()
                    _logger.info(
                        "Credit note created via API: %s (ID: %s) for invoice ID %s",
                        result.get('credit_note_name'),
                        result.get('credit_note_id'),
                        result.get('original_invoice_id'),
                    )
                else:
                    cr.rollback()
                    _logger.warning(
                        "Credit note creation failed: %s",
                        result.get('error')
                    )
                    error_msg = result.get('error', '')
                    if 'not found' in error_msg.lower():
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail=error_msg
                        )
                    if 'not in posted state' in error_msg.lower() or 'not a customer' in error_msg.lower():
                        raise HTTPException(
                            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail=error_msg
                        )

                return CreditNoteResponse(**result)

        except HTTPException:
            raise
        except Exception as e:
            _logger.error("Error in credit note endpoint: %s", str(e))
            return CreditNoteResponse(
                success=False,
                error=f"Internal error: {str(e)}"
            )

    return router

