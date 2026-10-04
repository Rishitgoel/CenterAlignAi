from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AuditBlock(BaseModel):
    index: int
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    task_id: str
    action_type: str  # STATE_TRANSITION, TOOL_EXECUTION, ESCALATION_DECISION, VERIFICATION_RESULT
    payload: Dict[str, Any]
    previous_hash: str
    block_hash: str


class CryptographicAuditLedger:
    """Tamper-evident, hash-chained ledger storing immutable execution records for SOC2 compliance."""

    def __init__(self, ledger_file: Optional[str] = None):
        self.ledger_path = Path(ledger_file or "logs/compliance_audit_ledger.jsonl")
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        self._last_hash = self._get_last_hash()

    def _get_last_hash(self) -> str:
        if not self.ledger_path.exists():
            # Genesis block hash
            return "0000000000000000000000000000000000000000000000000000000000000000"

        last_hash = "0000000000000000000000000000000000000000000000000000000000000000"
        with open(self.ledger_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        record = json.loads(line)
                        last_hash = record.get("block_hash", last_hash)
                    except Exception:
                        pass
        return last_hash

    def _compute_hash(self, index: int, timestamp: str, task_id: str, action_type: str, payload_str: str, prev_hash: str) -> str:
        raw = f"{index}:{timestamp}:{task_id}:{action_type}:{payload_str}:{prev_hash}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def record_event(self, task_id: str, action_type: str, payload: Dict[str, Any]) -> AuditBlock:
        timestamp = datetime.now(timezone.utc).isoformat()
        current_index = self._count_records() + 1
        payload_str = json.dumps(payload, sort_keys=True)
        prev_hash = self._last_hash

        block_hash = self._compute_hash(
            index=current_index,
            timestamp=timestamp,
            task_id=task_id,
            action_type=action_type,
            payload_str=payload_str,
            prev_hash=prev_hash,
        )

        block = AuditBlock(
            index=current_index,
            timestamp=timestamp,
            task_id=task_id,
            action_type=action_type,
            payload=payload,
            previous_hash=prev_hash,
            block_hash=block_hash,
        )

        with open(self.ledger_path, "a", encoding="utf-8") as f:
            f.write(block.model_dump_json() + "\n")

        self._last_hash = block_hash
        return block

    def _count_records(self) -> int:
        if not self.ledger_path.exists():
            return 0
        with open(self.ledger_path, "r", encoding="utf-8") as f:
            return sum(1 for line in f if line.strip())

    def verify_ledger_integrity(self) -> Dict[str, Any]:
        """Validates the cryptographic chain of all recorded execution blocks."""
        if not self.ledger_path.exists():
            return {"valid": True, "blocks_verified": 0}

        expected_prev = "0000000000000000000000000000000000000000000000000000000000000000"
        blocks_checked = 0

        with open(self.ledger_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                block = json.loads(line)
                if block.get("previous_hash") != expected_prev:
                    return {
                        "valid": False,
                        "broken_at_index": block.get("index"),
                        "reason": "Previous hash mismatch",
                    }

                recomputed = self._compute_hash(
                    index=block.get("index"),
                    timestamp=block.get("timestamp"),
                    task_id=block.get("task_id"),
                    action_type=block.get("action_type"),
                    payload_str=json.dumps(block.get("payload"), sort_keys=True),
                    prev_hash=expected_prev,
                )

                if recomputed != block.get("block_hash"):
                    return {
                        "valid": False,
                        "broken_at_index": block.get("index"),
                        "reason": "Block hash signature corrupt",
                    }

                expected_prev = block.get("block_hash")
                blocks_checked += 1

        return {"valid": True, "blocks_verified": blocks_checked}


audit_ledger = CryptographicAuditLedger()
