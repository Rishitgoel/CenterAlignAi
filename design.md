# 🎨 CentrAlign AI — Design System & UI Specification (`design.md`)

> **Primary Layout & Pipeline Reference**: [21st-crm.vercel.app/opportunities](https://21st-crm.vercel.app/opportunities)  
> **Brand & AI Employee Philosophy Reference**: [raj.centralign.ai](https://raj.centralign.ai/)  
> **Typography Standard**: **Google Sans** applied everywhere across the entire interface.  
> **Platform**: CentrAlign AI Autonomous Enterprise Task Worker & Mock ERP System.

---

## 1. 📐 Design Philosophy & Aesthetic Foundation

This design system fuses the sleek, high-density CRM layout of **21st-CRM** with the warm, executive-grade AI Employee identity of **CentrAlign AI** (`raj.centralign.ai`):

### Core Pillars
1. **Uncompromising Typography**: **Google Sans** is the single typographic standard for all headings, labels, cards, buttons, and navigation, paired with **JetBrains Mono** for monetary amounts, system codes, and timestamps.
2. **"AI Employee" Persona ("CentrAlign Doesn't Assist. It Gets the Work Done.")**:
   - The interface is not merely a passive database viewer; it is an active autonomous workspace.
   - Includes the signature CentrAlign live workflow progress bar ("*Ask once. Watch it happen.*") visualizing real-time autonomous task execution across distinct stages:
     `Ingestion ➔ Extraction ➔ Policy Check ➔ System of Record Mutation ➔ Verification`.
3. **Warm Modern Minimalist Palette**:
   - Clean canvas with subtle warm tones inspired by CentrAlign (`#fcfbf9` / `#faf9f6`), balanced by rich ink-black primary elements (`#161412` / `#0a0a0a`), crisp 1px neutral borders (`#e8e5de` / `#e5e7eb`), and CentrAlign's signature warm amber accents (`#d97706` / `#b45309`).
4. **Information Density & Zero Visual Noise**:
   - Seamless two-column layout with a collapsible sidebar (~256px) and an expansive main workspace.
   - Standardized card anatomy featuring high-contrast primary labels, semantic icons (Building, Diamond, Calendar), and owner avatar pills.

---

## 2. 🔤 Typography & Font Specification

Google Sans is strictly enforced across all elements via global rules:

```css
@import url('https://fonts.googleapis.com/css2?family=Product+Sans:wght@400;700&family=Google+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');
@import url('https://fonts.cdnfonts.com/css/google-sans');

:root {
  --font-sans: 'Google Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
  --font-mono: 'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

* {
  font-family: var(--font-sans) !important;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

code, pre, .mono, .amount-val, .badge-mono, .metric-number {
  font-family: var(--font-mono) !important;
}
```

### Typographic Hierarchy

| Role | Font Size | Weight | Tracking | Purpose |
|---|---|---|---|---|
| **App Title & Brand** | `15px` (`0.9375rem`) | `700` | `-0.02em` | CentrAlign AI brand header & active page title |
| **Section Eyebrow** | `11px` (`0.6875rem`) | `600` | `+0.06em` | Uppercase sidebar section labels ("Records", "Chats", "Lists") |
| **Stage Column Title** | `13px` (`0.8125rem`) | `600` | `normal` | Pipeline stage names (`Qualification`, `Discovery`, etc.) |
| **Card Entity Title** | `13px` (`0.8125rem`) | `600` | `-0.01em` | Deal title / Task description / Invoice record |
| **Metadata Row Text** | `12px` (`0.75rem`) | `400` / `500` | `normal` | Company name, due date, assigned operator |
| **Currency Amount** | `13px` (`0.8125rem`) | `600` | `-0.02em` | Formatted financial values (`$38,000.00`) |
| **Column Aggregate** | `12px` (`0.75rem`) | `500` | `normal` | Pipeline column footer totals (`◇ $99,000.00`) |
| **Pills & Status Badges** | `11px` (`0.6875rem`) | `600` | `normal` | Stage counter badges, HITL pending badges |

---

## 3. 🎨 Color Palette & Design Tokens

### Core Theme Tokens
```css
:root {
  /* Canvas & Surfaces */
  --bg-app: #ffffff;
  --bg-canvas: #fcfbf9;
  --bg-sidebar: #faf9f6;
  --bg-sidebar-hover: #f3f1ec;
  --bg-card: #ffffff;
  --bg-card-hover: #fbfaf7;
  --bg-muted: #f4f2ed;

  /* CentrAlign Amber Accents */
  --amber-brand: #d97706;
  --amber-light: #fef3c7;
  --amber-text: #92400e;
  --amber-border: #fde68a;

  /* Ink Primary & Text */
  --text-primary: #161412;
  --text-secondary: #524f4a;
  --text-muted: #78746d;
  --text-subtle: #a6a197;

  /* Borders & Dividers */
  --border-sidebar: #eae6de;
  --border-card: #e5e2da;
  --border-card-hover: #cfcabb;
  --border-divider: #ede9e1;

  /* Radii */
  --radius-card: 12px;
  --radius-inner: 8px;
  --radius-control: 6px;
  --radius-pill: 9999px;

  /* Shadows */
  --shadow-card: 0 1px 2px 0 rgba(22, 20, 18, 0.04);
  --shadow-card-hover: 0 4px 12px 0 rgba(22, 20, 18, 0.06), 0 1px 3px 0 rgba(22, 20, 18, 0.04);
  --shadow-modal: 0 20px 25px -5px rgba(22, 20, 18, 0.1), 0 8px 10px -6px rgba(22, 20, 18, 0.1);
}
```

### 5-Stage Pipeline Status Colors (21st-CRM Schema)

| Stage | Dot Indicator | Badge Pill Background | Badge Text | Border Accent | System Semantic Meaning |
|---|---|---|---|---|---|
| **Qualification** | `#64748b` (Slate) | `#f1f5f9` | `#475569` | `#e2e8f0` | Natural language goal parsed & plan initialized |
| **Discovery** | `#3b82f6` (Blue) | `#eff6ff` | `#1d4ed8` | `#bfdbfe` | Line-item extraction & source verification |
| **Proposal** | `#f59e0b` (Amber) | `#fef3c7` | `#b45309` | `#fde68a` | ERP transaction prepared & policy threshold evaluated |
| **Negotiation** | `#a855f7` (Violet) | `#faf5ff` | `#7e22ce` | `#e9d5ff` | HITL approval gate active (for $10,000+ invoices) |
| **Won** | `#10b981` (Emerald) | `#ecfdf5` | `#047857` | `#a7f3d0` | Cryptographically verified in company ERP |

---

## 4. 📐 Interface Components & Layout

```
+--------------------------------------------------------------------------------------------------------------------+
|  CentrAlign AI — Autonomous Enterprise Workspace                                                                  |
+----------------------+---------------------------------------------------------------------------------------------+
|  [SIDEBAR - 256px]   |  [TOP HEADER BAR]                                                                           |
|  ❖ Alex Morgan  [⌕]  |  🤝 Opportunities  [Filter ▾] [⌕]             [Display ▾] [+ Create opportunity / Invoice] |
|  ------------------  +---------------------------------------------------------------------------------------------+
|  🕒 Up next          |  [CENTRALIGN LIVE OPERATOR STATUS RIBBON]                                                   |
|  ☑ Tasks             |  ● AI Employee: Active · "Ask once. Watch it happen." · 3 Ingested · 1 Pending Review        |
|                      +---------------------------------------------------------------------------------------------+
|  CHATS               |  [KANBAN PIPELINE BOARD - 5 STAGES]                                                         |
|  + New chat          |  ● Qualification(3)  ● Discovery(3)   ● Proposal(3)   ● Negotiation(2)   ✓ Won(2)           |
|  💬 Acme Ingestion   |  +----------------+  +--------------+ +-------------+ +----------------+ +----------------+ |
|  💬 High-Value Gate  |  | Lumenfield     |  | Halcyon      | | Brightpath  | | Cedarstone     | | Northbeam      | |
|                      |  | 🏢 Lumenfield  |  | 🏢 Halcyon   | | 🏢 Brightpath| | 🏢 Cedarstone   | | 🏢 Northbeam   | |
|  RECORDS             |  | ◇ $38,000.00   |  | ◇ $64,000.00 | | ◇ $96,000.00| | ◇ $215,000.00  | | ◇ $9,600.00    | |
|  🏢 Accounts         |  | 📅 Feb 1, 2027 |  | 📅 Dec 7,2026| | 📅 Nov 16   | | 📅 Nov 1, 2026 | | 📅 Sep 17, 2026| |
|  👥 Contacts         |  | (JR) Jamie R.  |  | (AM) Alex M. | | (JR) Jamie  | | (AM) Alex M.   | | (SN) Sofia N.  | |
|  🤝 Opportunities ★  |  +----------------+  +--------------+ +-------------+ +----------------+ +----------------+ |
|                      |  | + Create opp   |  | + Create opp | | + Create opp| | + Create opp   | | + Create opp   | |
|  LISTS               |  +----------------+  +--------------+ +-------------+ +----------------+ +----------------+ |
|  + New list          |  ◇ $99,000.00        ◇ $168,000.00    ◇ $292,500.00   ◇ $363,000.00      ◇ $28,100.00       |
|  ⭐ Champions        +---------------------------------------------------------------------------------------------+
|  🎯 Q4 commit        |  [BOTTOM TABS: 🗂 Pipeline Board | 🧾 Invoices Table | 🛡️ HITL Approval Queue | 💻 CLI Runner]  |
+----------------------+---------------------------------------------------------------------------------------------+
```

### Component Details
1. **Collapsible Left Sidebar**:
   - Header with Operator/User avatar pill (`AM` / `CA`), quick search button (`⌘K`), and sidebar collapse button (`«`).
   - Quick navigation: `Up next`, `Tasks`.
   - Section groups (`Chats`, `Records`, `Lists`) with clean hover states and active pill highlighting.
   - Footer with real-time system health dot: `● System Operational (127.0.0.1:8000)`.
2. **Main Workspace Top Bar**:
   - Breadcrumb title with Lucide icon (`lucide-handshake`).
   - `Filter` button with Funnel icon.
   - Search trigger.
   - `Display` view customization dropdown.
   - High-contrast primary action button: `+ Create opportunity` / `+ Record Invoice`.
3. **CentrAlign Live Operator Progress Banner** (Inspired by `raj.centralign.ai`):
   - Signature pill badge: `<span class="mkt-dot"></span> The Autonomous AI Task Worker`.
   - Compact 4-step progress visual: `Search ➔ Extract ➔ Verify ➔ Record`.
4. **Kanban Pipeline Board**:
   - 5 distinct stages with colored dot indicators, count pills, and `+` add buttons.
   - Rich opportunity cards with Title, Account/Vendor (`lucide-building-2`), Amount (`lucide-gem`), Due Date (`lucide-calendar`), and Owner Avatar (`JR`, `AM`, `SN`).
   - Bottom sum aggregates for each stage with diamond glyph (`◇`).
5. **Multi-View Tab Switcher**:
   - **Pipeline Board (Kanban)**: Visual deal & task stages.
   - **Invoices Ledger (Table)**: Tabular system-of-record view compatible with Playwright test automation (`#invoices-table`, `#invoices-tbody`).
   - **HITL Governance Approval Queue**: Escalations requiring human sign-off (`#hitl-count-badge`, `#hitl-queue-container`).
   - **Interactive CLI Scenario Runner**: Scenarios 1–3 copyable commands and live terminal status.
6. **Modal Dialog**:
   - Accessible, high-contrast modal dialog retaining all Playwright DOM selectors (`#open-invoice-modal-btn`, `#invoice-modal`, `#vendor-name-input`, `#invoice-number-input`, `#amount-input`, `#due-date-input`, `#notes-input`, `#submit-invoice-btn`, `#toast-banner`, `#toast-message`).

---

## 5. 🗺️ Detailed Phase-Wise Implementation Plan

### Phase 1: Foundation & Asset Setup
- **Objective**: Establish typography, CDN links, and CSS variables across all portal templates.
- **Tasks**:
  1. Link **Google Sans** and **JetBrains Mono** fonts.
  2. Define CSS variable design tokens for 21st-CRM layout and CentrAlign warm-amber accents.
  3. Set up responsive base layout with sidebar and main content grid.

### Phase 2: Sidebar & Header Shell Architecture
- **Objective**: Build the 21st-CRM navigation shell with CentrAlign AI Employee branding.
- **Tasks**:
  1. Build the collapsible left sidebar (`Alex Morgan` profile badge, `Up next`, `Tasks`, `Chats`, `Records`, `Lists`).
  2. Build top page header with `Filter`, search trigger, `Display` switcher, and `+ Create opportunity` button.
  3. Add the CentrAlign AI Employee live status indicator banner (`raj.centralign.ai` inspiration).

### Phase 3: 5-Stage Kanban Opportunity Pipeline
- **Objective**: Deliver the primary Kanban board layout identical to the user reference screenshot.
- **Tasks**:
  1. Render 5 columns: `Qualification`, `Discovery`, `Proposal`, `Negotiation`, `Won`.
  2. Implement card anatomy with Title, Building icon + Company, Diamond icon + Amount, Calendar icon + Date, and Owner Avatar pill.
  3. Implement column footer sum aggregates with dynamic calculation from active cards.
  4. Sync live database invoices from `/invoices` into pipeline stages alongside seeded reference deals.

### Phase 4: Multi-View Switching (Table, HITL Queue, CLI Runner)
- **Objective**: Maintain complete feature parity and test compatibility.
- **Tasks**:
  1. Implement seamless view toggling:
     - View 1: **Kanban Opportunities Board**
     - View 2: **Invoices Ledger Table** (with `#invoices-table`, `#invoices-tbody`)
     - View 3: **HITL Governance Approval Queue** (`#hitl-count-badge`, `#hitl-queue-container`)
     - View 4: **Scenario Runner & Terminal Console**
  2. Wire up live API calls (`/invoices`, `/vendors`, `/api/hitl/tasks`, `/api/hitl/tasks/{id}/resolve`).

### Phase 5: Modal Dialog & Playwright Verification
- **Objective**: Ensure the `+ Record Invoice` / `+ Create opportunity` modal works smoothly and passes all tests.
- **Tasks**:
  1. Style modal to match the sleek 21st-CRM aesthetic.
  2. Verify all element IDs (`#open-invoice-modal-btn`, `#vendor-name-input`, `#toast-banner`, etc.).
  3. Execute `pytest tests/test_scenarios.py` to confirm 9/9 tests pass (including Playwright Scenario 4).

### Phase 6: Polish, Micro-Interactions & Documentation
- **Objective**: Final aesthetic inspection and documentation update.
- **Tasks**:
  1. Add subtle hover transitions, modal backdrops, and toast banners.
  2. Update `mock_erp/app.py` root route (`/`) and `/portal` route.
  3. Verify visual alignment with screenshot and reference URLs.
