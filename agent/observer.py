from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from config import settings
from agent.memory import WorkingMemory
from agent.models import HumanEscalation, PlannedStep, StepResult


class Observation(BaseModel):
    status: str  # "success" | "failure" | "needs_escalation"
    facts_discovered: Dict[str, Any] = Field(default_factory=dict)
    needs_escalation: bool = False
    escalation: Optional[HumanEscalation] = None
    error_details: Optional[str] = None


class Observer:
    def __init__(self, approval_threshold: Optional[float] = None):
        self.approval_threshold = approval_threshold or settings.approval_threshold

    def observe(
        self,
        step: PlannedStep,
        result: StepResult,
        memory: WorkingMemory,
    ) -> Observation:
        if not result.success:
            return Observation(
                status="failure",
                error_details=result.error_message or "Unknown tool execution failure",
            )

        facts: Dict[str, Any] = {}
        data = result.output_data

        # 1. Inspect file parser or document extractor output
        if step.tool_name in ["file_parser", "document_extractor"] and isinstance(data, dict):
            for field in ["vendor_name", "invoice_number", "amount", "due_date", "currency", "confidence_score"]:
                if field in data:
                    facts[field] = data[field]

            # Escalation Policy: High value invoice threshold
            amount = float(data.get("amount", 0.0))
            if amount > self.approval_threshold:
                escalation = HumanEscalation(
                    reason="HIGH_VALUE_THRESHOLD_EXCEEDED",
                    question=(
                        f"Invoice from '{data.get('vendor_name')}' for ${amount:,.2f} "
                        f"exceeds the authorized autonomous spending threshold of ${self.approval_threshold:,.2f}. "
                        "Do you authorize entering this invoice into the financial ERP?"
                    ),
                    context={
                        "vendor_name": data.get("vendor_name"),
                        "amount": amount,
                        "invoice_number": data.get("invoice_number"),
                        "threshold": self.approval_threshold,
                    },
                    options=["approve", "reject"],
                )
                return Observation(
                    status="needs_escalation",
                    facts_discovered=facts,
                    needs_escalation=True,
                    escalation=escalation,
                )

        # 2. Inspect ERP Client output
        elif step.tool_name == "erp_client" and isinstance(data, dict):
            if "id" in data:
                facts["created_invoice_id"] = data["id"]
            if "status" in data:
                facts["erp_invoice_status"] = data["status"]
            for field in ["vendor_name", "invoice_number", "amount", "due_date"]:
                if field in data and data[field]:
                    facts[field] = data[field]

        # 3. Inspect File Writer output
        elif step.tool_name == "file_writer" and isinstance(data, dict):
            if "file_path" in data:
                facts["report_file_path"] = data["file_path"]

        # 4. Inspect Browser Operator output
        elif step.tool_name == "browser_operator" and isinstance(data, dict):
            if "screenshot_path" in data:
                facts["browser_screenshot_path"] = data["screenshot_path"]
            if "toast_feedback" in data:
                facts["browser_feedback"] = data["toast_feedback"]
            if "ui_status" in data:
                facts["ui_status"] = data["ui_status"]
            for field in ["vendor_name", "invoice_number", "amount", "due_date"]:
                if field in data and data[field]:
                    facts[field] = data[field]

        return Observation(
            status="success",
            facts_discovered=facts,
            needs_escalation=False,
        )
