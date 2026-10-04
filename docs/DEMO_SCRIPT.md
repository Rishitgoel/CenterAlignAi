# 🎙️ CentrAlign AI Demo Video Recording Script

> **Target Duration**: 3 minutes  
> **Tools Recommended**: OBS Studio, Loom, or Windows Game Bar (`Win + G`)  
> **Primary View**: Web Browser open to `http://127.0.0.1:8000/portal` (Optional side-by-side terminal with `python main.py ...`)

---

## [0:00 – 0:25] Introduction & The Problem Statement
- **Visual**: Show Web Portal at `http://127.0.0.1:8000/portal` with the new **AI Worker Command Center** at the top.
- **Narration**:
  > "Hi everyone! I'm presenting my submission for the CentrAlign AI Autonomous Task Worker challenge.
  > Today, corporate operators spend hours moving manually between emails, PDF invoices, and company web portals, entering data and hoping nothing broke.
  > I built a goal-driven autonomous AI employee that takes natural language requests and autonomously executes them across enterprise software—featuring closed-loop query-back verification, self-correcting error recovery, human governance, and tamper-evident cryptographic audit logs."

---

## [0:25 – 0:50] The Environment & In-App AI Command Center
- **Visual**: Highlight the **AI Command Bar** and **5 Quick Demo Scenario Pills** at the top of the portal.
- **Narration**:
  > "Rather than just a CLI tool, our portal features a live In-App AI Worker Command Center.
  > Operators can type freeform instructions, attach documents via the paperclip button, or click 1-click preset scenario pills.
  > The system adheres to CentrAlign's Google Sans typography and 5-stage pipeline design: Ingest, Extract, Policy Check, Mutate ERP, and Verify."

---

## [0:50 – 1:30] Scenario 1: One-Click Dispatch & Live Streaming Drawer
- **Visual**: Click the **⚡ Clean Invoice (Globex)** pill or type:
  `Process invoice demo/invoices/invoice_globex_002.json into the ERP system.`
  The Slide-over Execution Drawer opens from the right. Watch the live SSE step feed, extracted entity cards, and the Query-Back verification table pass. Notice the live Accounts Payable ledger and Kanban board automatically update in the background.
- **Narration**:
  > "Let's click the Clean Invoice scenario pill. 
  > Notice the slide-over execution drawer immediately opens and connects to our real-time Server-Sent Events stream.
  > We can watch the agent decompose the goal, run the document extractor with millisecond timing, and enter the invoice.
  > Watch the verification step: it queries the SQLite database to confirm the exact row was created, displays a cryptographic SHA-256 block hash from our audit ledger, and automatically refreshes our Kanban board and ledger in the background without a page reload."

---

## [1:30 – 2:05] Scenario 2: Dynamic PDF Intake on Demand ("Add this PDF")
- **Visual**: Click the **📄 Ingest Custom PDF (Interactive)** pill or type:
  `Add this PDF invoice into our ERP system.`
  The drawer opens and prompts: *"Document Attachment Required"*. Drag or select `demo/invoices/invoice_cyberdyne_005.pdf`.
  The agent auto-resumes, extracts with Gemini 3.8 Flash multimodal, and completes.
- **Narration**:
  > "What if an operator simply says: 'Add this PDF'?
  > Instead of failing, the agent detects the missing document and transitions to AWAITING INPUT.
  > It renders an interactive drag-and-drop dropzone directly inside the drawer.
  > We drop our PDF invoice: it uploads, auto-resumes the worker, and uses Google Gemini 3.8 Flash for multimodal document extraction—capturing line items, currency, and amounts zero-shot."

---

## [2:05 – 2:35] Scenario 3: In-Drawer Human-in-the-Loop Governance ($75k Spend)
- **Visual**: Click the **⚠️ High-Value Escalation ($75k)** pill.
  The drawer streams until reaching the Policy stage, displays the amber alert banner: *"Task Suspended: Human-in-the-Loop Approval Required"*, then click **"✓ Approve & Resume"**.
  The task completes and records the approval in the hash chain.
- **Narration**:
  > "Next, enterprise safety governance. This invoice is for $75,000, which exceeds our spend threshold of $10,000.
  > The agent transitions to ESCALATED, pauses execution, and presents an inline approval banner in the drawer.
  > The operator reviews the details and clicks 'Approve & Resume'. 
  > The worker safely continues, records the human authorization in the cryptographic ledger, and commits the transaction."

---

## [2:35 – 3:00] Conclusion & Automated Verification
- **Visual**: Show `pytest tests/test_scenarios.py` in terminal with all 12/12 scenarios passing.
- **Narration**:
  > "All 12 automated integration scenarios pass with 100% success—validating happy path processing, self-healing replanning, multimodal document extraction, API dispatch, real-time SSE streaming, dynamic PDF ingestion, and in-app HITL governance.
  > The solution is fully containerized, rigorously tested, and production-ready. Thank you!"
