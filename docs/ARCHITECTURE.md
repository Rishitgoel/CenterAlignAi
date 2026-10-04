# 🏛️ CentrAlign AI Task Worker: Architecture Deep Dive

## Overview

The CentrAlign AI Autonomous Task Worker is designed around **goal-directed autonomy**, **deterministic verification**, and **fail-safe governance**. Rather than delegating the entire reasoning and execution process to an unconstrained LLM loop, the system employs an explicit **hierarchical state machine** coupled with structured observation gates.

---

## 1. State Machine Dynamics

```
[IDLE] 
  │
  ▼
[UNDERSTANDING] 
  │
  ▼
[PLANNING] ◄──────────────────────────────────────────────┐
  │                                                       │
  ▼                                                       │
[EXECUTING]                                               │
  │                                                       │ (Adapt / Replan)
  ▼                                                       │
[OBSERVING] ─── (Failure) ───► [ADAPTING] ────────────────┤
  │                                                       │
  ├─── (Threshold Exceeded) ───► [ESCALATED] ─────────────┘
  │                                 │ (Approved)
  ▼ (Step OK)                       │
[VERIFYING]                         ▼ (Rejected)
  │                              [FAILED]
  ├─── (Checks Pass) ───► [COMPLETED]
  └─── (Checks Fail) ───► [FAILED]
```

### Key State Transitions

1. **`PLANNING`**: The Planner receives the user's natural language goal, the current contents of `WorkingMemory`, and the schema of all tools in the `ToolRegistry`. The planner outputs a `TaskPlan` containing atomic `PlannedStep` records with variable placeholders (e.g. `{{vendor_name}}`, `{{created_invoice_id}}`).
2. **`EXECUTING`**: The `Executor` evaluates the step, dynamically binds placeholders from discovered memory facts, and invokes the tool's `execute()` method.
3. **`OBSERVING`**: Rather than passing raw tool stdout back to an LLM, the `Observer` extracts structured facts, evaluates policy rules (e.g., spending limits), and classifies the outcome as `success`, `failure`, or `needs_escalation`.
4. **`ADAPTING`**: When a tool fails, the agent self-corrects by incrementing `retry_count`, feeding the error back to the `Planner`, and constructing an alternative plan (e.g. falling back from JSON parsing to regex text extraction).
5. **`VERIFYING`**: After all execution steps conclude, the `Verifier` independently reads back data from the system-of-record (FastAPI Mock ERP) and validates field parity.

---

## 2. Core Modules

| Module | Class | Responsibility |
|---|---|---|
| `agent/core.py` | `Agent` | Master state machine controller and event loop. Manages transitions, human prompts, and audit artifact generation. |
| `agent/planner.py` | `Planner` | LLM-based goal decomposition using Google Gemini 3.8 Flash with structured JSON output and heuristic fallback. |
| `agent/executor.py` | `Executor` | Safe tool invocation engine with variable interpolation. |
| `agent/observer.py` | `Observer` | Extracts state facts from tool outputs and triggers policy guardrails. |
| `agent/verifier.py` | `Verifier` | Queries external APIs and filesystem to verify task completion. |
| `agent/memory.py` | `WorkingMemory` | In-memory context and execution history tracking. |
| `mock_erp/app.py` | FastAPI Application | Simulates an enterprise ERP/CRM service with SQLite database and duplicate detection. |

---

## 3. The Query-Back Verification Pattern

A critical vulnerability in contemporary autonomous agent prototypes is **hallucinated success** — where an agent marks a task complete simply because a tool executed without throwing an unhandled exception.

In this prototype, we implement the **Query-Back Verification Pattern**:
1. When `erp_client` executes `create_invoice`, it records an invoice with ID `N`.
2. The `Observer` stores `created_invoice_id = N` in working memory.
3. The `Verifier` executes a distinct `GET /invoices/N` request against the ERP API.
4. The retrieved record is compared against the source data:
   - Does `vendor_name` match?
   - Does `amount` match within floating-point tolerance?
   - Does `invoice_number` match?
5. The task is only designated as `COMPLETED` if all verification assertions pass.
