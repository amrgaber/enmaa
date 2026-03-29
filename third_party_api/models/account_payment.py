"""Extend account.payment with additional fields for third-party API."""

import json
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class AccountPayment(models.Model):
    """Extend account.payment with additional fields for API integration."""

    _inherit = "account.payment"

    # Check Name - derived from debtor/customer/contact
    check_name = fields.Char(
        string="Check Name",
        help="Name on the check (from debtor, customer, or contact)",
        tracking=True,
    )

    # Cheque Number
    cheque_no = fields.Char(
        string="Cheque No.",
        help="Cheque number from third-party system",
        tracking=True,
    )

    # Bank Cheque
    bank_cheque = fields.Char(
        string="Bank Cheque",
        help="Bank cheque identifier for third-party API",
        tracking=True,
    )

    # Check Status - selection field
    check_status = fields.Many2one(
        comodel_name="third.party.check.status",
        string="Check Status",
        help="Status of the check (searched by code in API)",
        tracking=True,
    )

    # Payout Number - reference to analytic account
    payout_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="Payout No.",
        help="Analytic Account for payout tracking",
        tracking=True,
    )

    # Cheque Type - selection field
    cheque_type = fields.Many2one(
        comodel_name="third.party.cheque.type",
        string="Cheque Type",
        help="Type of cheque (searched by code in API)",
        tracking=True,
    )

    # Cheque Location (from cheque collection)
    cheque_location_id = fields.Many2one(
        comodel_name="third.party.cheque.collection",
        string="Cheque Location",
        help="Cheque location from cheque collection (searched by reference in API)",
        tracking=True,
    )

    # Finance Bank
    finance_bank = fields.Char(
        string="Finance Bank",
        help="Finance bank name for third-party API (Sarwa)",
        tracking=True,
    )

    # Contract Number
    contract_no = fields.Char(
        string="Contract No",
        help="Contract number from third-party system",
        tracking=True,
    )

    # Receive Date
    receive_date = fields.Date(
        string="Receive Date",
        help="Date the payment was received",
        tracking=True,
    )

    # Remaining Amount (computed)
    remaining_amount = fields.Monetary(
        string="Remaining Amount",
        currency_field="currency_id",
        compute="_compute_remaining_amount",
        store=True,
        help="Amount minus Amount Signed (amount - amount_signed)",
        tracking=True,
    )

    @api.depends(
        "amount",
        "x_studio_many2many_field_5kv_1jhj5eu82",
        "x_studio_many2many_field_5kv_1jhj5eu82.amount",
    )
    def _compute_remaining_amount(self):
        field_name = "x_studio_many2many_field_5kv_1jhj5eu82"
        has_field = field_name in self._fields
        for payment in self:
            if has_field:
                part_total = sum(payment[field_name].mapped("amount"))
                payment.remaining_amount = payment.amount - part_total
            else:
                payment.remaining_amount = payment.amount

    # Sarwa API Logs
    sarwa_log_ids = fields.One2many(
        comodel_name="third.party.sarwa.log",
        inverse_name="payment_id",
        string="Sarwa API Logs",
    )
    sarwa_log_count = fields.Integer(
        string="Sarwa Logs",
        compute="_compute_sarwa_log_count",
    )

    @api.depends("sarwa_log_ids")
    def _compute_sarwa_log_count(self):
        for payment in self:
            payment.sarwa_log_count = len(payment.sarwa_log_ids)

    # -------------------------------------------------------------------------
    # Sarwa API — called by automation rule on check_status change
    # -------------------------------------------------------------------------

    def action_call_sarwa_change_status(self):
        """Call Sarwa external API to update check status.

        Called by automation rule when check_status field changes.
        Uses cheque_no as odoo_check_code,
        check_status.code as status_id,
        and payment amount as collection_amount (for status 2 and 8).
        """
        for payment in self:
            # Skip if no check_status or no check_status code
            if not payment.check_status or not payment.check_status.code:
                _logger.info(
                    "Sarwa API: Skipping payment %s — missing check_status code",
                    payment.id,
                )
                continue

            # Skip if no payout_id (Requirement: Do not push if payout value doesn't exist)
            if not payment.payout_id:
                _logger.info(
                    "Sarwa API: Skipping payment %s — missing payout_id", payment.id
                )
                continue

            try:
                from ..core.sarwa_api_client import SarwaApiClient

                # Check if Sarwa API is configured
                base_url = (
                    payment.env["ir.config_parameter"]
                    .sudo()
                    .get_param("third_party_api.sarwa_base_url")
                )
                if not base_url:
                    _logger.info(
                        "Sarwa API: Not configured, skipping for payment %s", payment.id
                    )
                    continue

                client = SarwaApiClient(payment.env)

                # Use check_status code directly as string (e.g., 'CK003')
                status_id = payment.check_status.code or ""

                # Determine collection_amount:
                #   If Status Name is 'Part Collection' or 'Collected'
                #   -> send remaining_amount
                #   All other statuses -> send 0
                collection_amount = 0
                status_name_lower = (payment.check_status.name or "").strip().lower()
                if status_name_lower in ("part collection", "collected"):
                    collection_amount = payment.remaining_amount

                request_data = {
                    "odoo_check_code": payment.id,
                    "status_id": status_id,
                    "collection_amount": collection_amount,
                }

                result = client.change_status(
                    odoo_check_code=payment.id,
                    status_id=status_id,
                    collection_amount=collection_amount,
                )

                # Create log record
                is_success = result.get("status") == "SUCCESS"
                payment.env["third.party.sarwa.log"].sudo().create(
                    {
                        "payment_id": payment.id,
                        "cheque_no": payment.cheque_no,
                        "status_sent": payment.check_status.name,
                        "status_code_sent": str(status_id),
                        "collection_amount": collection_amount,
                        "state": "success" if is_success else "error",
                        "request_data": json.dumps(request_data, indent=2),
                        "response_data": json.dumps(result, indent=2, default=str),
                        "response_message": result.get("message", ""),
                    }
                )

                if is_success:
                    _logger.info(
                        "Sarwa API: Payment %s (check %s) status updated to %s",
                        payment.name or payment.id,
                        payment.cheque_no,
                        payment.check_status.name,
                    )
                else:
                    _logger.error(
                        "Sarwa API: Failed for payment %s (check %s) — %s",
                        payment.name or payment.id,
                        payment.cheque_no,
                        result.get("message", "Unknown error"),
                    )

            except Exception as e:
                # Log error to DB too (capture partial data if available)
                log_vals = {
                    "payment_id": payment.id,
                    "cheque_no": payment.cheque_no,
                    "status_sent": payment.check_status.name
                    if payment.check_status
                    else "",
                    "status_code_sent": payment.check_status.code
                    if payment.check_status
                    else "",
                    "state": "error",
                    "response_message": str(e),
                }
                if "request_data" in locals():
                    log_vals["request_data"] = json.dumps(request_data, indent=2)
                if "result" in locals():
                    log_vals["response_data"] = json.dumps(
                        result, indent=2, default=str
                    )

                payment.env["third.party.sarwa.log"].sudo().create(log_vals)
                _logger.error(
                    "Sarwa API: Error for payment %s (check %s): %s",
                    payment.name or payment.id,
                    payment.cheque_no,
                    str(e),
                )

    def action_call_sarwa_change_finance_bank(self):
        """Call Sarwa external API to update finance bank.

        Called by automation rule when finance_bank field changes.
        Uses payment.id as odoo_cheque_id and finance_bank as the bank name.
        """
        for payment in self:
            # Skip if no finance_bank value
            if not payment.finance_bank:
                _logger.info(
                    "Sarwa API: Skipping payment %s — missing finance_bank",
                    payment.id,
                )
                continue

            # Skip if no payout_id
            if not payment.payout_id:
                _logger.info(
                    "Sarwa API: Skipping payment %s — missing payout_id",
                    payment.id,
                )
                continue

            try:
                from ..core.sarwa_api_client import SarwaApiClient

                # Check if Sarwa API is configured
                base_url = (
                    payment.env["ir.config_parameter"]
                    .sudo()
                    .get_param("third_party_api.sarwa_base_url")
                )
                if not base_url:
                    _logger.info(
                        "Sarwa API: Not configured, skipping for payment %s",
                        payment.id,
                    )
                    continue

                client = SarwaApiClient(payment.env)

                request_data = {
                    "odoo_cheque_id": payment.id,
                    "finance_bank": payment.finance_bank,
                }

                result = client.change_finance_bank(
                    odoo_cheque_id=payment.id,
                    finance_bank=payment.finance_bank,
                )

                # Create log record
                is_success = result.get("status") == "SUCCESS"
                payment.env["third.party.sarwa.log"].sudo().create(
                    {
                        "payment_id": payment.id,
                        "cheque_no": payment.cheque_no,
                        "finance_bank": payment.finance_bank,
                        "state": "success" if is_success else "error",
                        "request_data": json.dumps(request_data, indent=2),
                        "response_data": json.dumps(result, indent=2, default=str),
                        "response_message": result.get("message", ""),
                    }
                )

                if is_success:
                    _logger.info(
                        "Sarwa API: Payment %s (check %s) finance bank updated to %s",
                        payment.name or payment.id,
                        payment.cheque_no,
                        payment.finance_bank,
                    )
                else:
                    _logger.error(
                        "Sarwa API: Finance bank update failed for payment %s "
                        "(check %s) — %s",
                        payment.name or payment.id,
                        payment.cheque_no,
                        result.get("message", "Unknown error"),
                    )

            except Exception as e:
                # Log error to DB too
                log_vals = {
                    "payment_id": payment.id,
                    "cheque_no": payment.cheque_no,
                    "finance_bank": payment.finance_bank or "",
                    "state": "error",
                    "response_message": str(e),
                }
                if "request_data" in locals():
                    log_vals["request_data"] = json.dumps(request_data, indent=2)
                if "result" in locals():
                    log_vals["response_data"] = json.dumps(
                        result, indent=2, default=str
                    )

                payment.env["third.party.sarwa.log"].sudo().create(log_vals)
                _logger.error(
                    "Sarwa API: Error updating finance bank for payment %s "
                    "(check %s): %s",
                    payment.name or payment.id,
                    payment.cheque_no,
                    str(e),
                )

    def action_view_sarwa_logs(self):
        """Open Sarwa API logs for this payment (smart button)."""
        self.ensure_one()
        return {
            "name": "Sarwa API Logs",
            "type": "ir.actions.act_window",
            "res_model": "third.party.sarwa.log",
            "view_mode": "list,form",
            "domain": [("payment_id", "=", self.id)],
            "context": {"default_payment_id": self.id},
        }


