import asyncio
import json
import re
from typing import Any, Dict, List, Optional
from google import genai
from config import settings
from agent.memory import WorkingMemory
from agent.models import PlannedStep, TaskPlan


PLANNER_SYSTEM_PROMPT = """You are an expert autonomous task decomposition planner for an enterprise task worker.
Your role is to understand the user's high-level goal, inspect available tools, and produce an ordered sequence of executable steps in strict JSON format.

RULES:
1. Decompose the request into logical, atomic steps using available tools.
2. In 'tool_input', use placeholder syntax like '{{variable_name}}' for values that will only be discovered from prior steps (e.g., '{{extracted_vendor_name}}', '{{extracted_invoice_number}}', '{{extracted_amount}}', '{{extracted_due_date}}', '{{created_invoice_id}}').
3. Always include verification hints where appropriate so the agent can verify the action afterwards.
4. Output MUST BE strictly valid JSON conforming to the TaskPlan schema:
{
  "goal": "Concise summary of the task",
  "steps": [
    {
      "step_number": 1,
      "description": "What this step does",
      "tool_name": "exact_tool_name",
      "tool_input": { ... },
      "depends_on": null,
      "verification_hint": "What to inspect"
    }
  ]
}
Do NOT return Markdown fences or explanatory text. Return pure JSON only.
"""

REPLANNER_SYSTEM_PROMPT = """You are an expert autonomous error recovery replanner.
A step in the previous plan failed. Your job is to adapt the plan, applying alternative strategies, fallbacks, or corrections based on the error and discovered facts.

Output strictly valid JSON conforming to the TaskPlan schema without markdown code blocks.
"""


