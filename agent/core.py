from datetime import datetime
import json
from pathlib import Path
import time
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

console = Console()


class Agent:
    def __init__(self, interactive: bool = True):
        self.interactive = interactive
        self.registry = get_default_registry()
        self.planner = Planner()
        self.executor = Executor(self.registry)
        self.observer = Observer()
        self.verifier = Verifier(self.registry)
        self.state = AgentState.IDLE

    async def run(self, task: str) -> ExecutionLog:
        task_id = f"task_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        started_at = datetime.utcnow().isoformat()
        start_perf = time.perf_counter()

        memory = WorkingMemory(task_id=task_id, original_request=task)

        self._transition_state(AgentState.UNDERSTANDING)
        console.print(Panel(f"[bold green]Goal:[/bold green] {task}", title="Task Understanding", border_style="green"))

        # --- PLANNING ---
        self._transition_state(AgentState.PLANNING)
        tools_prompt = self.registry.get_tools_prompt()
        plan = await self.planner.create_plan(task, tools_prompt, memory)
        memory.current_plan = plan

        self._display_plan(plan)

        # --- EXECUTION LOOP ---
        step_idx = 0
        while step_idx < len(plan.steps):
            step = plan.steps[step_idx]

            self._transition_state(AgentState.EXECUTING)
            console.print(f"\n[bold cyan]Executing Step {step.step_number}/{len(plan.steps)}:[/bold cyan] {step.description}")

            result = await self.executor.execute_step(step, memory)
            memory.add_step_result(result)

            self._transition_state(AgentState.OBSERVING)
            observation = self.observer.observe(step, result, memory)

            # 1. Check for Human-in-the-Loop Escalation
            if observation.needs_escalation and observation.escalation:
                self._transition_state(AgentState.ESCALATED)
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
                    return self._finalize_log(
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
                    self._transition_state(AgentState.ADAPTING)
                    memory.retry_count += 1
                    console.print(
                        f"[bold yellow][RETRY] Self-Correcting (Attempt {memory.retry_count}/{settings.max_retries}):[/bold yellow] "
                        "Re-planning alternative strategy..."
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
                    step_idx = 0  # Re-evaluate from first recovery step
                    continue
                else:
                    console.print("[bold red][ERROR] Max retries exceeded. Task execution failed.[/bold red]")
                    return self._finalize_log(
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
        self._transition_state(AgentState.VERIFYING)
        console.print("\n[bold magenta]Verifying Outcome against System of Record...[/bold magenta]")
        verification = await self.verifier.verify(plan, memory)

        self._display_verification(verification)

        if verification.passed:
            self._transition_state(AgentState.COMPLETED)
            summary = (
                f"Successfully completed task. Processed invoice from '{memory.get_fact('vendor_name')}' "
                f"({memory.get_fact('invoice_number')}) for ${float(memory.get_fact('amount', 0.0)):,.2f}. "
                f"Verified in ERP under record ID #{memory.get_fact('created_invoice_id')}."
            )
            console.print(Panel(f"[bold green]SUCCESS:[/bold green] {summary}", title="Task Complete", border_style="green"))
            return self._finalize_log(
                memory=memory,
                state=AgentState.COMPLETED,
                summary=summary,
                started_at=started_at,
                start_perf=start_perf,
                evidence=verification.evidence,
            )
        else:
            self._transition_state(AgentState.FAILED)
            summary = f"Task execution finished but state verification failed: {', '.join(verification.discrepancies)}"
            console.print(Panel(f"[bold red]VERIFICATION FAILED:[/bold red] {summary}", title="Verification Error", border_style="red"))
            return self._finalize_log(
                memory=memory,
                state=AgentState.FAILED,
                summary=summary,
                started_at=started_at,
                start_perf=start_perf,
                evidence=verification.evidence,
            )

    def _transition_state(self, new_state: AgentState):
        prev = self.state
        self.state = new_state
        console.print(f"[dim]State Transition: {prev.value} -> [bold]{new_state.value}[/bold][/dim]")

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
        if self.interactive:
            return Confirm.ask("Do you approve proceeding with this action?", default=True)
        # Non-interactive default approval
        return True

    def _finalize_log(
        self,
        memory: WorkingMemory,
        state: AgentState,
        summary: str,
        started_at: str,
        start_perf: float,
        evidence: dict = None,
    ) -> ExecutionLog:
        duration_ms = round((time.perf_counter() - start_perf) * 1000.0, 2)
        completed_at = datetime.utcnow().isoformat()

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

        log_path = Path(settings.log_dir) / f"{memory.task_id}.json"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(log.model_dump_json(indent=2), encoding="utf-8")
        console.print(f"\n[dim]Audit evidence log written to: [bold]{log_path}[/bold][/dim]")

        return log
