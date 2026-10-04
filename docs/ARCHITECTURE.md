# 🏛️ CentrAlign AI Task Worker: Architecture Deep Dive

## Overview

The CentrAlign AI Autonomous Task Worker is designed around **goal-directed autonomy**, **deterministic verification**, **fail-safe governance**, and **production enterprise resilience**. Rather than delegating reasoning and execution to an unconstrained, non-deterministic LLM loop, the system employs an explicit **hierarchical state machine** coupled with structured observation gates, cryptographic audit trails, and multi-interface computer tooling.

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
[OBSERVING] ─── (Failure / Syntax Broken) ───► [ADAPTING]─┤
  │                                                       │
  ├─── (Spend Threshold Exceeded) ───► [ESCALATED] ───────┘
  │                                      │ (Approved via Web/CLI)
  ▼ (Step OK)                            │
[VERIFYING]                              ▼ (Rejected)
  │                                   [FAILED]
  ├─── (Multi-Check Pass) ───► [COMPLETED] ───► (Cryptographic Block Appended)
  └─── (Discrepancy)      ───► [FAILED]
```

### Key State Transitions

1. **`PLANNING`**: The Planner receives the user's natural language goal, the current contents of `WorkingMemory`, and the registered tools in `ToolRegistry` (including static tools and dynamically ingested OpenAPI endpoints). The planner outputs a `TaskPlan` containing atomic `PlannedStep` records with dynamic variable placeholders (e.g. `{{vendor_name}}`, `{{created_invoice_id}}`).
2. **`EXECUTING`**: The `Executor` evaluates the step, dynamically binds placeholders from discovered memory facts, and invokes the tool's `execute()` method.
3. **`OBSERVING`**: Rather than passing raw tool stdout back to an LLM, the `Observer` extracts structured facts, evaluates policy rules (e.g., spending limits), and classifies the outcome as `success`, `failure`, or `needs_escalation`.
4. **`ADAPTING`**: When a tool fails (e.g. malformed JSON, changed HTML selector), the agent self-corrects by incrementing `retry_count`, feeding the error back to the `Planner` or `self_healing` module, and constructing an alternative plan.
5. **`ESCALATED`**: When policy thresholds are reached ($10,000 spend limit), the task suspends into persistent disk storage (`logs/suspended_tasks/<id>.json`) and registers in the Web Operator Approval Queue (`/portal`), allowing asynchronous human review.
6. **`VERIFYING`**: After all execution steps conclude, the `Verifier` independently reads back data from the system-of-record (FastAPI Mock ERP), asserts visual page evidence, and validates field parity.
7. **`COMPLETED`**: Records an immutable SHA-256 block into the cryptographic compliance ledger and outputs structured JSON evidence.

---

## 2. Enterprise Core Modules

| Module | Class / Component | Responsibility |
|---|---|---|
| `agent/core.py` | `Agent` | Master state machine controller and event loop. Coordinates planning, execution, verification, and audit ledger recording. |
| `agent/planner.py` | `Planner` | Dual planning engine: Google Gemini 3.8 Flash via `google-genai` SDK with deterministic heuristic fallback. |
| `agent/executor.py` | `Executor` | Safe tool invocation engine with dynamic variable interpolation. |
| `agent/observer.py` | `Observer` | Extracts state facts from tool outputs and triggers policy guardrails. |
| `agent/verifier.py` | `Verifier` | Multi-layer verification: database read-back, screenshot verification, and disk report checks. |
| `agent/hitl_manager.py` | `HITLManager` | Asynchronous task suspension, resume handling, and web queue integration. |
| `agent/self_healing.py` | `SelfHealingSelector` | Heuristic and semantic selector fallback for altered web UIs. |
| `security/audit_ledger.py` | `CryptographicAuditLedger` | SHA-256 merkle-chained append-only compliance ledger with tamper detection. |
| `security/credential_vault.py` | `CredentialVault` | Secret credential storage and runtime redaction filter preventing leaks. |
| `infrastructure/worker.py` | `WorkerService` | Durable asynchronous task job runner and queue manager. |
| `benchmarks/eval_suite.py` | `BenchmarkRunner` | Automated benchmark evaluating autonomy, adaptation, and verification. |
| `mock_erp/app.py` | FastAPI Application | Enterprise ERP/CRM backend, Web Portal (`/portal`), and HITL webhook endpoints. |

---

## 3. The Query-Back Verification Pattern

A critical vulnerability in autonomous agents is **hallucinated success** — where an agent marks a task complete simply because a tool returned without raising an exception.

In this system, we implement the **Query-Back Verification Pattern**:
1. When `erp_client` executes `create_invoice`, it records an invoice with ID `N`.
2. The `Observer` stores `created_invoice_id = N` in working memory.
3. The `Verifier` executes an independent `GET /invoices/N` request against the ERP API.
4. The retrieved record is compared against the source data:
   - Does `vendor_name` match?
   - Does `amount` match within floating-point tolerance?
   - Does `invoice_number` match?
5. The task is only designated as `COMPLETED` if all verification assertions pass.

---

## 4. Multi-Interface Tool Layer

The agent does not rely on a single execution method:
1. **Headless Browser (`browser_operator.py`)**: Automates Playwright Chromium to interact with web forms, extract data tables, and capture visual screenshot proof.
2. **Multimodal Document Extractor (`document_extractor.py`)**: Ingests PDFs, images, and raw `.eml` emails using confidence-scored heuristics.
3. **Dynamic Zero-Code OpenAPI Ingestion (`openapi_loader.py`)**: Reads arbitrary OpenAPI/Swagger schemas and registers callable tools at runtime without writing code.
4. **Structured APIs (`erp_client.py`)**: Interacts with REST backends using typed schemas.
