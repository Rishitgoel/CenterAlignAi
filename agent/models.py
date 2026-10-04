from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AgentState(str, Enum):
    IDLE = "IDLE"
    UNDERSTANDING = "UNDERSTANDING"
    PLANNING = "PLANNING"
    EXECUTING = "EXECUTING"
    OBSERVING = "OBSERVING"
    AWAITING_INPUT = "AWAITING_INPUT"
    ADAPTING = "ADAPTING"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ESCALATED = "ESCALATED"


class StepResult(BaseModel):
    step_id: int
    tool_name: str
    action: str
    input_data: Dict[str, Any] = Field(default_factory=dict)
    output_data: Any = None
    success: bool
    error_message: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    duration_ms: float = 0.0


class PlannedStep(BaseModel):
    step_number: int
    description: str
    tool_name: str
    tool_input: Dict[str, Any] = Field(default_factory=dict)
    depends_on: Optional[int] = None
    verification_hint: Optional[str] = None


class TaskPlan(BaseModel):
    goal: str
    steps: List[PlannedStep] = Field(default_factory=list)


class HumanEscalation(BaseModel):
    reason: str
    question: str
    context: Dict[str, Any] = Field(default_factory=dict)
    options: List[str] = Field(default_factory=lambda: ["approve", "reject"])


class VerificationCheck(BaseModel):
    target: str
    expected: Any
    actual: Any
    matched: bool
    details: Optional[str] = None


class VerificationResult(BaseModel):
    passed: bool
    checks: List[VerificationCheck] = Field(default_factory=list)
    evidence: Dict[str, Any] = Field(default_factory=dict)
    discrepancies: List[str] = Field(default_factory=list)


class ExecutionLog(BaseModel):
    task_id: str
    original_request: str
    plan: Optional[TaskPlan] = None
    steps_executed: List[StepResult] = Field(default_factory=list)
    final_state: AgentState
    summary: str
    evidence: Dict[str, Any] = Field(default_factory=dict)
    started_at: str
    completed_at: str
    total_duration_ms: float