class ThirdPartyCheckStatus(models.Model):
    """Check status configuration for third-party API."""

    _name = "third.party.check.status"
    _description = "Check Status"
    _inherit = ["mail.thread"]

    name = fields.Char(
        string="Name",
        required=True,
        tracking=True,
    )
    code = fields.Char(
        string="Code",
        required=True,
        index=True,
        help="Unique code for API lookup",
        tracking=True,
    )

    _sql_constraints = [
        ("code_unique", "UNIQUE(code)", "Check Status code must be unique!"),
    ]


class ThirdPartyChequeType(models.Model):
    """Cheque type configuration for third-party API."""

    _name = "third.party.cheque.type"
    _description = "Cheque Type"
    _inherit = ["mail.thread"]

    name = fields.Char(
        string="Name",
        required=True,
        tracking=True,
    )
    code = fields.Char(
        string="Code",
        required=True,
        index=True,
        help="Unique code for API lookup",
        tracking=True,
    )

    _sql_constraints = [
        ("code_unique", "UNIQUE(code)", "Cheque Type code must be unique!"),
    ]


class ThirdPartyChequeCollection(models.Model):
    """Cheque collection configuration for third-party API."""

    _name = "third.party.cheque.collection"
    _description = "Cheque Collection"
    _inherit = ["mail.thread"]

    name = fields.Char(
        string="Name",
        required=True,
        tracking=True,
    )
    reference = fields.Char(
        string="Reference",
        required=True,
        index=True,
        help="Unique reference for API lookup",
        tracking=True,
    )

    _sql_constraints = [
        (
            "reference_unique",
            "UNIQUE(reference)",
            "Cheque Collection reference must be unique!",
        ),
    ]


class ThirdPartySarwaLog(models.Model):
    """Log for Sarwa API calls (check status updates)."""

    _name = "third.party.sarwa.log"
    _description = "Sarwa API Log"
    _inherit = ["mail.thread"]
    _order = "create_date desc"

    payment_id = fields.Many2one(
        comodel_name="account.payment",
        string="Payment",
        required=True,
        ondelete="cascade",
        index=True,
        tracking=True,
    )
    cheque_no = fields.Char(string="Cheque No.", readonly=True, tracking=True)
    status_sent = fields.Char(string="Status Sent", readonly=True, tracking=True)
    status_code_sent = fields.Char(string="Status Code", readonly=True, tracking=True)
    collection_amount = fields.Float(
        string="Collection Amount", readonly=True, tracking=True
    )
    finance_bank = fields.Char(string="Finance Bank", readonly=True, tracking=True)
    state = fields.Selection(
        selection=[("success", "Success"), ("error", "Error")],
        string="Result",
        readonly=True,
        tracking=True,
    )
    request_data = fields.Text(string="Request Data", readonly=True, tracking=True)
    response_data = fields.Text(string="Response Data", readonly=True, tracking=True)
    response_message = fields.Char(
        string="Response Message", readonly=True, tracking=True
    )
