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
                "enum": ["enter_invoice_form", "extract_table", "take_screenshot"],
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
        url = params.get("url") or f"{settings.erp_base_url}/portal"
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

                elif action == "extract_table":
                    return await self._extract_table(page)

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
