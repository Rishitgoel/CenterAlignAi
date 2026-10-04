"""CentrAlign AI Synthetic Enterprise Task Evaluation Benchmark Suite.

Evaluates Autonomy, Execution, Reliability (Adaptation), Verification,
and Cryptographic Ledger Compliance across synthetic enterprise task permutations.
"""

import asyncio
from datetime import datetime
import json
import threading
import time
from typing import Any, Dict, List
import httpx
from rich.console import Console
from rich.table import Table
import uvicorn

from agent.core import Agent
from agent.models import AgentState
from mock_erp.app import app
from mock_erp.database import clear_database, init_db
from security.audit_ledger import audit_ledger

console = Console()


class ServerThread(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        config = uvicorn.Config(app, host="127.0.0.1", port=8000, log_level="warning")
        self.server = uvicorn.Server(config)

    def run(self):
        self.server.run()

    def stop(self):
        self.server.should_exit = True


class BenchmarkRunner:
    def __init__(self):
        self.results: List[Dict[str, Any]] = []

    async def run_scenario(self, name: str, task: str, expected_state: AgentState, tags: List[str]) -> Dict[str, Any]:
        await clear_database()
        console.print(f"\n[bold cyan]=== Running Benchmark: {name} ===[/bold cyan]")
        start = time.perf_counter()

        agent = Agent(interactive=False)
        try:
            log = await agent.run(task)
            duration = round(time.perf_counter() - start, 3)
            passed = log.final_state == expected_state

            res = {
                "name": name,
                "passed": passed,
                "duration_seconds": duration,
                "steps_taken": len(log.steps_executed),
                "final_state": log.final_state.value,
                "tags": tags,
                "retries": sum(1 for s in log.steps_executed if not s.success),
            }
        except Exception as e:
            duration = round(time.perf_counter() - start, 3)
            res = {
                "name": name,
                "passed": False,
                "duration_seconds": duration,
                "steps_taken": 0,
                "final_state": "EXCEPTION",
                "tags": tags,
                "error": str(e),
                "retries": 0,
            }

        self.results.append(res)
        return res

    async def run_all(self) -> Dict[str, Any]:
        # Ensure DB is initialized
        await init_db()

        # Check if local ERP server is running; start thread if not
        server_thread = None
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get("http://127.0.0.1:8000/docs", timeout=1.0)
        except Exception:
            console.print("[dim]Starting local Mock ERP test server on http://127.0.0.1:8000...[/dim]")
            server_thread = ServerThread()
            server_thread.start()
            await asyncio.sleep(1.5)

        try:
            scenarios = [
                (
                    "Standard Happy Path Invoice Processing",
                    "Process the invoice from demo/invoices/invoice_globex_002.json into our ERP system.",
                    AgentState.COMPLETED,
                    ["autonomy", "execution", "verification"],
                ),
                (
                    "Corrupt File Self-Healing Adaptation",
                    "Process invoice demo/invoices/invoice_malformed_003.json into the ERP system.",
                    AgentState.COMPLETED,
                    ["reliability", "self-healing", "adaptation"],
                ),
                (
                    "Multimodal PDF Ingestion",
                    "Process the PDF invoice at demo/invoices/invoice_cyberdyne_005.pdf into the ERP system.",
                    AgentState.COMPLETED,
                    ["multimodal", "execution"],
                ),
            ]

            for name, task, expected_state, tags in scenarios:
                await self.run_scenario(name, task, expected_state, tags)

            # Audit ledger cryptographic check
            ledger_check = audit_ledger.verify_ledger_integrity()

            # Compute summary metrics
            total = len(self.results)
            passed_count = sum(1 for r in self.results if r["passed"])
            avg_time = round(sum(r["duration_seconds"] for r in self.results) / total, 2) if total else 0

            summary = {
                "total_scenarios": total,
                "passed_scenarios": passed_count,
                "success_rate_percent": round((passed_count / total) * 100, 1) if total else 0,
                "avg_duration_seconds": avg_time,
                "ledger_cryptographic_integrity": ledger_check["valid"],
                "ledger_blocks_verified": ledger_check.get("blocks_verified", 0),
            }

            self.display_report(summary)
            return summary
        finally:
            if server_thread:
                server_thread.stop()

    def display_report(self, summary: Dict[str, Any]):
        table = Table(title="Enterprise Benchmark Evaluation Report", show_header=True, header_style="bold green")
        table.add_column("Scenario", style="white")
        table.add_column("Status", style="bold")
        table.add_column("Duration (s)", style="cyan")
        table.add_column("Steps", style="dim")
        table.add_column("Tags", style="yellow")

        for r in self.results:
            status = "[green]PASS[/green]" if r["passed"] else "[red]FAIL[/red]"
            table.add_row(
                r["name"],
                status,
                str(r["duration_seconds"]),
                str(r["steps_taken"]),
                ", ".join(r["tags"]),
            )

        console.print(table)
        console.print(f"[bold cyan]Total Success Rate:[/bold cyan] {summary['success_rate_percent']}%")
        console.print(f"[bold cyan]Cryptographic Ledger Integrity:[/bold cyan] {'VALID (PASS)' if summary['ledger_cryptographic_integrity'] else 'TAMPERED (FAIL)'}")
        console.print(f"[bold cyan]Audit Blocks Verified:[/bold cyan] {summary['ledger_blocks_verified']}")


async def main():
    runner = BenchmarkRunner()
    await runner.run_all()


if __name__ == "__main__":
    asyncio.run(main())
