from pathlib import Path
import time
from typing import Any, Dict, Optional
from config import settings
from tools.base import Tool, ToolResult


class BrowserOperatorTool(Tool):
    name: str = "browser_operator"
    description: str = (
        "Automates interactive browser sessions using Playwright Chromium. "
        "Allows navigating web portals, opening modals, filling form fields, "
        "clicking submission buttons, extracting live DOM tables, and capturing screenshots for verification."
    )
    parameters_schema: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["enter_invoice_form", "extract_table", "take_screenshot", "move_opportunity_stage", "switch_portal_view", "filter_opportunities", "inspect_opportunity"],
                "description": "Browser automation action to execute.",
            },
            "url": {
                "type": "string",
                "default": "http://127.0.0.1:8000/portal",
                "description": "Web portal URL.",
            },
            "form_data": {
                "type": "object",
                "description": "Payload required for 'enter_invoice_form': vendor_name, invoice_number, amount, due_date, notes.",
            },
            "company": {
                "type": "string",
                "description": "Target company name for 'move_opportunity_stage'.",
            },
            "target_stage": {
                "type": "string",
                "enum": ["qualification", "discovery", "proposal", "negotiation", "won"],
                "description": "Target pipeline stage for 'move_opportunity_stage'.",
            },
            "headless": {
                "type": "boolean",
                "default": True,
                "description": "Whether to run browser in headless mode.",
            },
            "screenshot_path": {
                "type": "string",
                "default": "logs/portal_submission_screenshot.png",
                "description": "Target screenshot destination.",
            },
        },
        "required": ["action"],
    }

    async def execute(self, params: Dict[str, Any]) -> ToolResult:
        action = params.get("action")
        url = params.get("url")
        if not url or "127.0.0.1:8000" in url or "localhost:8000" in url:
            url = f"{settings.erp_base_url}/portal"
        headless = params.get("headless", True)

        try:
            from playwright.async_api import async_playwright
        except ImportError:
            return ToolResult(
                success=False,
                error="Playwright is not installed. Run 'pip install playwright && python -m playwright install chromium'",
            )

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=headless)
                context = await browser.new_context(viewport={"width": 1280, "height": 800})
                page = await context.new_page()

                # Navigate to the company portal
                await page.goto(url, wait_until="networkidle", timeout=15000)

                if action == "enter_invoice_form":
                    form_data = params.get("form_data") or {}
                    return await self._enter_invoice_form(page, form_data, params)

                elif action == "move_opportunity_stage":
                    company = params.get("company") or params.get("vendor_name") or "Tidewater"
                    target_stage = params.get("target_stage") or params.get("stage") or "won"
                    return await self._move_opportunity_stage(page, company, target_stage, params, browser)

                elif action == "extract_table":
                    return await self._extract_table(page)

                elif action == "switch_portal_view":
                    target_view = params.get("target_view", "kanban")
                    return await self._switch_portal_view(page, target_view, params, browser)

                elif action == "filter_opportunities":
                    return await self._filter_opportunities(page, params, browser)

                elif action == "inspect_opportunity":
                    company = params.get("company") or params.get("vendor_name") or "Tidewater"
                    return await self._inspect_opportunity(page, company, params, browser)

                elif action == "take_screenshot":
                    shot_path = params.get("screenshot_path", "logs/portal_screenshot.png")
                    Path(shot_path).parent.mkdir(parents=True, exist_ok=True)
                    await page.screenshot(path=shot_path, full_page=True)
                    await browser.close()
                    return ToolResult(
                        success=True,
                        data={"screenshot_path": shot_path},
                        metadata={"action": "take_screenshot"},
                    )

                else:
                    await browser.close()
                    return ToolResult(
                        success=False,
                        error=f"Unsupported browser action: '{action}'",
                    )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Browser automation failed: {str(e)}",
            )

    async def _enter_invoice_form(self, page, form_data: Dict[str, Any], params: Dict[str, Any]) -> ToolResult:
        vendor_name = form_data.get("vendor_name", "")
        invoice_number = form_data.get("invoice_number", "")
        amount = str(form_data.get("amount", ""))
        due_date = str(form_data.get("due_date", "2025-01-30"))
        notes = form_data.get("notes", "Automated entry via CentrAlign Browser Worker")

        if not vendor_name or not invoice_number:
            return ToolResult(
                success=False,
                error="enter_invoice_form requires at least 'vendor_name' and 'invoice_number' in form_data",
            )

        # 1. Click button to open the modal
        modal_btn = page.locator("#open-invoice-modal-btn")
        await modal_btn.wait_for(state="visible", timeout=5000)
        await modal_btn.click()

        # 2. Fill form fields using accessibility & ID selectors
        await page.wait_for_selector("#invoice-modal:not(.hidden)", timeout=5000)
        await page.fill("#vendor-name-input", str(vendor_name))
        await page.fill("#invoice-number-input", str(invoice_number))
        await page.fill("#amount-input", amount)
        await page.fill("#due-date-input", due_date)
        await page.fill("#notes-input", notes)

        # 3. Submit form
        await page.click("#submit-invoice-btn")

        # 4. Wait for response & inspect feedback toast banner
        toast_selector = "#toast-banner:not(.hidden)"
        await page.wait_for_selector(toast_selector, timeout=8000)
        toast_text = (await page.inner_text("#toast-message")).strip()

        # Capture evidence screenshot of submitted state
        shot_path = params.get("screenshot_path", "logs/portal_submission_screenshot.png")
        Path(shot_path).parent.mkdir(parents=True, exist_ok=True)
        await page.screenshot(path=shot_path, full_page=True)

        is_conflict = "conflict" in toast_text.lower() or "already exists" in toast_text.lower()
        is_success = "successfully registered" in toast_text.lower()

        if is_success:
            return ToolResult(
                success=True,
                data={
                    "ui_status": "submitted",
                    "toast_feedback": toast_text,
                    "screenshot_path": shot_path,
                    "vendor_name": vendor_name,
                    "invoice_number": invoice_number,
                    "amount": amount,
                },
                metadata={
                    "browser": "chromium",
                    "url": page.url,
                    "screenshot": shot_path,
                },
            )
        elif is_conflict:
            return ToolResult(
                success=False,
                error=f"ConflictError (409 via UI): {toast_text}",
                metadata={"status_code": 409, "screenshot": shot_path},
            )
        else:
            return ToolResult(
                success=False,
                error=f"Form submission error on UI: {toast_text}",
                metadata={"screenshot": shot_path},
            )

    async def _extract_table(self, page) -> ToolResult:
        rows = await page.eval_on_selector_all(
            "#invoices-tbody tr",
            """elements => elements.map(el => {
                const tds = el.querySelectorAll('td');
                return {
                    id: tds[0] ? tds[0].innerText.trim() : '',
                    vendor: tds[1] ? tds[1].innerText.trim() : '',
                    invoice_number: tds[2] ? tds[2].innerText.trim() : '',
                    amount: tds[3] ? tds[3].innerText.trim() : '',
                    due_date: tds[4] ? tds[4].innerText.trim() : '',
                    status: tds[5] ? tds[5].innerText.trim() : ''
                };
            })""",
        )
        return ToolResult(
            success=True,
            data={"rows": rows, "count": len(rows)},
            metadata={"row_count": len(rows)},
        )

    async def _move_opportunity_stage(
        self, page, company: str, target_stage: str, params: Dict[str, Any], browser
    ) -> ToolResult:
        js_code = """
        ({ company, targetStage }) => {
            const query = company.toLowerCase();
            let targetId = null;
            let matchedCard = null;

            if (typeof dynamicCards !== 'undefined') {
                for (const card of dynamicCards) {
                    if ((card.company && card.company.toLowerCase().includes(query)) ||
                        (card.title && card.title.toLowerCase().includes(query))) {
                        targetId = card.id;
                        matchedCard = card;
                        break;
                    }
                }
            }

            if (!targetId && typeof liveInvoices !== 'undefined') {
                for (const inv of liveInvoices) {
                    if (inv.vendor_name && inv.vendor_name.toLowerCase().includes(query)) {
                        targetId = `erp-${inv.id}`;
                        matchedCard = { id: targetId, company: inv.vendor_name, amount: inv.amount, title: inv.vendor_name };
                        break;
                    }
                }
            }

            if (targetId && typeof moveCardToStage === 'function') {
                moveCardToStage(targetId, targetStage);
                return {
                    found: true,
                    card_id: targetId,
                    company: matchedCard.company || matchedCard.title,
                    amount: matchedCard.amount,
                    new_stage: targetStage
                };
            }
            return { found: false };
        }
        """
        res = await page.evaluate(js_code, {"company": company, "targetStage": target_stage})
        shot_path = params.get("screenshot_path", "logs/portal_stage_move_screenshot.png")
        Path(shot_path).parent.mkdir(parents=True, exist_ok=True)
        await page.screenshot(path=shot_path)
        await browser.close()

        if res.get("found"):
            return ToolResult(
                success=True,
                data={
                    "card_id": res.get("card_id"),
                    "company": res.get("company"),
                    "amount": res.get("amount"),
                    "new_stage": res.get("new_stage"),
                    "screenshot_path": shot_path,
                    "ui_status": f"Moved '{company}' to {target_stage.title()}",
                },
                metadata={
                    "action": "move_opportunity_stage",
                    "screenshot_path": shot_path,
                    "target_stage": target_stage,
                },
            )
        else:
            return ToolResult(
                success=False,
                error=f"No opportunity card found matching company '{company}' in Kanban pipeline.",
            )

    async def _switch_portal_view(self, page, target_view: str, params: Dict[str, Any], browser) -> ToolResult:
        js = "view => { if (typeof switchTab === 'function') { switchTab(view); return true; } return false; }"
        ok = await page.evaluate(js, target_view)
        shot_path = params.get("screenshot_path", "logs/portal_view_switch_screenshot.png")
        Path(shot_path).parent.mkdir(parents=True, exist_ok=True)
        await page.screenshot(path=shot_path)
        await browser.close()

        return ToolResult(
            success=ok,
            data={"target_view": target_view, "screenshot_path": shot_path},
            metadata={"action": "switch_portal_view", "target_view": target_view},
        )

    async def _filter_opportunities(self, page, params: Dict[str, Any], browser) -> ToolResult:
        js = """
        filters => {
            if (filters.min_amount !== undefined && typeof setAmountFilter === 'function') {
                setAmountFilter(filters.min_amount);
            }
            if (filters.stage && document.getElementById('stage-filter')) {
                document.getElementById('stage-filter').value = filters.stage;
                if (typeof filterOpportunities === 'function') filterOpportunities();
            }
            if (filters.search && document.getElementById('search-input')) {
                document.getElementById('search-input').value = filters.search;
                if (typeof filterOpportunities === 'function') filterOpportunities();
            }
            return { applied: true };
        }
        """
        res = await page.evaluate(js, params)
        shot_path = params.get("screenshot_path", "logs/portal_filter_screenshot.png")
        Path(shot_path).parent.mkdir(parents=True, exist_ok=True)
        await page.screenshot(path=shot_path)
        await browser.close()

        return ToolResult(
            success=True,
            data={"filters": params, "screenshot_path": shot_path},
            metadata={"action": "filter_opportunities"},
        )

    async def _inspect_opportunity(self, page, company: str, params: Dict[str, Any], browser) -> ToolResult:
        js = """
        comp => {
            const co = (comp || '').toLowerCase();
            const matched = dynamicCards.find(c => 
                (c.company && c.company.toLowerCase().includes(co)) || 
                (c.title && c.title.toLowerCase().includes(co))
            );
            if (matched && typeof inspectCard === 'function') {
                inspectCard(matched.id);
                return { found: true, id: matched.id, company: matched.company, amount: matched.amount };
            }
            return { found: false };
        }
        """
        res = await page.evaluate(js, company)
        shot_path = params.get("screenshot_path", "logs/portal_inspect_screenshot.png")
        Path(shot_path).parent.mkdir(parents=True, exist_ok=True)
        await page.screenshot(path=shot_path)
        await browser.close()

        if res.get("found"):
            return ToolResult(
                success=True,
                data={**res, "screenshot_path": shot_path},
                metadata={"action": "inspect_opportunity", "company": company},
            )
        return ToolResult(
            success=False,
            error=f"No opportunity card found matching company '{company}' for inspection.",
        )
