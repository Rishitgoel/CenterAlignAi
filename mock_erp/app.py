from contextlib import asynccontextmanager
from typing import List, Optional
import aiosqlite
from fastapi import FastAPI, HTTPException, Query, status
from mock_erp.database import (
    create_invoice,
    delete_invoice,
    get_all_invoices,
    get_invoice,
    get_vendors,
    init_db,
    search_invoices,
)
from mock_erp.models import InvoiceCreateRequest, InvoiceRecord, VendorRecord


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB and tables on startup
    await init_db()
    yield


app = FastAPI(
    title="CentrAlign Mock Enterprise ERP System",
    description="Internal company API simulating ERP/CRM endpoints for autonomous task execution.",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "Mock ERP", "version": "1.0.0"}


@app.get("/invoices", response_model=List[InvoiceRecord])
async def list_invoices():
    return await get_all_invoices()


@app.get("/invoices/search", response_model=List[InvoiceRecord])
async def search_invoice_endpoint(
    vendor_name: Optional[str] = Query(None, description="Vendor name or substring"),
    invoice_number: Optional[str] = Query(None, description="Invoice reference code"),
    min_amount: Optional[float] = Query(None, description="Minimum amount threshold"),
    max_amount: Optional[float] = Query(None, description="Maximum amount threshold"),
):
    return await search_invoices(
        vendor_name=vendor_name,
        invoice_number=invoice_number,
        min_amount=min_amount,
        max_amount=max_amount,
    )


@app.get("/invoices/{invoice_id}", response_model=InvoiceRecord)
async def get_invoice_endpoint(invoice_id: int):
    record = await get_invoice(invoice_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice with ID {invoice_id} not found",
        )
    return record


@app.post("/invoices", response_model=InvoiceRecord, status_code=status.HTTP_201_CREATED)
async def create_invoice_endpoint(invoice_req: InvoiceCreateRequest):
    try:
        created = await create_invoice(invoice_req)
        return created
    except aiosqlite.IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Duplicate invoice: Invoice '{invoice_req.invoice_number}' for vendor '{invoice_req.vendor_name}' already exists.",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record invoice: {str(e)}",
        )


@app.delete("/invoices/{invoice_id}")
async def delete_invoice_endpoint(invoice_id: int):
    deleted = await delete_invoice(invoice_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice with ID {invoice_id} not found",
        )
    return {"status": "deleted", "invoice_id": invoice_id}


@app.get("/vendors", response_model=List[VendorRecord])
async def list_vendors():
    return await get_vendors()
