import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class CustomerData(BaseModel):
    id: int = Field(..., description="Unique ID for the customer in the third-party system")
    name: str = Field(..., description="Name of the customer")


class CreatePaymentRequest(BaseModel):
    amount: float = Field(..., gt=0, description="Payment amount")
    date: Optional[datetime.date] = Field(None, description="Payment date (YYYY-MM-DD), defaults to today")
    memo: Optional[str] = Field(None, description="Payment memo/reference")
    customer: CustomerData = Field(..., description="Customer information")
    journal_id: int = Field(..., description="Third-party ID of the Odoo Journal")
    payment_method_id: int = Field(..., description="Third-party ID of the Odoo Payment Method Line")
    analytic_id: Optional[int] = Field(None, description="Third-party ID for analytic account")


class CreatePaymentResponse(BaseModel):
    success: bool
    payment_id: Optional[int] = None
    payment_name: Optional[str] = None
    error: Optional[str] = None
