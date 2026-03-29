"""Payment creation service for third-party API."""
import logging
from datetime import date
from typing import Any

from odoo import models, api

from ..core.constants import (
    ERROR_MSG_JOURNAL_NOT_FOUND,
    ERROR_MSG_PAYMENT_METHOD_NOT_FOUND,
    ERROR_MSG_ANALYTIC_NOT_FOUND,
)

_logger = logging.getLogger(__name__)


class ThirdPartyPaymentService(models.AbstractModel):
    """Service for creating payments from third-party API requests."""

    _name = 'third.party.payment.service'
    _description = 'Third Party Payment Service'

    def create_payment_from_api(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Create a customer payment from API request data.
        """
        try:
            # Resolve customer
            partner = self._resolve_partner(data['customer'])

            # Resolve Journal
            journal = self._resolve_journal(data['journal_id'])

            # Resolve Payment Method Line
            payment_method_line = self._resolve_payment_method(data['payment_method_id'], journal)

            # Prepare analytic distribution if analytic ID provided
            analytic_distribution = {}
            if data.get('analytic_id'):
                analytic = self._resolve_analytic(data['analytic_id'])
                analytic_distribution[str(analytic.id)] = 100.0

            # Create payment
            payment_vals = {
                'payment_type': 'inbound',  # Receive
                'partner_type': 'customer',
                'partner_id': partner.id,
                'amount': data['amount'],
                'date': data.get('date') or date.today(),
                'memo': data.get('memo') or '',  # Use the payload memo here
                'payment_reference': data.get('memo') or '', 
                'journal_id': journal.id,
                'payment_method_line_id': payment_method_line.id,
            }

            payment = self.env['account.payment'].create(payment_vals)
            
            # In Odoo 19, analytics are on the move lines.
            # We apply it to the counterpart lines of the payment's generated move.
            if analytic_distribution and payment.move_id:
                # Find counterpart lines (receivable/payable)
                counterpart_lines = payment.move_id.line_ids.filtered(
                    lambda l: l.account_id.account_type in ('asset_receivable', 'liability_payable')
                )
                if counterpart_lines:
                    counterpart_lines.write({'analytic_distribution': analytic_distribution})

            # Post the payment if needed
            # payment.action_post() 

            _logger.info(
                "Created payment %s (ID: %d) for partner %s via third-party API",
                payment.name or 'Draft', payment.id, partner.name
            )

            return {
                'success': True,
                'payment_id': payment.id,
                'payment_name': payment.name or 'Draft',
            }

        except ValueError as e:
            _logger.warning("Validation error creating payment: %s", str(e))
            return {
                'success': False,
                'error': str(e),
            }
        except Exception as e:
            _logger.error("Error creating payment: %s", str(e))
            return {
                'success': False,
                'error': f"Failed to create payment: {str(e)}",
            }

    def _resolve_partner(self, customer_data: dict) -> 'res.partner':
        Partner = self.env['res.partner']
        third_party_id = customer_data['id']
        name = customer_data['name']

        partner = Partner.search([('third_party_id', '=', third_party_id)], limit=1)

        if not partner:
            partner = Partner.create({
                'name': name,
                'third_party_id': third_party_id,
                'company_type': 'person',
            })
            _logger.info("Created new partner '%s' with third_party_id=%d", name, third_party_id)
        elif partner.name != name:
            partner.write({'name': name})
            _logger.info("Updated partner name from '%s' to '%s' for ID %d", partner.name, name, third_party_id)

        return partner

    def _resolve_journal(self, third_party_id: int) -> 'account.journal':
        Journal = self.env['account.journal']
        journal = Journal.search([('third_party_id', '=', third_party_id)], limit=1)

        if not journal:
            raise ValueError(ERROR_MSG_JOURNAL_NOT_FOUND.format(third_party_id))

        return journal

    def _resolve_payment_method(self, third_party_id: int, journal: 'account.journal') -> 'account.payment.method.line':
        PaymentMethodGlobal = self.env['payment.method']
        AccountPaymentMethod = self.env['account.payment.method']
        PaymentMethodLine = self.env['account.payment.method.line']

        # 1. Find the Global Payment Method (where the Third Party ID is stored)
        global_method = PaymentMethodGlobal.search([('third_party_id', '=', third_party_id)], limit=1)
        
        if not global_method:
             raise ValueError(ERROR_MSG_PAYMENT_METHOD_NOT_FOUND.format(third_party_id))

        # 2. Find the corresponding Accounting Payment Method by code
        # In Odoo 19, these codes usually match (e.g., 'demo', 'manual', 'stripe')
        account_method = AccountPaymentMethod.search([
            ('code', '=', global_method.code),
            ('payment_type', '=', 'inbound')
        ], limit=1)

        if not account_method:
             # Fallback: some methods might use different names/codes, but usually 'code' is the link
             raise ValueError(f"Technical error: No accounting payment method found for code '{global_method.code}'")

        # 3. Find the specific line for this journal linked to that accounting method
        method_line = PaymentMethodLine.search([
            ('payment_method_id', '=', account_method.id),
            ('journal_id', '=', journal.id)
        ], limit=1)

        if not method_line:
             raise ValueError(f"Validation missing: Payment method '{global_method.name}' (Code: {global_method.code}) is not enabled on journal '{journal.name}'. Please add it to the 'Incoming Payments' tab of the journal.")

        return method_line

    def _resolve_analytic(self, third_party_id: int) -> 'account.analytic.account':
        Analytic = self.env['account.analytic.account']
        analytic = Analytic.search([('third_party_id', '=', third_party_id)], limit=1)

        if not analytic:
            raise ValueError(ERROR_MSG_ANALYTIC_NOT_FOUND.format(third_party_id))

        return analytic
