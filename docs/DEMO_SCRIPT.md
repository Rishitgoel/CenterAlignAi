# 🎙️ CentrAlign AI Demo Video Recording Script

> **Target Duration**: 2 minutes 30 seconds  
> **Tools Recommended**: OBS Studio or Windows Game Bar (`Win + G`)  
> **Layout**: Two side-by-side terminal windows (Left: Mock ERP Server, Right: Agent CLI)

---

## [0:00 – 0:25] Introduction & Problem Formulation
- **Visual**: Show project README on screen or title card.
- **Narration**:
  > "Hi everyone, I'm presenting my submission for the CentrAlign AI Autonomous Task Worker challenge. 
  > Knowledge workers spend countless hours reading files, entering data across internal business tools, and checking if tasks were completed correctly. 
  > I built a goal-driven autonomous agent that takes natural language requests and executes them with closed-loop verification, automatic error recovery, and human governance."

---

## [0:25 – 0:50] Architecture & Setup
- **Visual**: Show Left terminal with `python main.py server` running, and Right terminal ready.
- **Narration**:
  > "On the left, I have a local FastAPI enterprise ERP server with SQLite persistence. 
  > On the right is our Autonomous Worker CLI. 
  > The agent architecture strictly enforces an 8-stage state machine: Understand, Plan, Execute, Observe, Adapt, and Verify. 
  > Let's look at three quick scenarios."

---

## [0:50 – 1:25] Scenario 1: Happy Path & Deterministic Verification
- **Visual**: In Right terminal, run:
  ```bash
  python main.py run --task "Find the latest invoice from Acme Corp in demo/invoices/invoice_acme_001.json, extract the details, enter it into our ERP system, and verify completion."
  ```
- **Narration**:
  > "First, the happy path. The agent parses the goal, generates a multi-step plan, reads the JSON invoice, and calls our ERP API. 
  > Notice the critical step at the end: **State Verification**. 
  > Rather than hallucinating success, the agent queries the ERP database back, validates that record ID 3 matches the vendor and amount, and writes an audit report to disk with full JSON evidence."

---

## [1:25 – 1:55] Scenario 2: Autonomous Error Recovery (Self-Correction)
- **Visual**: In Right terminal, run:
  ```bash
  python main.py run --task "Process the invoice from demo/invoices/invoice_malformed_003.json and record it into our ERP system."
  ```
- **Narration**:
  > "Now, an intentional failure case. This invoice has broken syntax with missing JSON quotes. 
  > When Step 1 runs, the parser fails with a JSONDecodeError. 
  > Watch the state transition: the agent detects the failure, enters the ADAPTING state, and replans using a plain-text regex heuristic fallback. 
  > It recovers the invoice details for Initech, completes the ERP entry, and succeeds without human intervention."

---

## [1:55 – 2:20] Scenario 3: Human-in-the-Loop Governance Escalation
- **Visual**: In Right terminal, run:
  ```bash
  python main.py run --task "Process the high-value vendor invoice from demo/invoices/invoice_highvalue_004.json into our ERP system."
  ```
- **Narration**:
  > "Finally, safety governance. This invoice from Stark Industries is for $75,000, which exceeds our autonomous threshold of $10,000. 
  > The agent transitions to ESCALATED, halts, and presents an interactive approval gate. 
  > When I type 'y' to authorize, it completes the entry safely. If rejected, it aborts immediately."

---

## [2:20 – 2:30] Wrap-up & Code Quality
- **Visual**: Show `logs/` directory with structured JSON execution logs.
- **Narration**:
  > "Every run generates a structured JSON evidence trail capturing state transitions, tool timing, and database verification proof. 
  > The code is modular, well-tested, and ready to scale. Thanks for watching!"
