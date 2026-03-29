"""Payment service for third-party API."""
import logging
from datetime import datetime, timedelta
from typing import Any

from odoo import models

from ..core.constants import (
    SUCCESS_PAYMENT_CREATED,
    ERROR_NO_PARTNER,
    ERROR_JOURNAL_NOT_FOUND,
    ERROR_CHECK_STATUS_NOT_FOUND,
    ERROR_CHEQUE_TYPE_NOT_FOUND,
    ERROR_CHEQUE_COLLECTION_NOT_FOUND,
    ERROR_PAYOUT_NOT_FOUND,
    ERROR_INTERNAL,
)

_logger = logging.getLogger(__name__)


class ThirdPartyPaymentService(models.AbstractModel):
    """Service for payment creation from API."""

    _name = 'third.party.payment.service'
    _description = 'Third Party Payment Service'

    def create_payment(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Create a payment from API request data.

        Args:
            data: Validated request data containing partner info, cheque details,
                  journal, amount, etc.

        Returns:
            dict with success status and payment details or error
        """
        try:
            # 1. Resolve check name (priority: debtor_id → customer_id → contact_id)
            check_name = self._resolve_check_name(data)

            # 2. Resolve payment partner (by customer_name or customer_id)
            partner = self._resolve_payment_partner(data)
            if not partner:
                return {
                    'success': False,
                    'error': ERROR_NO_PARTNER,
                }

            # 3. Resolve journal by code
            journal = self._resolve_journal(data.get('journal_code'))
            if not journal:
                return {
                    'success': False,
                    'error': ERROR_JOURNAL_NOT_FOUND.format(data.get('journal_code')),
                }

            # 4. Resolve check status by code
            check_status = self._resolve_check_status(data.get('check_status_code'))
            if not check_status:
                return {
                    'success': False,
                    'error': ERROR_CHECK_STATUS_NOT_FOUND.format(data.get('check_status_code')),
                }

            # 5. Resolve cheque type by code
            cheque_type = self._resolve_cheque_type(data.get('cheque_type_code'))
            if not cheque_type:
                return {
                    'success': False,
                    'error': ERROR_CHEQUE_TYPE_NOT_FOUND.format(data.get('cheque_type_code')),
                }

            # 6. Resolve payout (analytic account by name or code)
            payout = self._resolve_or_create_payout(data)
            if not payout:
                payout_id = data.get('payout_name') or data.get('payout_code')
                return {
                    'success': False,
                    'error': ERROR_PAYOUT_NOT_FOUND.format(payout_id),
                }

            # 7. Resolve cheque collection (cheque location) by reference
            cheque_location_ref = data.get('cheque_location_reference')
            cheque_location = False
            if cheque_location_ref:
                cheque_location = self._resolve_cheque_collection(cheque_location_ref)
                if not cheque_location:
                    return {
                        'success': False,
                        'error': ERROR_CHEQUE_COLLECTION_NOT_FOUND.format(cheque_location_ref),
                    }

            # 8. Resolve currency if provided
            currency = self._resolve_currency(data.get('currency'))

            # 9. Parse and Map Dates
            invoice_date_str = data.get('invoice_date')
            due_date_str = data.get('due_date')
            
            # Parse Dates
            parsed_invoice_date = datetime.now().date()
            if invoice_date_str:
                parsed_invoice_date = datetime.strptime(invoice_date_str, '%Y-%m-%d').date()
            
            parsed_due_date = parsed_invoice_date
            if due_date_str:
                parsed_due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()

            # 10. Create payment
            payment_vals = {
                'payment_type': 'inbound',  # Receive
                'partner_type': 'customer',
                'partner_id': partner.id,
                'amount': data.get('amount', 0.0),
                'date': parsed_due_date, # due_date in API -> date in Odoo (Standard Payment Date)
                'journal_id': journal.id,
                'memo': data.get('memo'),
                # Custom fields
                'check_name': check_name,
                'cheque_no': data.get('cheque_number'),
                'bank_cheque': data.get('bank_cheque'),
                'receive_date': parsed_invoice_date, # invoice_date in API -> receive_date in Odoo
                'contract_no': data.get('contract_number'),
                'check_status': check_status.id,
                'cheque_type': cheque_type.id,
                'payout_id': payout.id,
            }

            # Set cheque location if resolved
            if cheque_location:
                payment_vals['cheque_location_id'] = cheque_location.id

            # Set currency if provided
            if currency:
                payment_vals['currency_id'] = currency.id

            # Set default payment method line from journal (Mapping by Reference)
            pm_code = data.get('payment_method_code')
            payment_method_line = None

            # 1. First, search within this specific Journal's inbound lines
            if pm_code:
                payment_method_line = journal.inbound_payment_method_line_ids.filtered(
                    lambda l: l.reference == pm_code
                )
                if payment_method_line:
                    payment_method_line = payment_method_line[0]

            # 2. Fallback to first available inbound method of the journal
            if not payment_method_line and journal.inbound_payment_method_line_ids:
                payment_method_line = journal.inbound_payment_method_line_ids[0]

            if payment_method_line:
                payment_vals['payment_method_line_id'] = payment_method_line.id

            payment = self.env['account.payment'].create(payment_vals)

            # 10. Determine state based on journal
            # If journal code contains 'cover' or 'check', confirm the payment
            should_confirm = self._should_confirm_payment(journal)
            
            if should_confirm:
                payment.action_post()
                _logger.info(
                    "Payment %s posted (confirmed) based on journal %s",
                    payment.name, journal.code
                )

            _logger.info(
                "Created payment %s (ID: %d) for partner %s via API",
                payment.name, payment.id, partner.name
            )

            return {
                'success': True,
                'message': SUCCESS_PAYMENT_CREATED,
                'payment_id': payment.id,
                'payment_name': str(payment.name or 'Draft'),
                'partner_id': partner.id,
                'partner_name': partner.name,
                'check_name': check_name,
                'contract_number': payment.contract_no,
                'bank_cheque': payment.bank_cheque,
                'state': str(payment.state),
            }

        except Exception as e:
            _logger.error("Error in create_payment: %s", str(e))
            return {
                'success': False,
                'error': ERROR_INTERNAL.format(str(e)),
            }

    def update_payment_status(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Update the check status of an existing payment.

        Args:
            data: Validated request data containing:
                - payment_id: Odoo ID of the payment
                - check_status_code: Code of the check status

        Returns:
            dict with success status and update details or error
        """
        try:
            payment_id = data.get('payment_id')
            status_code = data.get('check_status_code')

            # 1. Resolve payment
            payment = self.env['account.payment'].browse(payment_id).exists()
            if not payment:
                return {
                    'success': False,
                    'error': f"Payment with ID {payment_id} not found.",
                }

            # 2. Resolve check status by code
            check_status = self._resolve_check_status(status_code)
            if not check_status:
                return {
                    'success': False,
                    'error': ERROR_CHECK_STATUS_NOT_FOUND.format(status_code),
                }

            # 3. Update payment
            payment.write({'check_status': check_status.id})

            _logger.info(
                "Updated payment %s (ID: %d) check status to '%s' (Code: %s) via API",
                payment.name, payment.id, check_status.name, status_code
            )

            return {
                'success': True,
                'message': "Payment check status updated successfully.",
                'payment_id': payment.id,
                'new_status': check_status.name,
            }

        except Exception as e:
            _logger.error("Error in update_payment_status: %s", str(e))
            return {
                'success': False,
                'error': ERROR_INTERNAL.format(str(e)),
            }

    def _resolve_check_name(self, data: dict) -> str:
        """
        Resolve check name by priority: debtor_id → customer_id → contact_id.
        Supports both IDs and References.

        Returns:
            Partner name or empty string
        """
        # Priority 1: debtor_id
        if data.get('debtor_id'):
            partner = self._get_partner_by_id_or_ref(data['debtor_id'])
            if partner:
                return partner.name

        # Priority 2: customer_id
        if data.get('customer_id'):
            partner = self._get_partner_by_id_or_ref(data['customer_id'])
            if partner:
                return partner.name

        # Priority 3: contact_id
        if data.get('contact_id'):
            partner = self._get_partner_by_id_or_ref(data['contact_id'])
            if partner:
                return partner.name

        return ''

    def _resolve_payment_partner(self, data: dict) -> 'res.partner':
        """
        Resolve payment partner strictly by Odoo ID (customer_id).
        Returns:
            res.partner record or False
        """
        customer_id = data.get('customer_id')
        if customer_id:
            return self._get_partner_by_id_or_ref(customer_id)

        return False

    def _get_partner_by_id_or_ref(self, val) -> 'res.partner':
        """
        Search partner strictly by Odoo ID.
        """
        if not val:
            return False

        Partner = self.env['res.partner']
        partner_id = False
        
        # Determine ID from input
        if isinstance(val, int):
            partner_id = val
        elif isinstance(val, str) and val.isdigit():
            partner_id = int(val)
        
        if partner_id:
            partner = Partner.browse(partner_id).exists()
            return partner

        return False

    def _resolve_journal(self, reference: str) -> 'account.journal':
        """
        Find journal by reference.

        Returns:
            account.journal record or False
        """
        if not reference:
            return False
        return self.env['account.journal'].search(
            [('reference', '=', reference)],
            limit=1
        )

    def _resolve_check_status(self, code: str) -> 'third.party.check.status':
        """
        Find check status by code.

        Returns:
            third.party.check.status record or False
        """
        if not code:
            return False
        return self.env['third.party.check.status'].search(
            [('code', '=', code)],
            limit=1
        )

    def _resolve_cheque_type(self, code: str) -> 'third.party.cheque.type':
        """
        Find cheque type by code.

        Returns:
            third.party.cheque.type record or False
        """
        if not code:
            return False
        return self.env['third.party.cheque.type'].search(
            [('code', '=', code)],
            limit=1
        )

    def _resolve_cheque_collection(self, reference: str) -> 'third.party.cheque.collection':
        """
        Find cheque collection by reference.

        Returns:
            third.party.cheque.collection record or False
        """
        if not reference:
            return False
        return self.env['third.party.cheque.collection'].search(
            [('reference', '=', reference)],
            limit=1
        )

    def _resolve_or_create_payout(self, data: dict) -> 'account.analytic.account':
        """
        Find payout (analytic account) by name.
        If not found and facility_type_code provided, creates new.

        Returns:
            account.analytic.account record or False
        """
        AnalyticAccount = self.env['account.analytic.account']
        name = data.get('payout_name')
        ft_code = data.get('facility_type_code')

        if not name:
            return False

        # 1. Search strictly by Name
        payout = AnalyticAccount.search([('name', '=', name)], limit=1)
        
        # 2. Create if not found
        if not payout:
            # We need a plan (Facility Type) to create an analytic account
            plan = False
            if ft_code:
                plan = self.env['account.analytic.plan'].search([('reference', '=', ft_code)], limit=1)
            
            if plan:
                payout = AnalyticAccount.create({
                    'name': name,
                    'plan_id': plan.id,
                })
                _logger.info("Created payout analytic account '%s' (ID: %d) from Payment API", name, payout.id)

        return payout

    def _resolve_currency(self, currency_code: str) -> 'res.currency':
        """
        Find or create currency by code.
        Searches with case-insensitive match (including inactive), creates new if not found.
        """
        if not currency_code:
            return False
        
        Currency = self.env['res.currency']
        code_upper = currency_code.upper()
        
        # Search for BOTH active and inactive currencies to avoid unique constraint error
        currency = Currency.with_context(active_test=False).search([
            ('name', '=ilike', code_upper)
        ], limit=1)
        
        if currency:
            # If it was inactive, activate it
            if not currency.active:
                currency.active = True
                _logger.info("Activated existing currency: %s", code_upper)
            return currency
        
        # Truly not found, so create it
        _logger.info("Currency '%s' not found, creating new via API", code_upper)
        return Currency.create({
            'name': code_upper,
            'symbol': code_upper,
            'active': True,
        })



    def _should_confirm_payment(self, journal) -> bool:
        """
        Determine if payment should be confirmed based on journal.

        Confirms if journal code/name contains 'cover' or 'check'.
        Stays draft if journal code/name contains 'draft'.

        Returns:
            bool
        """
        journal_code_lower = (journal.code or '').lower()
        journal_name_lower = (journal.name or '').lower()

        # Check for draft indicators
        if 'draft' in journal_code_lower or 'draft' in journal_name_lower:
            return False

        # Check for confirm indicators
        if any(keyword in journal_code_lower or keyword in journal_name_lower
               for keyword in ['cover', 'check', 'cheque']):
            return True

        # Default: don't auto-confirm
        return False
