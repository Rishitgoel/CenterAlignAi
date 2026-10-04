import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any, Dict, List, Optional
import uuid
import aiosqlite
from fastapi import FastAPI, File, HTTPException, Query, Request, Response, UploadFile, status
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from mock_erp.database import (
    create_invoice,
    delete_invoice,
    get_all_invoices,
    get_invoice,
    get_vendors,
    init_db,
    search_invoices,
    update_invoice_status,
)
from pydantic import BaseModel
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
    docs_url=None,
    redoc_url=None,
)

static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    response = get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="CentrAlign ERP — API Documentation",
        swagger_favicon_url="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>❖</text></svg>",
    )
    content = response.body.decode("utf-8")
    custom_links = """
    <link rel="stylesheet" href="/static/theme.css">
    <link rel="stylesheet" href="/static/swagger-theme.css">
    </head>
    """
    content = content.replace("</head>", custom_links)
    return HTMLResponse(content=content)


@app.get("/", include_in_schema=False)
async def root(request: Request):
    accept = request.headers.get("accept", "")
    if "text/html" not in accept and "application/json" in accept:
        return JSONResponse({
            "service": "CentrAlign Mock Enterprise ERP System",
            "status": "online",
            "docs": "/docs",
            "endpoints": {
                "health": "/health",
                "invoices": "/invoices",
                "search_invoices": "/invoices/search",
                "vendors": "/vendors",
                "portal": "/portal",
            },
        })

    portal_file = Path(__file__).parent / "static" / "portal.html"
    if portal_file.exists():
        return HTMLResponse(content=portal_file.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>Portal not found</h1>", status_code=404)


@app.get("/portal", response_class=HTMLResponse, include_in_schema=False)
async def portal_page():
    portal_file = Path(__file__).parent / "static" / "portal.html"
    if portal_file.exists():
        return HTMLResponse(content=portal_file.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>Portal not found</h1>", status_code=404)


@app.get("/api/demo/sample-pdf", include_in_schema=False)
async def download_sample_pdf_endpoint():
    pdf_path = Path(__file__).parent.parent / "demo" / "invoices" / "invoice_cyberdyne_005.pdf"
    if not pdf_path.exists():
        pdf_path = Path("demo/invoices/invoice_cyberdyne_005.pdf")
    if pdf_path.exists():
        return FileResponse(
            path=str(pdf_path),
            filename="invoice_cyberdyne_005.pdf",
            media_type="application/pdf",
        )
    raise HTTPException(status_code=404, detail="Sample invoice PDF not found")


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


class InvoiceStatusUpdateRequest(BaseModel):
    status: str


@app.patch("/invoices/{invoice_id}/status", response_model=InvoiceRecord)
async def update_invoice_status_endpoint(invoice_id: int, req: InvoiceStatusUpdateRequest):
    updated = await update_invoice_status(invoice_id, req.status)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice with ID {invoice_id} not found",
        )
    return updated


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


# ============================================================================
# IN-APP AI WORKER DISPATCH & REAL-TIME EVENT STREAMING ENGINE
# ============================================================================

class TaskExecutionState:
    def __init__(self, task_id: str, task: str, file_path: Optional[str] = None):
        self.task_id = task_id
        self.task = task
        self.file_path = file_path
        self.status = "STARTED"  # STARTED, RUNNING, PENDING_APPROVAL, PENDING_INPUT, COMPLETED, FAILED
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.events: List[Dict[str, Any]] = []
        self.event_queue: asyncio.Queue = asyncio.Queue()
        self.approval_event: asyncio.Event = asyncio.Event()
        self.approval_decision: Optional[bool] = None
        self.input_event: asyncio.Event = asyncio.Event()
        self.input_data: Optional[Dict[str, Any]] = None
        self.result_log: Optional[Dict[str, Any]] = None

    async def add_event(self, event: Dict[str, Any]):
        self.events.append(event)
        await self.event_queue.put(event)


active_tasks: Dict[str, TaskExecutionState] = {}


async def run_agent_task(task_state: TaskExecutionState):
    from agent.core import Agent
    from agent.models import AgentState, HumanEscalation
    from agent.memory import WorkingMemory

    task_state.status = "RUNNING"

    async def on_event_handler(event: Dict[str, Any]):
        await task_state.add_event(event)
        ev_type = event.get("type")
        if ev_type == "ESCALATION_TRIGGERED":
            task_state.status = "PENDING_APPROVAL"
        elif ev_type == "INPUT_REQUIRED":
            task_state.status = "PENDING_INPUT"
        elif ev_type == "TASK_COMPLETED":
            task_state.status = "COMPLETED"
        elif ev_type == "TASK_FAILED":
            task_state.status = "FAILED"

    async def escalation_handler(escalation: HumanEscalation, memory: WorkingMemory) -> bool:
        task_state.status = "PENDING_APPROVAL"
        task_state.approval_event.clear()
        await task_state.approval_event.wait()
        approved = bool(task_state.approval_decision)
        task_state.status = "RUNNING"
        return approved

    async def input_handler(data: Dict[str, Any], memory: WorkingMemory) -> Dict[str, Any]:
        task_state.status = "PENDING_INPUT"
        task_state.input_event.clear()
        await task_state.input_event.wait()
        res = task_state.input_data or {}
        task_state.status = "RUNNING"
        return res

    # Pre-check: If user explicitly demanded adding a PDF without specifying a file path,
    # trigger the interactive file upload intake event before agent planning.
    task_lower = task_state.task.lower()
    is_pdf_intake_demand = any(w in task_lower for w in ["add this pdf", "ingest custom pdf", "upload pdf", "add pdf", "process this pdf", "ingest pdf"])
    has_existing_path = "demo/invoices/" in task_lower or ".json" in task_lower or ".pdf" in task_lower or ".eml" in task_lower

    if is_pdf_intake_demand and not has_existing_path and not task_state.file_path:
        task_state.status = "PENDING_INPUT"
        await task_state.add_event({
            "type": "INPUT_REQUIRED",
            "task_id": task_state.task_id,
            "input_type": "file_upload",
            "prompt": "Please attach or drop the PDF invoice you would like CentrAlign AI to ingest and record.",
            "allowed_extensions": [".pdf", ".png", ".jpg", ".jpeg", ".json"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        task_state.input_event.clear()
        await task_state.input_event.wait()
        provided = task_state.input_data or {}
        uploaded_path = provided.get("file_path")
        if uploaded_path:
            task_state.file_path = uploaded_path
            task_state.task = f"Process the invoice at {uploaded_path} into our ERP system."
            task_state.status = "RUNNING"
            await task_state.add_event({
                "type": "INPUT_RECEIVED",
                "task_id": task_state.task_id,
                "file_path": uploaded_path,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

    agent = Agent(
        interactive=False,
        on_event=on_event_handler,
        escalation_handler=escalation_handler,
        input_handler=input_handler,
    )

    try:
        log = await agent.run(task_state.task)
        task_state.result_log = log.model_dump()
        if log.final_state == AgentState.COMPLETED:
            task_state.status = "COMPLETED"
        else:
            task_state.status = "FAILED"
    except Exception as e:
        task_state.status = "FAILED"
        err_event = {
            "type": "TASK_FAILED",
            "task_id": task_state.task_id,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        await task_state.add_event(err_event)


class AgentDispatchRequest(BaseModel):
    task: str
    file_path: Optional[str] = None


@app.post("/api/agent/dispatch")
async def dispatch_agent_task(req: AgentDispatchRequest):
    if not req.task.strip():
        raise HTTPException(status_code=400, detail="Task prompt cannot be empty")
    task_id = f"task_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    task_state = TaskExecutionState(task_id=task_id, task=req.task, file_path=req.file_path)
    active_tasks[task_id] = task_state
    asyncio.create_task(run_agent_task(task_state))
    return {
        "task_id": task_id,
        "status": "STARTED",
        "task": req.task,
        "created_at": task_state.created_at,
    }


@app.get("/api/agent/tasks/{task_id}/events")
async def stream_task_events(task_id: str, request: Request):
    task_state = active_tasks.get(task_id)
    if not task_state:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    async def event_generator():
        # First deliver historical events already emitted
        for ev in list(task_state.events):
            yield f"data: {json.dumps(ev)}\n\n"

        if task_state.status in ["COMPLETED", "FAILED"] and task_state.event_queue.empty():
            return

        while True:
            if await request.is_disconnected():
                break
            try:
                ev = await asyncio.wait_for(task_state.event_queue.get(), timeout=1.5)
                yield f"data: {json.dumps(ev)}\n\n"
                if ev.get("type") in ["TASK_COMPLETED", "TASK_FAILED"]:
                    break
            except asyncio.TimeoutError:
                yield ": ping\n\n"
                if task_state.status in ["COMPLETED", "FAILED"] and task_state.event_queue.empty():
                    break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/agent/tasks/{task_id}")
async def get_task_status_endpoint(task_id: str):
    task_state = active_tasks.get(task_id)
    if not task_state:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return {
        "task_id": task_state.task_id,
        "task": task_state.task,
        "status": task_state.status,
        "created_at": task_state.created_at,
        "events": task_state.events,
        "result": task_state.result_log,
    }


@app.post("/api/agent/tasks/{task_id}/approve")
async def approve_task_endpoint(task_id: str):
    task_state = active_tasks.get(task_id)
    if not task_state:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    task_state.approval_decision = True
    task_state.approval_event.set()
    return {"status": "approved", "task_id": task_id}


@app.post("/api/agent/tasks/{task_id}/reject")
async def reject_task_endpoint(task_id: str):
    task_state = active_tasks.get(task_id)
    if not task_state:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    task_state.approval_decision = False
    task_state.approval_event.set()
    return {"status": "rejected", "task_id": task_id}


class TaskInputRequest(BaseModel):
    file_path: Optional[str] = None
    input_text: Optional[str] = None


@app.post("/api/agent/tasks/{task_id}/input")
async def provide_task_input(task_id: str, req: TaskInputRequest):
    task_state = active_tasks.get(task_id)
    if not task_state:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    task_state.input_data = req.model_dump()
    task_state.input_event.set()
    return {"status": "input_received", "task_id": task_id}


@app.post("/api/agent/upload")
async def upload_document_endpoint(file: UploadFile = File(...)):
    allowed_exts = {".pdf", ".png", ".jpg", ".jpeg", ".json", ".eml"}
    orig_name = Path(file.filename or "invoice.pdf").name
    ext = Path(orig_name).suffix.lower()
    if ext not in allowed_exts:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {sorted(list(allowed_exts))}",
        )
    upload_dir = Path("demo/invoices/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    clean_stem = re.sub(r"[^a-zA-Z0-9_-]", "_", Path(orig_name).stem)
    dest_path = upload_dir / f"{timestamp}_{clean_stem}{ext}"

    content = await file.read()
    dest_path.write_bytes(content)

    return {
        "status": "uploaded",
        "filename": orig_name,
        "file_path": dest_path.as_posix(),
        "size_bytes": len(content),
    }

