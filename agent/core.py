import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import time
from typing import Any, Callable, Dict, List, Optional, Union
import uuid
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.table import Table

from config import settings
from agent.executor import Executor
from agent.memory import WorkingMemory
from agent.models import (
    AgentState,
    ExecutionLog,
    HumanEscalation,
    PlannedStep,
    StepResult,
    TaskPlan,
    VerificationResult,
)
from agent.observer import Observer
from agent.planner import Planner
from agent.verifier import Verifier
from tools import get_default_registry
from security.audit_ledger import audit_ledger
from security.credential_vault import credential_vault

console = Console()


class Agent:
    def __init__(
        self,
        interactive: bool = True,
        on_event: Optional[Callable[[Dict[str, Any]], Any]] = None,
        escalation_handler: Optional[Callable[[HumanEscalation, WorkingMemory], Any]] = None,
        input_handler: Optional[Callable[[Dict[str, Any], WorkingMemory], Any]] = None,
    ):
        self.interactive = interactive
        self.on_event = on_event
        self.escalation_handler = escalation_handler
        self.input_handler = input_handler
        self.registry = get_default_registry()
        self.planner = Planner()
        self.executor = Executor(self.registry)
        self.observer = Observer()
        self.verifier = Verifier(self.registry)
        self.state = AgentState.IDLE
        self.current_task_id = None

    async def _emit_event(self, event_type: str, data: Optional[Dict[str, Any]] = None):
        if not self.on_event:
            return
        payload = {
            "type": event_type,
            "task_id": self.current_task_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **(data or {}),
        }
        try:
            if asyncio.iscoroutinefunction(self.on_event):
                await self.on_event(payload)
            elif callable(self.on_event):
                res = self.on_event(payload)
                if asyncio.iscoroutine(res):
                    await res
        except Exception as e:
            console.print(f"[dim red]Error emitting event: {e}[/dim red]")

    async def run(self, task: str) -> ExecutionLog:
        task_id = f"task_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        self.current_task_id = task_id
        started_at = datetime.now(timezone.utc).isoformat()
        start_perf = time.perf_counter()

        await self._emit_event("TASK_STARTED", {"task": task})

        memory = WorkingMemory(task_id=task_id, original_request=task)

        await self._transition_state(AgentState.UNDERSTANDING)
        console.print(Panel(f"[bold green]Goal:[/bold green] {task}", title="Task Understanding", border_style="green"))

        # --- PLANNING ---
        await self._transition_state(AgentState.PLANNING)
        tools_prompt = self.registry.get_tools_prompt()
        plan = await self.planner.create_plan(task, tools_prompt, memory)
        memory.current_plan = plan

        self._display_plan(plan)
        await self._emit_event("PLAN_CREATED", {"goal": task, "steps": [s.model_dump() for s in plan.steps]})

        # --- EXECUTION LOOP ---
        step_idx = 0
        while step_idx < len(plan.steps):
            step = plan.steps[step_idx]

            await self._transition_state(AgentState.EXECUTING)
            console.print(f"\n[bold cyan]Executing Step {step.step_number}/{len(plan.steps)}:[/bold cyan] {step.description}")
            await self._emit_event(
                "STEP_START",
                {
                    "step_number": step.step_number,
                    "total_steps": len(plan.steps),
                    "tool_name": step.tool_name,
                    "description": step.description,
                    "tool_input": step.tool_input,
                },
            )

            result = await self.executor.execute_step(step, memory)
            memory.add_step_result(result)
            audit_ledger.record_event(
                task_id=memory.task_id,
                action_type="TOOL_EXECUTION",
                payload={
                    "step_number": step.step_number,
                    "tool_name": step.tool_name,
                    "success": result.success,
                    "error_message": result.error_message,
                },
            )

            await self._emit_event(
                "STEP_COMPLETE",
                {
                    "step_number": step.step_number,
                    "total_steps": len(plan.steps),
                    "tool_name": step.tool_name,
                    "success": result.success,
                    "duration_ms": result.duration_ms,
                    "output_data": result.output_data,
                    "error_message": result.error_message,
                },
            )

            await self._transition_state(AgentState.OBSERVING)
            observation = self.observer.observe(step, result, memory)

            # 1. Check for Human-in-the-Loop Escalation
            if observation.needs_escalation and observation.escalation:
                await self._transition_state(AgentState.ESCALATED)
                approved = await self._handle_escalation(
                    escalation=observation.escalation,
                    memory=memory,
                    step_idx=step_idx,
                    plan=plan,
                )
                if approved:
                    console.print("[green][APPROVED] Human approval granted. Proceeding to enter invoice.[/green]")
                    # Record facts and continue
                    for k, v in observation.facts_discovered.items():
                        memory.add_fact(k, v)
                    step_idx += 1
                    continue
                else:
                    console.print("[red][REJECTED] Human rejected task execution. Safely halting.[/red]")
                    return await self._finalize_log(
                        memory=memory,
                        state=AgentState.FAILED,
                        summary="Execution halted by user during human-in-the-loop escalation.",
                        started_at=started_at,
                        start_perf=start_perf,
                        evidence={"escalation": observation.escalation.model_dump()},
                    )

            # 2. Check for Tool Failure & Trigger Autonomous Adaptation
            if observation.status == "failure":
                console.print(f"[bold red][FAILURE] Step {step.step_number} Failed:[/bold red] {result.error_message}")

                if memory.retry_count < settings.max_retries:
                    await self._transition_state(AgentState.ADAPTING)
                    memory.retry_count += 1
                    console.print(
                        f"[bold yellow][RETRY] Self-Correcting (Attempt {memory.retry_count}/{settings.max_retries}):[/bold yellow] "
                        "Re-planning alternative strategy..."
                    )
                    await self._emit_event(
                        "ADAPTATION_TRIGGERED",
                        {
                            "retry_count": memory.retry_count,
                            "failed_step": step.step_number,
                            "error_message": result.error_message,
                        },
                    )

                    new_plan = await self.planner.replan(
                        original_plan=plan,
                        failed_step=step,
                        error_message=result.error_message or "Unknown error",
                        tools_description=tools_prompt,
                        memory=memory,
                    )
                    plan = new_plan
                    memory.current_plan = plan
                    self._display_plan(plan, title="Revised Plan (Recovered)")
                    await self._emit_event("PLAN_CREATED", {"goal": task, "steps": [s.model_dump() for s in plan.steps], "is_replan": True})
                    step_idx = 0  # Re-evaluate from first recovery step
                    continue
                else:
                    console.print("[bold red][ERROR] Max retries exceeded. Task execution failed.[/bold red]")
                    return await self._finalize_log(
                        memory=memory,
                        state=AgentState.FAILED,
                        summary=f"Task failed after {memory.retry_count} adaptation attempts. Last error: {result.error_message}",
                        started_at=started_at,
                        start_perf=start_perf,
                    )

            # Step succeeded
            console.print(f"   [bold green][OK] Step {step.step_number} Success[/bold green]")
            for k, v in observation.facts_discovered.items():
                memory.add_fact(k, v)

            step_idx += 1

        # --- VERIFICATION ---
        await self._transition_state(AgentState.VERIFYING)
        console.print("\n[bold magenta]Verifying Outcome against System of Record...[/bold magenta]")
        verification = await self.verifier.verify(plan, memory)

        self._display_verification(verification)
        await self._emit_event(
            "VERIFICATION_REPORT",
            {
                "passed": verification.passed,
                "checks": [c.model_dump() for c in verification.checks],
                "discrepancies": verification.discrepancies,
                "evidence": verification.evidence,
                "block_hash": getattr(audit_ledger, "_last_hash", ""),
            },
        )

        if verification.passed:
            await self._transition_state(AgentState.COMPLETED)
            vendor = memory.get_fact("vendor_name")
            inv_num = memory.get_fact("invoice_number") or "N/A"
            amt = memory.get_fact("amount")
            rec_id = memory.get_fact("created_invoice_id")
            deleted_id = memory.get_fact("deleted_invoice_id")
            ui_status = memory.get_fact("ui_status")
            status_fact = memory.get_fact("erp_invoice_status")

            if deleted_id:
                summary = f"Successfully completed task. Removed invoice #{deleted_id} from ERP system."
            elif status_fact == "approved" and not memory.get_fact("file_path") and not rec_id:
                summary = f"Successfully completed task. Approved invoice in ERP system."
            elif vendor and amt is not None:
                float_amt = float(amt)
                verif_proof = f"Verified in ERP under record ID #{rec_id}." if rec_id else "Verified in company portal with screenshot proof."
                summary = (
                    f"Successfully completed task. Processed invoice from '{vendor}' "
                    f"({inv_num}) for ${float_amt:,.2f}. {verif_proof}"
                )
            elif ui_status:
                summary = f"Successfully completed task. {ui_status}."
            else:
                summary = f"Successfully completed task: {plan.goal}."

            console.print(Panel(f"[bold green]SUCCESS:[/bold green] {summary}", title="Task Complete", border_style="green"))
            return await self._finalize_log(
                memory=memory,
                state=AgentState.COMPLETED,
                summary=summary,
                started_at=started_at,
                start_perf=start_perf,
                evidence=verification.evidence,
            )
        else:
            await self._transition_state(AgentState.FAILED)
            summary = f"Task execution finished but state verification failed: {', '.join(verification.discrepancies)}"
            console.print(Panel(f"[bold red]VERIFICATION FAILED:[/bold red] {summary}", title="Verification Error", border_style="red"))
            return await self._finalize_log(
                memory=memory,
                state=AgentState.FAILED,
                summary=summary,
                started_at=started_at,
                start_perf=start_perf,
                evidence=verification.evidence,
            )

    async def _transition_state(self, new_state: AgentState):
        prev = self.state
        self.state = new_state
        console.print(f"[dim]State Transition: {prev.value} -> [bold]{new_state.value}[/bold][/dim]")
        if self.current_task_id:
            audit_ledger.record_event(
                task_id=self.current_task_id,
                action_type="STATE_TRANSITION",
                payload={"from_state": prev.value, "to_state": new_state.value},
            )
        await self._emit_event("STATE_CHANGE", {"from_state": prev.value, "to_state": new_state.value})

    def _display_plan(self, plan: TaskPlan, title: str = "Action Plan"):
        table = Table(title=title, show_header=True, header_style="bold cyan")
        table.add_column("Step #", style="dim", width=8)
        table.add_column("Tool", style="yellow", width=14)
        table.add_column("Description", style="white")
        table.add_column("Verification Hint", style="dim")

        for step in plan.steps:
            table.add_row(
                str(step.step_number),
                step.tool_name,
                step.description,
                step.verification_hint or "-",
            )
        console.print(table)

    def _display_verification(self, verification: VerificationResult):
        table = Table(title="State Verification Report", show_header=True, header_style="bold magenta")
        table.add_column("Check Target", style="white")
        table.add_column("Expected", style="cyan")
        table.add_column("Actual (Queried)", style="cyan")
        table.add_column("Status", style="bold")

        for c in verification.checks:
            status_str = "[green]MATCH (PASS)[/green]" if c.matched else "[red]MISMATCH (FAIL)[/red]"
            table.add_row(c.target, str(c.expected), str(c.actual), status_str)
        console.print(table)

    async def _handle_escalation(
        self,
        escalation: HumanEscalation,
        memory: WorkingMemory,
        step_idx: int,
        plan: TaskPlan,
    ) -> bool:
        from agent.hitl_manager import hitl_manager

        # Persist suspended task into HITL manager storage queue
        hitl_manager.suspend_task(
            task_id=memory.task_id,
            original_request=memory.original_request,
            escalation=escalation,
            discovered_facts=memory.discovered_facts,
            current_step_idx=step_idx,
            plan_json=plan.model_dump_json(),
        )

        console.print(
            Panel(
                f"[bold red]HUMAN-IN-THE-LOOP ESCALATION REQUIRED[/bold red]\n\n"
                f"{escalation.question}\n\n"
                f"[dim]Reason: {escalation.reason}[/dim]\n"
                f"[bold cyan]Queue Status:[/bold cyan] Task registered in Web Operator Queue (/portal)\n"
                f"[dim]Task ID: {memory.task_id}[/dim]",
                title="Human Approval Gate",
                border_style="yellow",
            )
        )
        await self._emit_event(
            "ESCALATION_TRIGGERED",
            {
                "question": escalation.question,
                "reason": escalation.reason,
                "context": escalation.context,
                "options": escalation.options,
            },
        )

        approved = False
        if self.escalation_handler:
            if asyncio.iscoroutinefunction(self.escalation_handler):
                approved = await self.escalation_handler(escalation, memory)
            else:
                approved = self.escalation_handler(escalation, memory)
        elif self.interactive:
            approved = Confirm.ask("Do you approve proceeding with this action?", default=True)
        else:
            # Non-interactive default approval
            approved = True

        audit_ledger.record_event(
            task_id=memory.task_id,
            action_type="ESCALATION_DECISION",
            payload={
                "question": escalation.question,
                "reason": escalation.reason,
                "approved": approved,
            },
        )
        await self._emit_event(
            "ESCALATION_RESOLVED",
            {
                "approved": approved,
                "question": escalation.question,
            },
        )
        return approved

    async def _finalize_log(
        self,
        memory: WorkingMemory,
        state: AgentState,
        summary: str,
        started_at: str,
        start_perf: float,
        evidence: dict = None,
    ) -> ExecutionLog:
        duration_ms = round((time.perf_counter() - start_perf) * 1000.0, 2)
        completed_at = datetime.now(timezone.utc).isoformat()

        log = ExecutionLog(
            task_id=memory.task_id,
            original_request=memory.original_request,
            plan=memory.current_plan,
            steps_executed=memory.executed_steps,
            final_state=state,
            summary=summary,
            evidence=evidence or {},
            started_at=started_at,
            completed_at=completed_at,
            total_duration_ms=duration_ms,
        )

        audit_ledger.record_event(
            task_id=memory.task_id,
            action_type="VERIFICATION_RESULT",
            payload={
                "final_state": state.value,
                "summary": summary,
                "evidence_keys": list((evidence or {}).keys()),
            },
        )

        log_path = Path(settings.log_dir) / f"{memory.task_id}.json"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_json = log.model_dump_json(indent=2)
        sanitized_json = credential_vault.redact_text(log_json)
        log_path.write_text(sanitized_json, encoding="utf-8")
        console.print(f"\n[dim]Audit evidence log written to: [bold]{log_path}[/bold][/dim]")

        block_hash = getattr(audit_ledger, "_last_hash", "")
        if state == AgentState.COMPLETED:
            await self._emit_event(
                "TASK_COMPLETED",
                {
                    "summary": summary,
                    "final_state": state.value,
                    "duration_ms": duration_ms,
                    "evidence": evidence or {},
                    "block_hash": block_hash,
                },
            )
        else:
            await self._emit_event(
                "TASK_FAILED",
                {
                    "summary": summary,
                    "final_state": state.value,
                    "duration_ms": duration_ms,
                    "evidence": evidence or {},
                    "block_hash": block_hash,
                },
            )

        return log
