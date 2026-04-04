"""FastAPI router for lookup/sync GET endpoints."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from odoo import api

from ..schemas import (
    LookupResponse,
    JournalItem,
    CurrencyItem,
    PartnerItem,
    FiscalPositionItem,
    PaymentTermItem,
    CompanyItem,
    AnalyticPlanItem,
    AnalyticAccountItem,
    AccountItem,
    ProductItem,
    UomItem,
    TaxItem,
    UserItem,
)
from ..core.constants import SERVICE_LOOKUP
from odoo.addons.fastapi_v19_authentication.core.auth import (
    create_jwt_auth_dependency,
    create_rate_limit_dependency,
)

_logger = logging.getLogger(__name__)


def create_lookup_router(registry, uid, context):
    """Create and return the lookup API router for syncing relational data.

    Args:
        registry: Odoo registry
        uid: User ID for running operations
        context: Odoo context dict

    Returns:
        FastAPI APIRouter with all lookup GET endpoints
    """
    router = APIRouter(
        prefix="/lookup",
        tags=["Lookup / Sync"],
    )

    jwt_auth = create_jwt_auth_dependency(registry, uid, context)
    rate_limit = create_rate_limit_dependency(registry, uid, context)

    # =========================================================================
    # JOURNALS
    # =========================================================================
    @router.get(
        "/journals",
        response_model=LookupResponse,
        status_code=status.HTTP_200_OK,
        summary="List Journals",
        description="""
Return lightweight journal records for sync.

**Optional Filters:**
- `type`: Filter by journal type (`sale`, `purchase`, `bank`, `cash`, `general`)
- `search`: Search by name or code (case-insensitive)
- `limit` / `offset`: Pagination (default: 100 / 0)

**Response fields per item:** `id`, `name`, `code`, `type`, `reference`
        """,
        dependencies=[Depends(rate_limit), Depends(jwt_auth)],
    )
    def list_journals(
        type: Optional[str] = Query(default=None, description="Journal type: sale, purchase, bank, cash, general"),
        search: Optional[str] = Query(default=None, description="Search by name or code"),
        limit: int = Query(default=100, ge=1, le=1000, description="Max records"),
        offset: int = Query(default=0, ge=0, description="Skip records"),
    ):
        try:
            with registry.cursor() as cr:
                env = api.Environment(cr, uid, context)
                service = env[SERVICE_LOOKUP]
                data = service.get_journals(journal_type=type, search=search, limit=limit, offset=offset)
                return LookupResponse(success=True, count=len(data), data=data)
        except Exception as e:
            _logger.error("Error in lookup/journals: %s", str(e))
            return LookupResponse(success=False, error=f"Internal error: {str(e)}")

    # =========================================================================
    # CURRENCIES
    # =========================================================================
    @router.get(
        "/currencies",
        response_model=LookupResponse,
        status_code=status.HTTP_200_OK,
        summary="List Currencies",
        description="""
Return lightweight currency records for sync.

**Optional Filters:**
- `search`: Search by name (case-insensitive)
- `limit` / `offset`: Pagination

**Response fields per item:** `id`, `name`, `symbol`
        """,
        dependencies=[Depends(rate_limit), Depends(jwt_auth)],
    )
    def list_currencies(
        search: Optional[str] = Query(default=None, description="Search by name"),
        limit: int = Query(default=100, ge=1, le=1000),
        offset: int = Query(default=0, ge=0),
    ):
        try:
            with registry.cursor() as cr:
                env = api.Environment(cr, uid, context)
                service = env[SERVICE_LOOKUP]
                data = service.get_currencies(search=search, limit=limit, offset=offset)
                return LookupResponse(success=True, count=len(data), data=data)
        except Exception as e:
            _logger.error("Error in lookup/currencies: %s", str(e))
            return LookupResponse(success=False, error=f"Internal error: {str(e)}")

    # =========================================================================
    # PARTNERS
    # =========================================================================
    @router.get(
        "/partners",
        response_model=LookupResponse,
        status_code=status.HTTP_200_OK,
        summary="List Partners",
        description="""
Return lightweight partner records for sync.

**Optional Filters:**
- `type`: `customer` or `supplier`
- `search`: Search by name or ref (case-insensitive)
- `limit` / `offset`: Pagination

