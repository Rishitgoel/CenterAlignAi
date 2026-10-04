from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from agent.models import PlannedStep, StepResult, TaskPlan


class WorkingMemory(BaseModel):
    task_id: str
    original_request: str
    discovered_facts: Dict[str, Any] = Field(default_factory=dict)
    executed_steps: List[StepResult] = Field(default_factory=list)
    current_plan: Optional[TaskPlan] = None
    retry_count: int = 0
    errors_encountered: List[str] = Field(default_factory=list)

    def add_fact(self, key: str, value: Any) -> None:
        self.discovered_facts[key] = value

    def get_fact(self, key: str, default: Any = None) -> Any:
        return self.discovered_facts.get(key, default)

    def add_step_result(self, result: StepResult) -> None:
        self.executed_steps.append(result)
        if not result.success and result.error_message:
            self.errors_encountered.append(result.error_message)

    def get_last_error(self) -> Optional[str]:
        if self.errors_encountered:
            return self.errors_encountered[-1]
        return None

    def get_context_summary(self) -> str:
        summary_lines = [
            f"Original Goal: {self.original_request}",
            f"Current Retry Count: {self.retry_count}",
        ]
        if self.discovered_facts:
            summary_lines.append("\nDiscovered Facts & Extracted State:")
            for k, v in self.discovered_facts.items():
                summary_lines.append(f"  - {k}: {v}")

        if self.executed_steps:
            summary_lines.append("\nExecution History:")
            for step in self.executed_steps:
                status = "SUCCESS" if step.success else f"FAILED: {step.error_message}"
                summary_lines.append(
                    f"  - Step {step.step_id} ({step.tool_name}): {status}"
                )

        if self.errors_encountered:
            summary_lines.append(f"\nRecent Error: {self.errors_encountered[-1]}")

        return "\n".join(summary_lines)