class Planner:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.gemini_api_key
        self._client: Optional[genai.Client] = None

    def _get_client(self) -> Optional[genai.Client]:
        if not self._client and self.api_key:
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    async def create_plan(
        self,
        task: str,
        tools_description: str,
        memory: WorkingMemory,
    ) -> TaskPlan:
        client = self._get_client()

        # If LLM client is available, plan using Gemini Flash with strict timeout
        if client:
            try:
                user_prompt = (
                    f"AVAILABLE TOOLS:\n{tools_description}\n\n"
                    f"CURRENT CONTEXT & MEMORY:\n{memory.get_context_summary()}\n\n"
                    f"USER TASK:\n{task}\n\n"
                    "Generate the optimal TaskPlan JSON:"
                )
                response = await asyncio.wait_for(
                    client.aio.models.generate_content(
                        model="gemini-3.5-flash-lite",
                        contents=f"{PLANNER_SYSTEM_PROMPT}\n\n{user_prompt}",
                    ),
                    timeout=5.0,
                )
                raw_text = response.text or ""
                return self._parse_plan_json(raw_text, fallback_task=task)
            except Exception:
                # Fallback to deterministic heuristic plan if API is unavailable, rate-limited, or times out
                pass

        # Deterministic heuristic plan generator (guarantees zero-dependency operation)
        return self._create_heuristic_plan(task)

    async def replan(
        self,
        original_plan: TaskPlan,
        failed_step: PlannedStep,
        error_message: str,
        tools_description: str,
        memory: WorkingMemory,
    ) -> TaskPlan:
        client = self._get_client()

        if client:
            try:
                prompt = (
                    f"AVAILABLE TOOLS:\n{tools_description}\n\n"
                    f"PREVIOUS PLAN:\n{original_plan.model_dump_json(indent=2)}\n\n"
                    f"FAILED STEP: Step {failed_step.step_number} ({failed_step.tool_name})\n"
                    f"ERROR ENCOUNTERED:\n{error_message}\n\n"
                    f"MEMORY CONTEXT:\n{memory.get_context_summary()}\n\n"
                    "Formulate a corrected, recovered TaskPlan JSON that overcomes this failure:"
                )
                response = await asyncio.wait_for(
                    client.aio.models.generate_content(
                        model="gemini-3.5-flash-lite",
                        contents=f"{REPLANNER_SYSTEM_PROMPT}\n\n{prompt}",
                    ),
                    timeout=5.0,
                )
                raw_text = response.text or ""
                return self._parse_plan_json(raw_text, fallback_task=original_plan.goal)
            except Exception:
                pass

        # Deterministic replan heuristic
        return self._replan_heuristic(original_plan, failed_step, error_message, memory)

    def _parse_plan_json(self, raw_text: str, fallback_task: str) -> TaskPlan:
        # Strip potential markdown fences
        cleaned = re.sub(r"^```(?:json)?\s*", "", raw_text.strip(), flags=re.MULTILINE)
        cleaned = re.sub(r"```$", "", cleaned.strip(), flags=re.MULTILINE).strip()

        # Find first JSON object
        json_match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                return TaskPlan(**data)
            except Exception:
                pass

        return self._create_heuristic_plan(fallback_task)

    def _create_heuristic_plan(self, task: str) -> TaskPlan:
        """Deterministic enterprise workflow plan for invoice tasks."""
        # Detect target file path in task prompt (supporting json, csv, txt, pdf, eml)
        file_match = re.search(r"([\w/\\.-]+\.(?:json|csv|txt|pdf|eml|png|jpg))", task, re.IGNORECASE)
        file_path = file_match.group(1) if file_match else "demo/invoices/invoice_acme_001.json"

        # Check if file requires multimodal document understanding
        is_multimodal = any(file_path.lower().endswith(ext) for ext in [".pdf", ".eml", ".png", ".jpg", ".jpeg"])
        extractor_tool = "document_extractor" if is_multimodal else "file_parser"

        # Check if user explicitly requests browser / web portal interaction
        use_browser = any(kw in task.lower() for kw in ["browser", "portal", "website", "web portal", "ui", "web form"])

        if use_browser:
            return TaskPlan(
                goal=task,
                steps=[
                    PlannedStep(
                        step_number=1,
                        description=f"Extract invoice document data from {file_path}",
                        tool_name=extractor_tool,
                        tool_input={"file_path": file_path},
                        verification_hint="Verify vendor_name and amount are extracted",
                    ),
                    PlannedStep(
                        step_number=2,
                        description="Navigate to company web portal and submit invoice form via browser",
                        tool_name="browser_operator",
                        tool_input={
                            "action": "enter_invoice_form",
                            "form_data": {
                                "vendor_name": "{{vendor_name}}",
                                "invoice_number": "{{invoice_number}}",
                                "amount": "{{amount}}",
                                "due_date": "{{due_date}}",
                                "notes": "Submitted via CentrAlign Autonomous Browser Worker",
                            },
                            "headless": True,
                            "screenshot_path": "logs/portal_submission_screenshot.png",
                        },
                        depends_on=1,
                        verification_hint="Verify modal submission and toast confirmation banner",
                    ),
                    PlannedStep(
                        step_number=3,
                        description="Write task audit trail and completion report",
                        tool_name="file_writer",
                        tool_input={
                            "file_path": "logs/browser_task_completion_report.md",
                            "content": "Invoice entry completed via Playwright browser operator for {{vendor_name}} (Invoice #{{invoice_number}}). Amount: ${{amount}}.",
                        },
                        depends_on=2,
                        verification_hint="Confirm completion report exists on disk",
                    ),
                ],
            )

        return TaskPlan(
            goal=task,
            steps=[
                PlannedStep(
                    step_number=1,
                    description=f"Extract invoice document data from {file_path}",
                    tool_name=extractor_tool,
                    tool_input={"file_path": file_path, "format": "auto"} if not is_multimodal else {"file_path": file_path},
                    verification_hint="Verify vendor_name and amount are extracted",
                ),
                PlannedStep(
                    step_number=2,
                    description="Enter extracted invoice details into internal ERP system",
                    tool_name="erp_client",
                    tool_input={
                        "action": "create_invoice",
                        "invoice_data": {
                            "vendor_name": "{{vendor_name}}",
                            "invoice_number": "{{invoice_number}}",
                            "amount": "{{amount}}",
                            "due_date": "{{due_date}}",
                            "currency": "{{currency}}",
                        },
                    },
                    depends_on=1,
                    verification_hint="Check response contains created invoice ID",
                ),
                PlannedStep(
                    step_number=3,
                    description="Write task audit trail and completion report",
                    tool_name="file_writer",
                    tool_input={
                        "file_path": "logs/task_completion_report.md",
                        "content": "Invoice entry completed successfully for {{vendor_name}} (Invoice #{{invoice_number}}). Amount: ${{amount}}.",
                    },
                    depends_on=2,
                    verification_hint="Confirm completion report exists on disk",
                ),
            ],
        )

    def _replan_heuristic(
        self,
        original_plan: TaskPlan,
        failed_step: PlannedStep,
        error_message: str,
        memory: WorkingMemory,
    ) -> TaskPlan:
        """Deterministic recovery plan when step fails."""
        # If file_parser failed on JSON, switch to txt regex fallback
        if failed_step.tool_name == "file_parser" and "json" in error_message.lower():
            file_path = failed_step.tool_input.get("file_path", "demo/invoices/invoice_malformed_003.json")
            return TaskPlan(
                goal=f"Recovered Plan: {original_plan.goal}",
                steps=[
                    PlannedStep(
                        step_number=1,
                        description=f"Retry parsing {file_path} using plain-text regex heuristic fallback",
                        tool_name="file_parser",
                        tool_input={"file_path": file_path, "format": "txt"},
                        verification_hint="Extract invoice fields despite syntax errors",
                    ),
                    PlannedStep(
                        step_number=2,
                        description="Enter recovered invoice data into ERP system",
                        tool_name="erp_client",
                        tool_input={
                            "action": "create_invoice",
                            "invoice_data": {
                                "vendor_name": "{{vendor_name}}",
                                "invoice_number": "{{invoice_number}}",
                                "amount": "{{amount}}",
                                "due_date": "{{due_date}}",
                                "currency": "{{currency}}",
                            },
                        },
                        depends_on=1,
                    ),
                    PlannedStep(
                        step_number=3,
                        description="Write recovery audit log",
                        tool_name="file_writer",
                        tool_input={
                            "file_path": "logs/recovered_task_report.md",
                            "content": "Invoice recovered and entered for {{vendor_name}} ({{invoice_number}}). Amount: ${{amount}}.",
                        },
                        depends_on=2,
                    ),
                ],
            )

        return original_plan