**Response fields per item:** `id`, `name`, `ref`, `vat`, `email`
        """,
        dependencies=[Depends(rate_limit), Depends(jwt_auth)],
    )
    def list_partners(
        type: Optional[str] = Query(default=None, description="Partner type: customer, supplier"),
        search: Optional[str] = Query(default=None, description="Search by name or ref"),
        limit: int = Query(default=100, ge=1, le=1000),
        offset: int = Query(default=0, ge=0),
    ):
        try:
            with registry.cursor() as cr:
                env = api.Environment(cr, uid, context)
                service = env[SERVICE_LOOKUP]
                data = service.get_partners(partner_type=type, search=search, limit=limit, offset=offset)
                return LookupResponse(success=True, count=len(data), data=data)
        except Exception as e:
            _logger.error("Error in lookup/partners: %s", str(e))
            return LookupResponse(success=False, error=f"Internal error: {str(e)}")

    # =========================================================================
    # FISCAL POSITIONS
    # =========================================================================
    @router.get(
        "/fiscal-positions",
        response_model=LookupResponse,
        status_code=status.HTTP_200_OK,
        summary="List Fiscal Positions",
        description="""
Return lightweight fiscal position records for sync.

**Response fields per item:** `id`, `name`
        """,
        dependencies=[Depends(rate_limit), Depends(jwt_auth)],
    )
    def list_fiscal_positions(
        search: Optional[str] = Query(default=None, description="Search by name"),
        limit: int = Query(default=100, ge=1, le=1000),
        offset: int = Query(default=0, ge=0),
    ):
        try:
            with registry.cursor() as cr:
                env = api.Environment(cr, uid, context)
                service = env[SERVICE_LOOKUP]
                data = service.get_fiscal_positions(search=search, limit=limit, offset=offset)
                return LookupResponse(success=True, count=len(data), data=data)
        except Exception as e:
            _logger.error("Error in lookup/fiscal-positions: %s", str(e))
            return LookupResponse(success=False, error=f"Internal error: {str(e)}")

    # =========================================================================
    # PAYMENT TERMS
    # =========================================================================
    @router.get(
        "/payment-terms",
        response_model=LookupResponse,
        status_code=status.HTTP_200_OK,
        summary="List Payment Terms",
        description="""
Return lightweight payment term records for sync.

**Response fields per item:** `id`, `name`
        """,
        dependencies=[Depends(rate_limit), Depends(jwt_auth)],
    )
    def list_payment_terms(
        search: Optional[str] = Query(default=None, description="Search by name"),
        limit: int = Query(default=100, ge=1, le=1000),
        offset: int = Query(default=0, ge=0),
    ):
        try:
            with registry.cursor() as cr:
                env = api.Environment(cr, uid, context)
                service = env[SERVICE_LOOKUP]
                data = service.get_payment_terms(search=search, limit=limit, offset=offset)
                return LookupResponse(success=True, count=len(data), data=data)
        except Exception as e:
            _logger.error("Error in lookup/payment-terms: %s", str(e))
            return LookupResponse(success=False, error=f"Internal error: {str(e)}")

    # =========================================================================
    # COMPANIES
    # =========================================================================
    @router.get(
        "/companies",
        response_model=LookupResponse,
        status_code=status.HTTP_200_OK,
        summary="List Companies",
        description="""
Return lightweight company records for sync.

**Response fields per item:** `id`, `name`
        """,
        dependencies=[Depends(rate_limit), Depends(jwt_auth)],
    )
    def list_companies(
        search: Optional[str] = Query(default=None, description="Search by name"),
        limit: int = Query(default=100, ge=1, le=1000),
        offset: int = Query(default=0, ge=0),
    ):
        try:
            with registry.cursor() as cr:
                env = api.Environment(cr, uid, context)
                service = env[SERVICE_LOOKUP]
                data = service.get_companies(search=search, limit=limit, offset=offset)
                return LookupResponse(success=True, count=len(data), data=data)
        except Exception as e:
            _logger.error("Error in lookup/companies: %s", str(e))
            return LookupResponse(success=False, error=f"Internal error: {str(e)}")

    # =========================================================================
    # ANALYTIC PLANS (Facility Types)
    # =========================================================================
    @router.get(
        "/analytic-plans",
        response_model=LookupResponse,
        status_code=status.HTTP_200_OK,
        summary="List Analytic Plans (Facility Types)",
        description="""
