"""Invoice creation service for third-party API."""

import logging
from datetime import date
from typing import Any

from odoo import models, api

from ..core.constants import (
    ERROR_MSG_ACCOUNT_NOT_FOUND,
    ERROR_MSG_ANALYTIC_NOT_FOUND,
)

_logger = logging.getLogger(__name__)


class ThirdPartyInvoiceService(models.AbstractModel):
    """Service for creating invoices from third-party API requests."""

    _name = "third.party.invoice.service"
    _description = "Third Party Invoice Service"

    def create_invoice_from_api(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Create a customer invoice from API request data.

        Args:
            data: Validated request data from Pydantic schema

        Returns:
            dict with success status and invoice details or error
        """
        try:
            # Resolve customer
            partner = self._resolve_partner(data["customer"])

            # Prepare invoice lines
            invoice_lines = []
            for line_data in data["lines"]:
                line_vals = self._prepare_invoice_line(line_data)
                invoice_lines.append((0, 0, line_vals))

            # Create invoice
            invoice_vals = {
                "move_type": "out_invoice",
                "partner_id": partner.id,
                "name": data["customer_invoice"],
                "ref": data["customer_invoice"],
                "e_invoice_number": data.get("e_invoice_number"),
                "invoice_line_ids": invoice_lines,
            }

            # Set invoice date if provided
            if data.get("invoice_date"):
                invoice_vals["invoice_date"] = data["invoice_date"]

            invoice = self.env["account.move"].create(invoice_vals)

            _logger.info(
                "Created invoice %s (ID: %d) for partner %s via third-party API",
                invoice.name,
                invoice.id,
                partner.name,
            )

            return {
                "success": True,
                "invoice_id": invoice.id,
                "invoice_name": invoice.name,
            }

        except ValueError as e:
            _logger.warning("Validation error creating invoice: %s", str(e))
            return {
                "success": False,
                "error": str(e),
            }
        except Exception as e:
            _logger.error("Error creating invoice: %s", str(e))
            return {
                "success": False,
                "error": f"Failed to create invoice: {str(e)}",
            }

    def _resolve_partner(self, customer_data: dict) -> "res.partner":
        """
        Find or create a partner based on third_party_id.

        Args:
            customer_data: Dict with 'id' and 'name' keys

        Returns:
            res.partner record
        """
        Partner = self.env["res.partner"]
        third_party_id = customer_data["id"]
        name = customer_data["name"]

        # Search by third_party_id
        partner = Partner.search([("third_party_id", "=", third_party_id)], limit=1)

        if not partner:
            # Create new partner
            partner = Partner.create(
                {
                    "name": name,
                    "third_party_id": third_party_id,
                    "company_type": "person",
                }
            )
            _logger.info(
                "Created new partner '%s' with third_party_id=%d", name, third_party_id
            )

        return partner

    def _resolve_product(self, product_data: dict) -> "product.product":
        """
        Find or create a product based on third_party_id.

        Args:
            product_data: Dict with 'id' and 'name' keys

        Returns:
            product.product record
        """
        ProductTemplate = self.env["product.template"]
        Product = self.env["product.product"]
        third_party_id = product_data["id"]
        name = product_data["name"]

        # Search template by third_party_id
        template = ProductTemplate.search(
            [("third_party_id", "=", third_party_id)], limit=1
        )

        if not template:
            # Create new product template (type='consu' for goods)
            template = ProductTemplate.create(
                {
                    "name": name,
                    "third_party_id": third_party_id,
                    "type": "consu",  # Consumable/Goods
                }
            )
            _logger.info(
                "Created new product '%s' with third_party_id=%d", name, third_party_id
            )

        # Get the product variant
        product = Product.search([("product_tmpl_id", "=", template.id)], limit=1)
        return product

    def _resolve_account(self, third_party_id: int) -> "account.account":
        """
        Find an account by third_party_id. Raises error if not found.

        Args:
            third_party_id: Third party account ID

        Returns:
            account.account record

        Raises:
            ValueError: If account not found
        """
        Account = self.env["account.account"]
        account = Account.search([("third_party_id", "=", third_party_id)], limit=1)

        if not account:
            raise ValueError(ERROR_MSG_ACCOUNT_NOT_FOUND.format(third_party_id))

        return account

    def _resolve_analytic(self, third_party_id: int) -> "account.analytic.account":
        """
        Find an analytic account by third_party_id. Raises error if not found.

        Args:
            third_party_id: Third party analytic account ID

        Returns:
            account.analytic.account record

        Raises:
            ValueError: If analytic account not found
        """
        Analytic = self.env["account.analytic.account"]
        analytic = Analytic.search([("third_party_id", "=", third_party_id)], limit=1)

        if not analytic:
            raise ValueError(ERROR_MSG_ANALYTIC_NOT_FOUND.format(third_party_id))

        return analytic

    def _prepare_invoice_line(self, line_data: dict) -> dict:
        """
        Prepare invoice line values from API data.

        Args:
            line_data: Line data from API request

        Returns:
            dict of invoice line values
        """
        # Resolve product
        product = self._resolve_product(line_data["product"])

        line_vals = {
            "product_id": product.id,
            "quantity": line_data.get("quantity", 1.0),
        }

        # Set price if provided
        if line_data.get("price") is not None:
            line_vals["price_unit"] = line_data["price"]

        # Resolve account if provided
        if line_data.get("account_id"):
            account = self._resolve_account(line_data["account_id"])
            line_vals["account_id"] = account.id

        # Resolve analytic if provided
        if line_data.get("analytic_id"):
            analytic = self._resolve_analytic(line_data["analytic_id"])
            # In Odoo 17+, analytic distribution is a JSON field
            line_vals["analytic_distribution"] = {str(analytic.id): 100}

        return line_vals
