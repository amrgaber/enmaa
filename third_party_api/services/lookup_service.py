"""Lookup service for syncing relational field data via GET endpoints."""

import logging
from typing import Any

from odoo import models

_logger = logging.getLogger(__name__)


class ThirdPartyLookupService(models.AbstractModel):
    """Service for retrieving lightweight reference data for relational fields."""

    _name = "third.party.lookup.service"
    _description = "Third Party Lookup Service"

    # -------------------------------------------------------------------------
    # Helper
    # -------------------------------------------------------------------------

    def _apply_search_and_pagination(self, model_name, domain, search=None,
                                      search_fields=None, limit=100, offset=0):
        """Apply optional name search and pagination to a domain query.

        Args:
            model_name: Odoo model technical name
            domain: Base search domain
            search: Optional search string for name filtering
            search_fields: Fields to search in (defaults to ['name'])
            limit: Max records to return
            offset: Number of records to skip

        Returns:
            Recordset matching the criteria
        """
        if search:
            search_fields = search_fields or ["name"]
            search_domain = [
                "|" for _ in range(len(search_fields) - 1)
            ] + [(f, "ilike", search) for f in search_fields]
            domain = domain + search_domain

        return self.env[model_name].search(domain, limit=limit, offset=offset)

    # -------------------------------------------------------------------------
    # Journals
    # -------------------------------------------------------------------------

    def get_journals(self, journal_type=None, search=None,
                     limit=100, offset=0) -> list[dict[str, Any]]:
        """Return lightweight journal records."""
        domain = []
        if journal_type:
            domain.append(("type", "=", journal_type))

        records = self._apply_search_and_pagination(
            "account.journal", domain, search,
            search_fields=["name", "code"], limit=limit, offset=offset,
        )
        return [
            {
                "id": r.id,
                "name": r.name,
                "code": r.code,
                "type": r.type,
                "reference": r.reference if hasattr(r, "reference") else None,
            }
            for r in records
        ]

    # -------------------------------------------------------------------------
    # Currencies
    # -------------------------------------------------------------------------

    def get_currencies(self, search=None, limit=100, offset=0) -> list[dict[str, Any]]:
        """Return lightweight currency records."""
        records = self._apply_search_and_pagination(
            "res.currency", [], search, limit=limit, offset=offset,
        )
        return [
            {"id": r.id, "name": r.name, "symbol": r.symbol}
            for r in records
        ]

    # -------------------------------------------------------------------------
    # Partners
    # -------------------------------------------------------------------------

    def get_partners(self, partner_type=None, search=None,
                     limit=100, offset=0) -> list[dict[str, Any]]:
        """Return lightweight partner records.

        Args:
            partner_type: 'customer' or 'supplier' to filter
        """
        domain = []
        if partner_type == "customer":
            domain.append(("customer_rank", ">", 0))
        elif partner_type == "supplier":
            domain.append(("supplier_rank", ">", 0))

        records = self._apply_search_and_pagination(
            "res.partner", domain, search,
            search_fields=["name", "ref"], limit=limit, offset=offset,
        )
        return [
            {
                "id": r.id,
                "name": r.name,
                "ref": r.ref or None,
                "vat": r.vat or None,
                "email": r.email or None,
            }
            for r in records
        ]

    # -------------------------------------------------------------------------
    # Fiscal Positions
    # -------------------------------------------------------------------------

    def get_fiscal_positions(self, search=None,
                              limit=100, offset=0) -> list[dict[str, Any]]:
        """Return lightweight fiscal position records."""
        records = self._apply_search_and_pagination(
            "account.fiscal.position", [], search, limit=limit, offset=offset,
        )
        return [{"id": r.id, "name": r.name} for r in records]

    # -------------------------------------------------------------------------
    # Payment Terms
    # -------------------------------------------------------------------------

    def get_payment_terms(self, search=None,
                           limit=100, offset=0) -> list[dict[str, Any]]:
        """Return lightweight payment term records."""
        records = self._apply_search_and_pagination(
            "account.payment.term", [], search, limit=limit, offset=offset,
        )
        return [{"id": r.id, "name": r.name} for r in records]

    # -------------------------------------------------------------------------
    # Companies
    # -------------------------------------------------------------------------

    def get_companies(self, search=None,
                       limit=100, offset=0) -> list[dict[str, Any]]:
        """Return lightweight company records."""
        records = self._apply_search_and_pagination(
            "res.company", [], search, limit=limit, offset=offset,
        )
        return [{"id": r.id, "name": r.name} for r in records]

    # -------------------------------------------------------------------------
    # Analytic Plans (Facility Types)
    # -------------------------------------------------------------------------

    def get_analytic_plans(self, search=None,
                            limit=100, offset=0) -> list[dict[str, Any]]:
        """Return lightweight analytic plan records."""
        records = self._apply_search_and_pagination(
            "account.analytic.plan", [], search, limit=limit, offset=offset,
        )
        return [
            {
                "id": r.id,
                "name": r.name,
                "reference": r.reference if hasattr(r, "reference") else None,
            }
            for r in records
        ]

    # -------------------------------------------------------------------------
    # Analytic Accounts (Payouts)
    # -------------------------------------------------------------------------

    def get_analytic_accounts(self, plan_id=None, search=None,
                               limit=100, offset=0) -> list[dict[str, Any]]:
        """Return lightweight analytic account records.

        Args:
            plan_id: Optional plan ID to filter by
        """
        domain = []
        if plan_id:
            domain.append(("plan_id", "=", plan_id))

        records = self._apply_search_and_pagination(
            "account.analytic.account", domain, search,
            search_fields=["name", "code"], limit=limit, offset=offset,
        )
        return [
            {
                "id": r.id,
                "name": r.name,
                "code": r.code or None,
                "plan_id": r.plan_id.id if r.plan_id else None,
                "plan_name": r.plan_id.name if r.plan_id else None,
            }
            for r in records
        ]

    # -------------------------------------------------------------------------
    # Chart of Accounts
    # -------------------------------------------------------------------------

    def get_accounts(self, account_type=None, search=None,
                      limit=100, offset=0) -> list[dict[str, Any]]:
        """Return lightweight account records.

        Args:
            account_type: e.g. 'asset_receivable', 'liability_payable'
        """
        domain = []
        if account_type:
            domain.append(("account_type", "=", account_type))

        records = self._apply_search_and_pagination(
            "account.account", domain, search,
            search_fields=["name", "code"], limit=limit, offset=offset,
        )
        return [
            {"id": r.id, "name": r.name, "code": r.code or None}
            for r in records
        ]

    # -------------------------------------------------------------------------
    # Products
    # -------------------------------------------------------------------------

    def get_products(self, analytic_plan_id=None, search=None,
                      limit=100, offset=0) -> list[dict[str, Any]]:
        """Return lightweight product records.

        Args:
            analytic_plan_id: Filter by analytic plan on product template
        """
        domain = []
        if analytic_plan_id:
            domain.append(("product_tmpl_id.analytic_plan_id", "=", analytic_plan_id))

        records = self._apply_search_and_pagination(
            "product.product", domain, search, limit=limit, offset=offset,
        )
        return [
            {
                "id": r.id,
                "name": r.name,
                "default_code": r.default_code or None,
                "internal_ref": r.product_tmpl_id.internal_ref
                if hasattr(r.product_tmpl_id, "internal_ref") else r.default_code or None,
            }
            for r in records
        ]

    # -------------------------------------------------------------------------
    # Units of Measure
    # -------------------------------------------------------------------------

    def get_uom(self, search=None, limit=100, offset=0) -> list[dict[str, Any]]:
        """Return lightweight UoM records."""
        records = self._apply_search_and_pagination(
            "uom.uom", [], search, limit=limit, offset=offset,
        )
        return [{"id": r.id, "name": r.name} for r in records]

    # -------------------------------------------------------------------------
    # Taxes
    # -------------------------------------------------------------------------

    def get_taxes(self, type_tax_use=None, search=None,
                   limit=100, offset=0) -> list[dict[str, Any]]:
        """Return lightweight tax records.

        Args:
            type_tax_use: 'sale' or 'purchase'
        """
        domain = []
        if type_tax_use:
            domain.append(("type_tax_use", "=", type_tax_use))

        records = self._apply_search_and_pagination(
            "account.tax", domain, search, limit=limit, offset=offset,
        )
        return [
            {
                "id": r.id,
                "name": r.name,
                "amount": r.amount,
                "type_tax_use": r.type_tax_use,
            }
            for r in records
        ]

    # -------------------------------------------------------------------------
    # Users
    # -------------------------------------------------------------------------

    def get_users(self, search=None, limit=100, offset=0) -> list[dict[str, Any]]:
        """Return lightweight user records."""
        records = self._apply_search_and_pagination(
            "res.users", [("share", "=", False)], search, limit=limit, offset=offset,
        )
        return [{"id": r.id, "name": r.name} for r in records]