Return lightweight analytic plan records for sync (used as Facility Types).

**Response fields per item:** `id`, `name`, `reference`
        """,
        dependencies=[Depends(rate_limit), Depends(jwt_auth)],
    )
    def list_analytic_plans(
        search: Optional[str] = Query(default=None, description="Search by name"),
        limit: int = Query(default=100, ge=1, le=1000),
        offset: int = Query(default=0, ge=0),
    ):
        try:
            with registry.cursor() as cr:
                env = api.Environment(cr, uid, context)
                service = env[SERVICE_LOOKUP]
                data = service.get_analytic_plans(search=search, limit=limit, offset=offset)
                return LookupResponse(success=True, count=len(data), data=data)
        except Exception as e:
            _logger.error("Error in lookup/analytic-plans: %s", str(e))
            return LookupResponse(success=False, error=f"Internal error: {str(e)}")

    # =========================================================================
    # ANALYTIC ACCOUNTS (Payouts)
    # =========================================================================
    @router.get(
        "/analytic-accounts",
        response_model=LookupResponse,
        status_code=status.HTTP_200_OK,
        summary="List Analytic Accounts (Payouts)",
        description="""
Return lightweight analytic account records for sync (used as Payouts).

**Optional Filters:**
- `plan_id`: Filter by analytic plan ID
- `search`: Search by name or code

**Response fields per item:** `id`, `name`, `code`, `plan_id`, `plan_name`
        """,
        dependencies=[Depends(rate_limit), Depends(jwt_auth)],
    )
    def list_analytic_accounts(
        plan_id: Optional[int] = Query(default=None, description="Filter by analytic plan ID"),
        search: Optional[str] = Query(default=None, description="Search by name or code"),
        limit: int = Query(default=100, ge=1, le=1000),
        offset: int = Query(default=0, ge=0),
    ):
        try:
            with registry.cursor() as cr:
                env = api.Environment(cr, uid, context)
                service = env[SERVICE_LOOKUP]
                data = service.get_analytic_accounts(plan_id=plan_id, search=search, limit=limit, offset=offset)
                return LookupResponse(success=True, count=len(data), data=data)
        except Exception as e:
            _logger.error("Error in lookup/analytic-accounts: %s", str(e))
            return LookupResponse(success=False, error=f"Internal error: {str(e)}")

    # =========================================================================
    # CHART OF ACCOUNTS
    # =========================================================================
    @router.get(
        "/accounts",
        response_model=LookupResponse,
        status_code=status.HTTP_200_OK,
        summary="List Chart of Accounts",
        description="""
Return lightweight account records for sync.

**Optional Filters:**
- `type`: Account type (e.g. `asset_receivable`, `liability_payable`, `expense`, `income`)
- `search`: Search by name or code

**Response fields per item:** `id`, `name`, `code`
        """,
        dependencies=[Depends(rate_limit), Depends(jwt_auth)],
    )
    def list_accounts(
        type: Optional[str] = Query(default=None, description="Account type filter"),
        search: Optional[str] = Query(default=None, description="Search by name or code"),
        limit: int = Query(default=100, ge=1, le=1000),
        offset: int = Query(default=0, ge=0),
    ):
        try:
            with registry.cursor() as cr:
                env = api.Environment(cr, uid, context)
                service = env[SERVICE_LOOKUP]
                data = service.get_accounts(account_type=type, search=search, limit=limit, offset=offset)
                return LookupResponse(success=True, count=len(data), data=data)
        except Exception as e:
            _logger.error("Error in lookup/accounts: %s", str(e))
            return LookupResponse(success=False, error=f"Internal error: {str(e)}")

    # =========================================================================
    # PRODUCTS
    # =========================================================================
    @router.get(
        "/products",
        response_model=LookupResponse,
        status_code=status.HTTP_200_OK,
        summary="List Products",
        description="""
Return lightweight product records for sync.

**Optional Filters:**
- `analytic_plan_id`: Filter by analytic plan on product template
- `search`: Search by name

