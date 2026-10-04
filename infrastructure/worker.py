import asyncio
from datetime import datetime
import json
from pathlib import Path
from typing import Dict, List, Optional
import uuid
from pydantic import BaseModel, Field

from agent.core import Agent
from agent.models import AgentState


class TaskJob(BaseModel):
    job_id: str
    task: str
    status: str = "PENDING"  # PENDING, RUNNING, COMPLETED, FAILED
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    summary: Optional[str] = None
    error: Optional[str] = None
    task_id: Optional[str] = None


class WorkerService:
    """Enterprise job queue and worker execution manager.

    Provides durable task persistence, asynchronous execution, and job status tracking.
    """

    def __init__(self, job_store_dir: str = "logs/jobs"):
        self.job_store_dir = Path(job_store_dir)
        self.job_store_dir.mkdir(parents=True, exist_ok=True)
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._running: bool = False

    def submit_task(self, task: str) -> str:
        """Enqueues a natural language task and persists the pending job record."""
        job_id = f"job_{uuid.uuid4().hex[:10]}"
        job = TaskJob(
            job_id=job_id,
            task=task,
            status="PENDING",
        )
        self._save_job(job)
        self._queue.put_nowait(job_id)
        return job_id

    def _save_job(self, job: TaskJob):
        job.updated_at = datetime.utcnow().isoformat()
        job_file = self.job_store_dir / f"{job.job_id}.json"
        job_file.write_text(job.model_dump_json(indent=2), encoding="utf-8")

    def get_job(self, job_id: str) -> Optional[TaskJob]:
        """Loads job state from persistent storage."""
        job_file = self.job_store_dir / f"{job_id}.json"
        if not job_file.exists():
            return None
        return TaskJob.model_validate_json(job_file.read_text(encoding="utf-8"))

    def list_jobs(self) -> List[TaskJob]:
        """Lists all recorded background jobs."""
        jobs = []
        for file in self.job_store_dir.glob("job_*.json"):
            try:
                jobs.append(TaskJob.model_validate_json(file.read_text(encoding="utf-8")))
            except Exception:
                continue
        return sorted(jobs, key=lambda j: j.created_at, reverse=True)

    async def execute_job(self, job_id: str) -> TaskJob:
        """Executes a single job using the Autonomous AI Agent."""
        job = self.get_job(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")

        job.status = "RUNNING"
        self._save_job(job)

        agent = Agent(interactive=False)
        try:
            log = await agent.run(job.task)
            job.task_id = log.task_id
            job.summary = log.summary
            if log.final_state == AgentState.COMPLETED:
                job.status = "COMPLETED"
            else:
                job.status = "FAILED"
                job.error = log.summary
        except Exception as e:
            job.status = "FAILED"
            job.error = str(e)

        self._save_job(job)
        return job

    async def run_worker_loop(self):
        """Continuous background worker processing tasks from the queue."""
        self._running = True
        print(f"[*] Autonomous AI Worker running. Waiting for tasks in {self.job_store_dir}...")
        while self._running:
            try:
                job_id = await self._queue.get()
                print(f"[*] Processing job: {job_id}")
                await self.execute_job(job_id)
                self._queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[!] Worker exception: {e}")
                await asyncio.sleep(1)

    def stop(self):
        self._running = False


worker_service = WorkerService()

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(worker_service.run_worker_loop())
    except KeyboardInterrupt:
        print("\n[*] Worker terminated by user.")
