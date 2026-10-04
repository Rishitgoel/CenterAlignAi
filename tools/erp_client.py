from typing import Any, Dict
import httpx
from config import settings
from tools.base import Tool, ToolResult


class ERPClientTool(Tool):
    name: str = "erp_client"
    description: str = (
        "Interacts with the internal enterprise ERP/CRM API system. "
        "Supported actions: 'create_invoice' (record an invoice), "
        "'get_invoice' (lookup by ID), 'search_invoices' (search by vendor or invoice code), "
        "and 'list_invoices' (fetch recent entries)."
    )
    parameters_schema: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["create_invoice", "get_invoice", "search_invoices", "list_invoices", "update_invoice_status", "delete_invoice"],
                "description": "The specific ERP operation to perform.",
            },
            "invoice_data": {
                "type": "object",
                "description": "Payload required when action is 'create_invoice'. Must contain vendor_name, invoice_number, amount, due_date.",
            },
            "invoice_id": {
                "type": "integer",
                "description": "Invoice ID required for 'get_invoice', 'update_invoice_status', and 'delete_invoice'.",
            },
            "status": {
                "type": "string",
                "description": "Status string when updating invoice (e.g. 'approved', 'verified', 'settled', 'rejected').",
            },
            "vendor_name": {
                "type": "string",
                "description": "Filter vendor name for 'search_invoices'.",
            },
            "invoice_number": {
                "type": "string",
                "description": "Filter invoice number for 'search_invoices'.",
            },
        },
        "required": ["action"],
    }

    def __init__(self, base_url: str = None):
        self.base_url = base_url or settings.erp_base_url

    async def execute(self, params: Dict[str, Any]) -> ToolResult:
        action = params.get("action")
        if not action:
            return ToolResult(success=False, error="Missing required parameter 'action'")

        try:
            async with httpx.AsyncClient(base_url=self.base_url, timeout=10.0) as client:
                if action == "create_invoice":
                    return await self._create_invoice(client, params.get("invoice_data") or {})
                elif action == "get_invoice":
                    return await self._get_invoice(client, params.get("invoice_id"))
                elif action == "search_invoices":
                    return await self._search_invoices(
                        client,
                        vendor_name=params.get("vendor_name"),
                        invoice_number=params.get("invoice_number"),
                    )
                elif action == "list_invoices":
                    return await self._list_invoices(client)
                elif action == "update_invoice_status":
                    return await self._update_invoice_status(
                        client,
                        invoice_id=params.get("invoice_id"),
                        status=params.get("status", "approved"),
                    )
                elif action == "delete_invoice":
                    return await self._delete_invoice(client, params.get("invoice_id"))
                else:
                    return ToolResult(
                        success=False,
                        error=f"Unsupported action: '{action}'. Allowed: create_invoice, get_invoice, search_invoices, list_invoices, update_invoice_status, delete_invoice",
                    )
        except httpx.ConnectError:
            return ToolResult(
                success=False,
                error=f"ConnectionRefused: Unable to connect to Mock ERP at {self.base_url}. Ensure server is running ('python main.py server').",
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"HTTP request failed: {str(e)}",
            )

    async def _create_invoice(self, client: httpx.AsyncClient, data: Dict[str, Any]) -> ToolResult:
        if not data.get("vendor_name") or not data.get("invoice_number"):
            return ToolResult(
                success=False,
                error="create_invoice requires at least 'vendor_name' and 'invoice_number' in invoice_data",
            )

        resp = await client.post("/invoices", json=data)
        if resp.status_code == 201:
            res_data = resp.json()
            return ToolResult(
                success=True,
                data=res_data,
                metadata={"status_code": 201, "invoice_id": res_data.get("id")},
            )
        elif resp.status_code == 409:
            detail = resp.json().get("detail", "Duplicate invoice record detected.")
            return ToolResult(
                success=False,
                error=f"ConflictError (409): {detail}",
                metadata={"status_code": 409, "is_duplicate": True},
            )
        else:
            return ToolResult(
                success=False,
                error=f"ERP API Error ({resp.status_code}): {resp.text}",
                metadata={"status_code": resp.status_code},
            )

    async def _get_invoice(self, client: httpx.AsyncClient, invoice_id: Any) -> ToolResult:
        if invoice_id is None:
            return ToolResult(success=False, error="Missing required parameter 'invoice_id'")

        resp = await client.get(f"/invoices/{invoice_id}")
        if resp.status_code == 200:
            return ToolResult(
                success=True,
                data=resp.json(),
                metadata={"status_code": 200},
            )
        elif resp.status_code == 404:
            return ToolResult(
                success=False,
                error=f"Invoice ID {invoice_id} not found in ERP",
                metadata={"status_code": 404},
            )
        else:
            return ToolResult(
                success=False,
                error=f"ERP API Error ({resp.status_code}): {resp.text}",
            )

    async def _search_invoices(
        self,
        client: httpx.AsyncClient,
        vendor_name: str = None,
        invoice_number: str = None,
    ) -> ToolResult:
        params = {}
        if vendor_name:
            params["vendor_name"] = vendor_name
        if invoice_number:
            params["invoice_number"] = invoice_number

        resp = await client.get("/invoices/search", params=params)
        if resp.status_code == 200:
            records = resp.json()
            return ToolResult(
                success=True,
                data=records,
                metadata={"status_code": 200, "count": len(records)},
            )
        else:
            return ToolResult(
                success=False,
                error=f"Search failed ({resp.status_code}): {resp.text}",
            )

    async def _list_invoices(self, client: httpx.AsyncClient) -> ToolResult:
        resp = await client.get("/invoices")
        if resp.status_code == 200:
            records = resp.json()
            return ToolResult(
                success=True,
                data=records,
                metadata={"status_code": 200, "count": len(records)},
            )
        else:
            return ToolResult(
                success=False,
                error=f"List failed ({resp.status_code}): {resp.text}",
            )

    async def _update_invoice_status(self, client: httpx.AsyncClient, invoice_id: Any, status: str) -> ToolResult:
        if invoice_id is None:
            return ToolResult(success=False, error="Missing required parameter 'invoice_id'")

        resp = await client.patch(f"/invoices/{invoice_id}/status", params={"status": status})
        if resp.status_code == 200:
            return ToolResult(
                success=True,
                data=resp.json(),
                metadata={"status_code": 200, "invoice_id": invoice_id, "new_status": status},
            )
        elif resp.status_code == 404:
            return ToolResult(
                success=False,
                error=f"Invoice ID {invoice_id} not found in ERP",
                metadata={"status_code": 404},
            )
        else:
            return ToolResult(
                success=False,
                error=f"Status update failed ({resp.status_code}): {resp.text}",
            )

    async def _delete_invoice(self, client: httpx.AsyncClient, invoice_id: Any) -> ToolResult:
        if invoice_id is None:
            return ToolResult(success=False, error="Missing required parameter 'invoice_id'")

        resp = await client.delete(f"/invoices/{invoice_id}")
        if resp.status_code == 200:
            return ToolResult(
                success=True,
                data=resp.json(),
                metadata={"status_code": 200, "deleted_id": invoice_id},
            )
        elif resp.status_code == 404:
            return ToolResult(
                success=False,
                error=f"Invoice ID {invoice_id} not found in ERP",
                metadata={"status_code": 404},
            )
        else:
            return ToolResult(
                success=False,
                error=f"Delete failed ({resp.status_code}): {resp.text}",
            )
