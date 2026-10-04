# 🎙️ CentrAlign AI Demo Video Recording Script

> **Target Duration**: 2 minutes 45 seconds  
> **Tools Recommended**: OBS Studio, Loom, or Windows Game Bar (`Win + G`)  
> **Layout**: Two side-by-side windows:
> - **Left Window**: Web Browser open to `http://127.0.0.1:8000/portal`
> - **Right Window**: Terminal with Agent CLI (`python main.py ...`)

---

## [0:00 – 0:25] Introduction & The Problem Statement
- **Visual**: Show `README.md` and Web Portal at `http://127.0.0.1:8000/portal`.
- **Narration**:
  > "Hi everyone, I'm presenting my submission for the CentrAlign AI Autonomous Task Worker challenge. 
  > Today, corporate operators spend hours moving manually between emails, PDF invoices, and company web portals, entering data and hoping nothing broke. 
  > I built a goal-driven autonomous AI worker that takes a high-level natural language request and autonomously executes it using computers—complete with closed-loop verification, self-correcting error recovery, human governance, and tamper-evident cryptographic audit logs."

---

## [0:25 – 0:50] The Environment & Architecture
- **Visual**: Show the Web Portal on the left (`http://127.0.0.1:8000/portal`) with the live Accounts Payable ledger and Approval Queue.
- **Narration**:
  > "On the left is our company ERP Web Portal. It shows our live database of accounts payable and a pending Human-in-the-Loop approval queue. 
  > The agent architecture enforces an 8-state machine: Understand, Plan, Execute, Observe, Adapt, and Verify. 
  > Crucially, it doesn't just use APIs—it can operate headless browsers with Playwright, parse raw PDFs and emails, and self-heal when things break."

---

## [0:50 – 1:30] Scenario 1: Autonomous Browser & System Verification
- **Visual**: Run in terminal:
  ```bash
  python main.py "Open the company web portal and submit the invoice for Stark Industries, invoice INV-WEB-770, amount 4200.00, due 2026-11-15."
  ```
  Watch the terminal output and refresh the browser portal to see the new row instantly appear.
- **Narration**:
  > "Let's give the agent a natural language instruction to open the web portal and enter an invoice. 
  > The agent decomposes the goal, launches Playwright Chromium, fills the form modal, and captures a screenshot. 
  > Notice the verification step: rather than assuming success, it performs an independent query-back check against the database to prove the row was created, writes a completion report, and records a cryptographic block in our SOC2 audit ledger."

---

## [1:30 – 2:00] Scenario 2: Autonomous Error Recovery & Self-Healing
- **Visual**: Run in terminal:
  ```bash
  python main.py "Process invoice demo/invoices/invoice_malformed_003.json into the ERP system."
  ```
- **Narration**:
  > "Now, an intentional failure case. This invoice contains broken, malformed JSON syntax. 
  > When Step 1 runs, the standard parser fails. 
  > Instead of crashing, the agent enters the ADAPTING state. It analyzes the failure and dynamically replans using plain-text regex heuristic fallbacks. 
  > It recovers the invoice details for Initech, completes the ERP entry, and verifies state—achieving 100% autonomous self-correction."

---

## [2:00 – 2:30] Scenario 3: Human-in-the-Loop Governance & Web Queue
- **Visual**: Run in terminal:
  ```bash
  python main.py "Process invoice demo/invoices/invoice_highvalue_004.json into our ERP system."
  ```
  Show the terminal pausing at the human approval gate, and show the pending task in the Web Portal at `http://127.0.0.1:8000/portal`.
- **Narration**:
  > "Finally, enterprise governance. This invoice is for $75,000, which exceeds our safety threshold of $10,000. 
  > The agent transitions to ESCALATED, suspends execution to disk, and pushes an authorization request to the operator queue on our web portal. 
  > Once approved, it safely resumes and records the decision in the immutable hash chain."

---

## [2:30 – 2:45] Conclusion & Code Quality
- **Visual**: Show `pytest tests/ -v` (9/9 passed) or the benchmarks report (`python -m benchmarks.eval_suite`).
- **Narration**:
  > "All 9 automated integration scenarios pass with 100% benchmark success. 
  > The solution is fully containerized with Docker, well-documented, and ready for production. Thank you!"