**Response fields per item:** `id`, `name`, `default_code`, `internal_ref`
        """,
        dependencies=[Depends(rate_limit), Depends(jwt_auth)],
    )
    def list_products(
        analytic_plan_id: Optional[int] = Query(default=None, description="Filter by analytic plan ID"),
        search: Optional[str] = Query(default=None, description="Search by name"),
        limit: int = Query(default=100, ge=1, le=1000),
        offset: int = Query(default=0, ge=0),
    ):
        try:
            with registry.cursor() as cr:
                env = api.Environment(cr, uid, context)
                service = env[SERVICE_LOOKUP]
                data = service.get_products(analytic_plan_id=analytic_plan_id, search=search, limit=limit, offset=offset)
                return LookupResponse(success=True, count=len(data), data=data)
        except Exception as e:
            _logger.error("Error in lookup/products: %s", str(e))
            return LookupResponse(success=False, error=f"Internal error: {str(e)}")

    # =========================================================================
    # UNITS OF MEASURE
    # =========================================================================
    @router.get(
        "/uom",
        response_model=LookupResponse,
        status_code=status.HTTP_200_OK,
        summary="List Units of Measure",
        description="""
Return lightweight UoM records for sync.

**Response fields per item:** `id`, `name`
        """,
        dependencies=[Depends(rate_limit), Depends(jwt_auth)],
    )
    def list_uom(
        search: Optional[str] = Query(default=None, description="Search by name"),
        limit: int = Query(default=100, ge=1, le=1000),
        offset: int = Query(default=0, ge=0),
    ):
        try:
            with registry.cursor() as cr:
                env = api.Environment(cr, uid, context)
                service = env[SERVICE_LOOKUP]
                data = service.get_uom(search=search, limit=limit, offset=offset)
                return LookupResponse(success=True, count=len(data), data=data)
        except Exception as e:
            _logger.error("Error in lookup/uom: %s", str(e))
            return LookupResponse(success=False, error=f"Internal error: {str(e)}")

    # =========================================================================
    # TAXES
    # =========================================================================
    @router.get(
        "/taxes",
        response_model=LookupResponse,
        status_code=status.HTTP_200_OK,
        summary="List Taxes",
        description="""
Return lightweight tax records for sync.

**Optional Filters:**
- `type`: Tax use type (`sale` or `purchase`)
- `search`: Search by name

**Response fields per item:** `id`, `name`, `amount`, `type_tax_use`
        """,
        dependencies=[Depends(rate_limit), Depends(jwt_auth)],
    )
    def list_taxes(
        type: Optional[str] = Query(default=None, description="Tax type: sale, purchase"),
        search: Optional[str] = Query(default=None, description="Search by name"),
        limit: int = Query(default=100, ge=1, le=1000),
        offset: int = Query(default=0, ge=0),
    ):
        try:
            with registry.cursor() as cr:
                env = api.Environment(cr, uid, context)
                service = env[SERVICE_LOOKUP]
                data = service.get_taxes(type_tax_use=type, search=search, limit=limit, offset=offset)
                return LookupResponse(success=True, count=len(data), data=data)
        except Exception as e:
            _logger.error("Error in lookup/taxes: %s", str(e))
            return LookupResponse(success=False, error=f"Internal error: {str(e)}")

    # =========================================================================
    # USERS
    # =========================================================================
    @router.get(
        "/users",
        response_model=LookupResponse,
        status_code=status.HTTP_200_OK,
        summary="List Internal Users",
        description="""
Return lightweight internal user records for sync (excludes portal/public users).

**Response fields per item:** `id`, `name`
        """,
        dependencies=[Depends(rate_limit), Depends(jwt_auth)],
    )
    def list_users(
        search: Optional[str] = Query(default=None, description="Search by name"),
        limit: int = Query(default=100, ge=1, le=1000),
        offset: int = Query(default=0, ge=0),
    ):
        try:
            with registry.cursor() as cr:
                env = api.Environment(cr, uid, context)
                service = env[SERVICE_LOOKUP]
                data = service.get_users(search=search, limit=limit, offset=offset)
                return LookupResponse(success=True, count=len(data), data=data)
        except Exception as e:
            _logger.error("Error in lookup/users: %s", str(e))
            return LookupResponse(success=False, error=f"Internal error: {str(e)}")

    return router
