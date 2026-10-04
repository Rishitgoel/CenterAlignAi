import json
from typing import List, Optional
import aiosqlite
from config import settings
from mock_erp.models import InvoiceCreateRequest, InvoiceRecord, LineItem, VendorRecord


def get_connection():
    # Return the connect coroutine/context manager directly
    return aiosqlite.connect(settings.database_path)


async def init_db():
    async with get_connection() as conn:
        conn.row_factory = aiosqlite.Row
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS vendors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                contact_email TEXT,
                payment_terms TEXT DEFAULT 'Net 30'
            )
            """
        )
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vendor_name TEXT NOT NULL,
                invoice_number TEXT NOT NULL,
                amount REAL NOT NULL,
                currency TEXT DEFAULT 'USD',
                due_date TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                line_items_json TEXT DEFAULT '[]',
                notes TEXT,
                created_at TEXT NOT NULL,
                UNIQUE(vendor_name, invoice_number)
            )
            """
        )

        # Seed initial vendors if empty
        async with conn.execute("SELECT COUNT(*) as count FROM vendors") as cursor:
            row = await cursor.fetchone()
            if row and row["count"] == 0:
                vendors = [
                    ("Acme Corp", "billing@acmecorp.com", "Net 30"),
                    ("Globex Corporation", "accounts@globex.com", "Net 45"),
                    ("Initech", "invoicing@initech.com", "Net 15"),
                    ("Stark Industries", "finance@starkindustries.com", "Net 60"),
                ]
                await conn.executemany(
                    "INSERT INTO vendors (name, contact_email, payment_terms) VALUES (?, ?, ?)",
                    vendors,
                )
        await conn.commit()


def _row_to_invoice(row: aiosqlite.Row) -> InvoiceRecord:
    line_items_raw = json.loads(row["line_items_json"] or "[]")
    line_items = [LineItem(**item) for item in line_items_raw]
    return InvoiceRecord(
        id=row["id"],
        vendor_name=row["vendor_name"],
        invoice_number=row["invoice_number"],
        amount=row["amount"],
        currency=row["currency"],
        due_date=row["due_date"],
        status=row["status"],
        line_items=line_items,
        notes=row["notes"],
        created_at=row["created_at"],
    )


async def create_invoice(req: InvoiceCreateRequest) -> InvoiceRecord:
    from datetime import datetime, timezone

    created_at = datetime.now(timezone.utc).isoformat()
    line_items_json = json.dumps([item.model_dump() for item in (req.line_items or [])])

    async with get_connection() as conn:
        conn.row_factory = aiosqlite.Row
        cursor = await conn.execute(
            """
            INSERT INTO invoices (
                vendor_name, invoice_number, amount, currency, due_date, status, line_items_json, notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                req.vendor_name,
                req.invoice_number,
                req.amount,
                req.currency,
                req.due_date,
                req.status or "pending",
                line_items_json,
                req.notes,
                created_at,
            ),
        )
        invoice_id = cursor.lastrowid
        await conn.commit()

        async with conn.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)) as cur:
            row = await cur.fetchone()
            if not row:
                raise RuntimeError("Failed to retrieve created invoice record.")
            return _row_to_invoice(row)


async def get_invoice(invoice_id: int) -> Optional[InvoiceRecord]:
    async with get_connection() as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)) as cur:
            row = await cur.fetchone()
            if row:
                return _row_to_invoice(row)
            return None


async def get_all_invoices() -> List[InvoiceRecord]:
    async with get_connection() as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute("SELECT * FROM invoices ORDER BY id DESC") as cur:
            rows = await cur.fetchall()
            return [_row_to_invoice(r) for r in rows]


async def search_invoices(
    vendor_name: Optional[str] = None,
    invoice_number: Optional[str] = None,
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
) -> List[InvoiceRecord]:
    query = "SELECT * FROM invoices WHERE 1=1"
    params = []

    if vendor_name:
        query += " AND LOWER(vendor_name) LIKE LOWER(?)"
        params.append(f"%{vendor_name}%")
    if invoice_number:
        query += " AND LOWER(invoice_number) LIKE LOWER(?)"
        params.append(f"%{invoice_number}%")
    if min_amount is not None:
        query += " AND amount >= ?"
        params.append(min_amount)
    if max_amount is not None:
        query += " AND amount <= ?"
        params.append(max_amount)

    query += " ORDER BY id DESC"

    async with get_connection() as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute(query, params) as cur:
            rows = await cur.fetchall()
            return [_row_to_invoice(r) for r in rows]


async def update_invoice_status(invoice_id: int, status: str) -> Optional[InvoiceRecord]:
    async with get_connection() as conn:
        conn.row_factory = aiosqlite.Row
        await conn.execute("UPDATE invoices SET status = ? WHERE id = ?", (status, invoice_id))
        await conn.commit()
        async with conn.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)) as cur:
            row = await cur.fetchone()
            if row:
                return _row_to_invoice(row)
            return None


async def delete_invoice(invoice_id: int) -> bool:
    async with get_connection() as conn:
        cursor = await conn.execute("DELETE FROM invoices WHERE id = ?", (invoice_id,))
        await conn.commit()
        return cursor.rowcount > 0


async def get_vendors() -> List[VendorRecord]:
    async with get_connection() as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute("SELECT * FROM vendors ORDER BY name ASC") as cur:
            rows = await cur.fetchall()
            return [
                VendorRecord(
                    id=r["id"],
                    name=r["name"],
                    contact_email=r["contact_email"],
                    payment_terms=r["payment_terms"],
                )
                for r in rows
            ]


async def clear_database():
    """Clears all invoice records for clean test/benchmark execution."""
    async with get_connection() as conn:
        await conn.execute("DELETE FROM invoices")
        await conn.commit()

