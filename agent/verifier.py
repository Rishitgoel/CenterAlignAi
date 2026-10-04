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
                amount_ok = (abs(actual_amount - float(expected_amount or 0.0)) < 0.01)
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

        all_passed = len(checks) > 0 and all(c.matched for c in checks) and len(discrepancies) == 0

        return VerificationResult(
            passed=all_passed,
            checks=checks,
            evidence=evidence,
            discrepancies=discrepancies,
        )
