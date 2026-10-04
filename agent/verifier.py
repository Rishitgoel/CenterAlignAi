from pathlib import Path
from typing import List
from agent.memory import WorkingMemory
from agent.models import TaskPlan, VerificationCheck, VerificationResult
from tools.registry import ToolRegistry


class Verifier:
    def __init__(self, registry: ToolRegistry):
        self.registry = registry

    async def verify(self, plan: TaskPlan, memory: WorkingMemory) -> VerificationResult:
        checks: List[VerificationCheck] = []
        discrepancies: List[str] = []
        evidence: dict = {}

        # 1. Verification of ERP invoice creation (State Query Verification)
        created_id = memory.get_fact("created_invoice_id")
        expected_vendor = memory.get_fact("vendor_name")
        expected_amount = memory.get_fact("amount")
        expected_inv_num = memory.get_fact("invoice_number")

        erp_tool = self.registry.get("erp_client")
        if created_id is not None and erp_tool:
            erp_check_res = await erp_tool.execute({
                "action": "get_invoice",
                "invoice_id": created_id,
            })

            if erp_check_res.success and isinstance(erp_check_res.data, dict):
                record = erp_check_res.data
                evidence["erp_record"] = record

                # Vendor match
                actual_vendor = record.get("vendor_name")
                if expected_vendor is not None:
                    vendor_ok = (str(actual_vendor).lower() == str(expected_vendor).lower())
                    checks.append(
                        VerificationCheck(
                            target="ERP Vendor Name Match",
                            expected=expected_vendor,
                            actual=actual_vendor,
                            matched=vendor_ok,
                        )
                    )
                    if not vendor_ok:
                        discrepancies.append(f"Vendor mismatch: Expected {expected_vendor}, found {actual_vendor}")

                # Amount match
                actual_amount = float(record.get("amount", 0.0))
                if expected_amount is not None:
                    amount_ok = (abs(actual_amount - float(expected_amount)) < 0.01)
                    checks.append(
                        VerificationCheck(
                            target="ERP Amount Match",
                            expected=expected_amount,
                            actual=actual_amount,
                            matched=amount_ok,
                        )
                    )
                    if not amount_ok:
                        discrepancies.append(f"Amount mismatch: Expected {expected_amount}, found {actual_amount}")

                # Invoice number match
                actual_num = record.get("invoice_number")
                if expected_inv_num is not None:
                    num_ok = (str(actual_num) == str(expected_inv_num))
                    checks.append(
                        VerificationCheck(
                            target="ERP Invoice Number Match",
                            expected=expected_inv_num,
                            actual=actual_num,
                            matched=num_ok,
                        )
                    )
                    if not num_ok:
                        discrepancies.append(f"Invoice number mismatch: Expected {expected_inv_num}, found {actual_num}")

                # Status match if an update occurred
                expected_status = memory.get_fact("erp_invoice_status")
                if expected_status:
                    actual_status = record.get("status")
                    st_ok = (str(actual_status).lower() == str(expected_status).lower())
                    checks.append(
                        VerificationCheck(
                            target="ERP Invoice Status Match",
                            expected=expected_status,
                            actual=actual_status,
                            matched=st_ok,
                        )
                    )
                    if not st_ok:
                        discrepancies.append(f"Status mismatch: Expected {expected_status}, found {actual_status}")
            else:
                checks.append(
                    VerificationCheck(
                        target="ERP Record Exists",
                        expected=f"Invoice ID {created_id} in database",
                        actual=erp_check_res.error or "Not found",
                        matched=False,
                    )
                )
                discrepancies.append(f"Failed to query created invoice ID {created_id} from ERP")

        # 1B. Verification of Invoice Deletion
        deleted_id = memory.get_fact("deleted_invoice_id")
        if deleted_id is not None and erp_tool:
            del_check = await erp_tool.execute({
                "action": "get_invoice",
                "invoice_id": deleted_id,
            })
            is_deleted = not del_check.success
            checks.append(
                VerificationCheck(
                    target="ERP Invoice Deletion Confirmed",
                    expected=f"Invoice ID {deleted_id} deleted (Not in DB)",
                    actual="Deleted (404 Not Found)" if is_deleted else "Still exists in DB",
                    matched=is_deleted,
                )
            )
            if not is_deleted:
                discrepancies.append(f"Invoice ID {deleted_id} was expected to be deleted but still exists in ERP.")

        # 2. Verification of Report Generation
        report_path = memory.get_fact("report_file_path")
        if report_path:
            p = Path(report_path)
            file_exists = p.exists() and p.stat().st_size > 0
            checks.append(
                VerificationCheck(
                    target="Completion Report File Written",
                    expected=f"Existing non-empty file at {report_path}",
                    actual="Exists on disk" if file_exists else "File not found",
                    matched=file_exists,
                )
            )
            if not file_exists:
                discrepancies.append(f"Report file {report_path} was not verified on disk.")
            else:
                evidence["report_content"] = p.read_text(encoding="utf-8")

        # 3. Verification of Browser Screenshot Evidence
        shot_path = memory.get_fact("browser_screenshot_path")
        if shot_path:
            sp = Path(shot_path)
            shot_exists = sp.exists() and sp.stat().st_size > 0
            checks.append(
                VerificationCheck(
                    target="Browser UI Screenshot Evidence Captured",
                    expected=f"Screenshot image file at {shot_path}",
                    actual=f"Captured ({sp.stat().st_size} bytes)" if shot_exists else "Screenshot not found",
                    matched=shot_exists,
                )
            )
            if not shot_exists:
                discrepancies.append(f"Browser UI screenshot {shot_path} was not verified.")
            else:
                evidence["screenshot_path"] = str(sp)

        # 4. Fallback search verification if created via browser directly without returned ID
        if created_id is None and expected_inv_num:
            search_res = await erp_tool.execute({
                "action": "search_invoices",
                "invoice_number": expected_inv_num,
            })
            if search_res.success and isinstance(search_res.data, list) and len(search_res.data) > 0:
                record = search_res.data[0]
                evidence["erp_record"] = record
                memory.add_fact("created_invoice_id", record.get("id"))
                checks.append(
                    VerificationCheck(
                        target="Browser UI Form Submitted into ERP DB",
                        expected=f"Invoice #{expected_inv_num} registered in ERP",
                        actual=f"Found Record #{record.get('id')} ({record.get('vendor_name')})",
                        matched=True,
                    )
                )

        # 5. Fallback verification: if no specific artifact targets applied, assert all execution steps succeeded
        if len(checks) == 0:
            all_steps_ok = all(s.success for s in memory.executed_steps) if memory.executed_steps else True
            checks.append(
                VerificationCheck(
                    target="All Plan Steps Executed Successfully",
                    expected="All steps succeeded",
                    actual="All steps succeeded" if all_steps_ok else "One or more steps failed",
                    matched=all_steps_ok,
                )
            )
            if not all_steps_ok:
                discrepancies.append("One or more planned steps failed during task execution.")

        all_passed = len(checks) > 0 and all(c.matched for c in checks) and len(discrepancies) == 0

        return VerificationResult(
            passed=all_passed,
            checks=checks,
            evidence=evidence,
            discrepancies=discrepancies,
        )
