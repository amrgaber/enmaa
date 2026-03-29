"""Customer Invoice service for third-party API."""

import logging
from datetime import datetime
from typing import Any

from odoo import models

from ..core.constants import (
    SUCCESS_INVOICE_CREATED,
    SUCCESS_CREDIT_NOTE_CREATED,
    ERROR_NO_PARTNER,
    ERROR_FACILITY_TYPE_NOT_FOUND,
    ERROR_JOURNAL_NOT_FOUND,
    ERROR_PRODUCT_NOT_FOUND,
    ERROR_INTERNAL,
    ERROR_INVOICE_NOT_FOUND,
    ERROR_INVOICE_NOT_POSTED,
    ERROR_INVOICE_WRONG_TYPE,
)

_logger = logging.getLogger(__name__)


class ThirdPartyInvoiceService(models.AbstractModel):
    """Service for customer invoice creation from API."""

    _name = "third.party.invoice.service"
    _description = "Third Party Invoice Service"

    def create_customer_invoice(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Create a customer invoice from API request data.

        Args:
            data: Validated request data containing partner, facility type,
                  journal, dates, payout, and lines

        Returns:
            dict with success status and invoice details or error
        """
        try:
            # 1. Resolve partner (priority: debtor_id → customer_id → contact_id)
            partner = self._resolve_partner(data)
            if not partner:
                return {
                    "success": False,
                    "error": ERROR_NO_PARTNER,
                }

            # 2. Resolve facility type (analytic plan by code)
            facility_type = self._resolve_facility_type(data.get("facility_type_code"))
            if not facility_type:
                return {
                    "success": False,
                    "error": ERROR_FACILITY_TYPE_NOT_FOUND.format(
                        data.get("facility_type_code")
                    ),
                }

            # 3. Resolve journal by code
            journal = self._resolve_journal(data.get("journal_code"))
            if not journal:
                return {
                    "success": False,
                    "error": ERROR_JOURNAL_NOT_FOUND.format(data.get("journal_code")),
                }

            # Validate move_type
            valid_move_types = ("out_invoice", "out_refund")
            move_type = data.get("move_type") or "out_invoice"
            if move_type not in valid_move_types:
                return {
                    "success": False,
                    "error": f"Invalid move_type '{move_type}'. Allowed values: {valid_move_types}",
                }

            if journal.type != "sale":
                return {
                    "success": False,
                    "error": f"Journal '{journal.name}' (Code: {data.get('journal_code')}) is not a Sales journal. Invoices must be recorded in a journal of type 'sale'.",
                }

            # 4. Resolve or create payout (analytic account)
            payout = self._resolve_or_create_payout(
                data.get("payout_name"), facility_type, data.get("currency")
            )

            # 5. Resolve currency if provided
            currency = self._resolve_currency(data.get("currency"))

            # 6. Prepare invoice lines
            lines_result = self._prepare_invoice_lines(
                data.get("lines", []), facility_type, payout
            )
            if lines_result.get("error"):
                return {
                    "success": False,
                    "error": lines_result["error"],
                }
            invoice_lines = lines_result["lines"]

            # 7. Parse dates
            invoice_date = self._parse_date(data.get("invoice_date"))
            due_date = self._parse_date(data.get("due_date"))

            # 8. Create invoice
            invoice_vals = {
                "move_type": move_type,
                "partner_id": partner.id,
                "invoice_date": invoice_date,
                "invoice_date_due": due_date,
                "journal_id": journal.id,
                "facility_type_id": facility_type.id,
                "payout_id": payout.id,
                "contract_no": data.get("contract_number"),
                "invoice_reference": data.get("invoice_reference"),
                "e_invoice_number": data.get("e_invoice_number"),
                "invoice_line_ids": invoice_lines,
            }

            # Set currency if provided and different from journal
            if currency and currency.id != journal.currency_id.id:
                invoice_vals["currency_id"] = currency.id

            invoice = self.env["account.move"].create(invoice_vals)

            # Note: We do NOT post the invoice automatically anymore (remains draft)
            _logger.info("Created invoice ID: %d in draft state", invoice.id)

            _logger.info(
                "Created invoice %s (ID: %d) for partner %s via API",
                invoice.name,
                invoice.id,
                partner.name,
            )

            return {
                "success": True,
                "message": SUCCESS_INVOICE_CREATED,
                "invoice_id": invoice.id,
                "invoice_name": invoice.name or None,
                "partner_id": partner.id,
                "partner_name": partner.name or None,
                "payout_id": payout.id,
                "payout_name": payout.name or None,
                "invoice_reference": invoice.invoice_reference or None,
            }

        except Exception as e:
            _logger.error("Error in create_customer_invoice: %s", str(e))
            return {
                "success": False,
                "error": ERROR_INTERNAL.format(str(e)),
            }

    def create_credit_note(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Create a credit note (reversal) for a posted invoice.

        Mimics clicking the Credit Note button, setting reversal date to today,
        and clicking Reverse in the wizard.

        Args:
            data: dict containing 'invoice_id' (int)

        Returns:
            dict with success status and credit note details or error
        """
        try:
            invoice_id = data.get("invoice_id")

            # 1. Find the invoice
            invoice = self.env["account.move"].browse(invoice_id).exists()
            if not invoice:
                return {
                    "success": False,
                    "error": ERROR_INVOICE_NOT_FOUND.format(invoice_id),
                }

            # 2. Validate it is a posted invoice
            if invoice.state != "posted":
                return {
                    "success": False,
                    "error": ERROR_INVOICE_NOT_POSTED.format(invoice_id, invoice.state),
                }

            # 3. Validate it is a customer or vendor invoice
            valid_types = ("out_invoice", "in_invoice")
            if invoice.move_type not in valid_types:
                return {
                    "success": False,
                    "error": ERROR_INVOICE_WRONG_TYPE.format(invoice_id, invoice.move_type),
                }

            # 4. Resolve journal by code
            journal = self._resolve_journal(data.get("journal_code"))
            if not journal:
                return {
                    "success": False,
                    "error": ERROR_JOURNAL_NOT_FOUND.format(data.get("journal_code")),
                }

            # 5. Create the reversal wizard with today's date (equivalent to the UI dialog)
            today = datetime.now().date()
            wizard_vals = {
                "move_ids": [(4, invoice.id)],
                "date": today,
                "journal_id": journal.id,
            }
            if data.get("reason"):
                wizard_vals["reason"] = data["reason"]
            wizard = self.env["account.move.reversal"].create(wizard_vals)

            # 6. Execute the reversal (equivalent to clicking "Reverse")
            result_action = wizard.reverse_moves()

            # 7. Extract the created credit note from the action result
            # Single move → res_id; multiple moves → domain [('id', 'in', [...])]
            credit_note = False
            if isinstance(result_action, dict):
                res_id = result_action.get("res_id")
                if res_id:
                    credit_note = self.env["account.move"].browse(res_id).exists()
                else:
                    domain = result_action.get("domain")
                    if domain:
                        for condition in domain:
                            if isinstance(condition, (list, tuple)) and len(condition) == 3:
                                field, op, val = condition
                                if field == "id" and op == "in" and val:
                                    credit_note = self.env["account.move"].browse(val[0]).exists()
                                    break

            if not credit_note:
                return {
                    "success": False,
                    "error": ERROR_INTERNAL.format("Credit note was created but could not be retrieved"),
                }

            _logger.info(
                "Created credit note %s (ID: %d) for invoice %s (ID: %d) via API",
                credit_note.name,
                credit_note.id,
                invoice.name,
                invoice.id,
            )

            return {
                "success": True,
                "message": SUCCESS_CREDIT_NOTE_CREATED,
                "credit_note_id": credit_note.id,
                "credit_note_name": credit_note.name or None,
                "original_invoice_id": invoice.id,
                "original_invoice_name": invoice.name or None,
                "reversal_date": str(today),
            }

        except Exception as e:
            _logger.error("Error in create_credit_note: %s", str(e))
            return {
                "success": False,
                "error": ERROR_INTERNAL.format(str(e)),
            }

    def _resolve_partner(self, data: dict) -> "res.partner":
        """
        Resolve partner by priority: debtor_id → customer_id → contact_id.
        Supports both integer IDs and string references.

        Returns:
            res.partner record or False
        """
        # Priority 1: debtor_id
        if data.get("debtor_id"):
            partner = self._get_partner_by_id_or_ref(data["debtor_id"])
            if partner:
                return partner

        # Priority 2: customer_id
        if data.get("customer_id"):
            partner = self._get_partner_by_id_or_ref(data["customer_id"])
            if partner:
                return partner

        # Priority 3: contact_id
        if data.get("contact_id"):
            partner = self._get_partner_by_id_or_ref(data["contact_id"])
            if partner:
                return partner

        return False

    def _get_partner_by_id_or_ref(self, val) -> "res.partner":
        """
        Search partner strictly by Odoo ID.
        """
        if not val:
            return False

        Partner = self.env["res.partner"]
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

    def _resolve_facility_type(self, reference: str) -> "account.analytic.plan":
        """
        Find analytic plan by reference.

        Returns:
            account.analytic.plan record or False
        """
        if not reference:
            return False
        return self.env["account.analytic.plan"].search(
            [("reference", "=", reference)], limit=1
        )

    def _resolve_journal(self, reference: str) -> "account.journal":
        """
        Find journal by reference.

        Returns:
            account.journal record or False
        """
        if not reference:
            return False
        return self.env["account.journal"].search(
            [("reference", "=", reference)], limit=1
        )

    def _resolve_currency(self, currency_code: str) -> "res.currency":
        """
        Find or create currency by code.
        Searches with case-insensitive match (including inactive), creates new if not found.
        """
        if not currency_code:
            return False

        Currency = self.env["res.currency"]
        code_upper = currency_code.upper()

        # Search for BOTH active and inactive currencies to avoid unique constraint error
        currency = Currency.with_context(active_test=False).search(
            [("name", "=ilike", code_upper)], limit=1
        )

        if currency:
            # If it was inactive, activate it
            if not currency.active:
                currency.active = True
                _logger.info("Activated existing currency: %s", code_upper)
            return currency

        # Truly not found, so create it
        _logger.info("Currency '%s' not found, creating new via API", code_upper)
        return Currency.create(
            {
                "name": code_upper,
                "symbol": code_upper,
                "active": True,
            }
        )

    def _resolve_or_create_payout(
        self, name: str, facility_type, currency_code: str = None
    ) -> "account.analytic.account":
        """
        Find or create an analytic account for payout.

        Args:
            name: Payout name
            facility_type: account.analytic.plan record
            currency_code: Optional currency code

        Returns:
            account.analytic.account record
        """
        AnalyticAccount = self.env["account.analytic.account"]

        # Search by name
        payout = AnalyticAccount.search([("name", "=", name)], limit=1)
        if payout:
            return payout

        # Create new analytic account
        vals = {
            "name": name,
            "plan_id": facility_type.id,
        }

        # Add currency if provided
        if currency_code:
            currency = self._resolve_currency(currency_code)
            if currency:
                vals["currency_id"] = currency.id

        payout = AnalyticAccount.create(vals)
        _logger.info("Created payout analytic account '%s' (ID: %d)", name, payout.id)
        return payout

    def _prepare_invoice_lines(self, lines_data: list, facility_type, payout) -> dict:
        """
        Prepare invoice line values from API data.

        Args:
            lines_data: List of line data from API request
            facility_type: account.analytic.plan record
            payout: account.analytic.account record

        Returns:
            dict with 'lines' (list of tuples) or 'error' (str)
        """
        Product = self.env["product.product"]
        invoice_lines = []

        for line_data in lines_data:
            internal_ref = (line_data.get("internal_ref") or "").strip()

            # Search by Internal Reference (matching the field on template) and Analytic Plan
            product = Product.search(
                [
                    ("product_tmpl_id.internal_ref", "=", internal_ref),
                    ("product_tmpl_id.analytic_plan_id", "=", facility_type.id),
                ],
                limit=1,
            )

            if not product:
                return {
                    "error": f"Product with internal reference '{internal_ref}' not found for Facility Type '{facility_type.name}'",
                }

            line_vals = {
                "product_id": product.id,
                "name": product.display_name,
                "quantity": line_data.get("quantity", 1.0),
                "price_unit": line_data.get("price", 0.0),
                "tax_ids": [(5, 0, 0)],  # Clear all taxes
                "analytic_distribution": {str(payout.id): 100} if payout else False,
            }

            invoice_lines.append((0, 0, line_vals))

        return {"lines": invoice_lines}

    def _parse_date(self, date_str: str):
        """
        Parse date string to date object.

        Args:
            date_str: Date string in YYYY-MM-DD format

        Returns:
            date object or False
        """
        if not date_str:
            return False
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return False
