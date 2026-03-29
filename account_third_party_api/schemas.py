"""Pydantic schemas for Account Third Party API."""

from pydantic import BaseModel, Field
from datetime import date
from typing import Optional


class CustomerData(BaseModel):
    """Customer data from third-party system."""

    id: int = Field(..., description="Third party customer ID")
    name: str = Field(..., description="Customer name")


class ProductData(BaseModel):
    """Product data from third-party system."""

    id: int = Field(..., description="Third party product ID")
    name: str = Field(..., description="Product name")


class InvoiceLine(BaseModel):
    """Invoice line data."""

    product: ProductData
    account_id: Optional[int] = Field(
        default=None,
        description="Third party account ID (optional, uses Odoo default if not provided)",
    )
    analytic_id: Optional[int] = Field(
        default=None, description="Third party analytic account ID (optional)"
    )
    price: Optional[float] = Field(
        default=None,
        description="Unit price (optional, uses product price if not provided)",
    )
    quantity: float = Field(default=1.0, ge=0, description="Quantity (default: 1)")


class CreateInvoiceRequest(BaseModel):
    """Request body for creating an invoice."""

    customer_invoice: str = Field(
        ..., description="Invoice reference (stored in name and ref)"
    )
    invoice_date: Optional[date] = Field(
        default=None, description="Invoice date (optional, defaults to today)"
    )
    e_invoice_number: Optional[str] = Field(
        default=None, description="Electronic invoice number from third-party system"
    )
    customer: CustomerData
    lines: list[InvoiceLine] = Field(
        ..., min_length=1, description="Invoice lines (at least one required)"
    )


class CreateInvoiceResponse(BaseModel):
    """Response for invoice creation."""

    success: bool
    invoice_id: Optional[int] = None
    invoice_name: Optional[str] = None
    error: Optional[str] = None
