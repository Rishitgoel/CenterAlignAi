from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, Field


class LineItem(BaseModel):
    description: str
    quantity: float = 1.0
    unit_price: float
    total: float


class VendorRecord(BaseModel):
    id: int
    name: str
    contact_email: Optional[str] = None
    payment_terms: str = "Net 30"


class InvoiceRecord(BaseModel):
    id: int
    vendor_name: str
    invoice_number: str
    amount: float
    currency: str = "USD"
    due_date: str
    status: str = "pending"
    line_items: List[LineItem] = Field(default_factory=list)
    notes: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class InvoiceCreateRequest(BaseModel):
    vendor_name: str
    invoice_number: str
    amount: float
    currency: str = "USD"
    due_date: str
    status: Optional[str] = "pending"
    line_items: Optional[List[LineItem]] = Field(default_factory=list)
    notes: Optional[str] = None


class InvoiceResponse(BaseModel):
    success: bool
    invoice: Optional[InvoiceRecord] = None
    message: Optional[str] = None
