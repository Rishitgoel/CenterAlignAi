import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel, Field
from config import settings
from agent.models import HumanEscalation


class SuspendedTask(BaseModel):
    task_id: str
    original_request: str
    escalation: HumanEscalation
    discovered_facts: Dict[str, Any]
    current_step_idx: int
    plan_json: str
    suspended_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status: str = "PENDING_APPROVAL"  # PENDING_APPROVAL, APPROVED, REJECTED
    operator_notes: Optional[str] = None


class HITLManager:
    """Manages asynchronous human-in-the-loop task suspension, resumption, and approval events."""

    def __init__(self, storage_dir: Optional[str] = None):
        self.storage_dir = Path(storage_dir or "logs/suspended_tasks")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._listeners: List[Callable[[SuspendedTask], Any]] = []

    def suspend_task(
        self,
        task_id: str,
        original_request: str,
        escalation: HumanEscalation,
        discovered_facts: Dict[str, Any],
        current_step_idx: int,
        plan_json: str,
    ) -> SuspendedTask:
        suspended = SuspendedTask(
            task_id=task_id,
            original_request=original_request,
            escalation=escalation,
            discovered_facts=discovered_facts,
            current_step_idx=current_step_idx,
            plan_json=plan_json,
        )
        task_file = self.storage_dir / f"{task_id}.json"
        task_file.write_text(suspended.model_dump_json(indent=2), encoding="utf-8")
        return suspended

    def list_pending_tasks(self) -> List[SuspendedTask]:
        tasks = []
        for file in self.storage_dir.glob("*.json"):
            try:
                data = json.loads(file.read_text(encoding="utf-8"))
                if data.get("status") == "PENDING_APPROVAL":
                    tasks.append(SuspendedTask(**data))
            except Exception:
                pass
        return sorted(tasks, key=lambda x: x.suspended_at, reverse=True)

    def get_task(self, task_id: str) -> Optional[SuspendedTask]:
        task_file = self.storage_dir / f"{task_id}.json"
        if task_file.exists():
            data = json.loads(task_file.read_text(encoding="utf-8"))
            return SuspendedTask(**data)
        return None

    def resolve_task(
        self,
        task_id: str,
        approved: bool,
        operator_notes: Optional[str] = None,
    ) -> Optional[SuspendedTask]:
        task = self.get_task(task_id)
        if not task:
            return None

        task.status = "APPROVED" if approved else "REJECTED"
        task.operator_notes = operator_notes

        task_file = self.storage_dir / f"{task_id}.json"
        task_file.write_text(task.model_dump_json(indent=2), encoding="utf-8")
        return task


hitl_manager = HITLManager()
