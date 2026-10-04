"""
Utility script to reset all demo data and state back to a pristine clean slate.
Usage:
    python reset_demo_data.py
"""
import glob
import os
import sqlite3
from pathlib import Path


def reset_environment():
    print("=" * 60)
    print("Resetting CentrAlign AI Demo Environment to Clean Slate")
    print("=" * 60)

    # 1. Reset ERP SQLite Database
    db_path = Path("erp_data.db")
    if db_path.exists():
        conn = sqlite3.connect(str(db_path))
        c = conn.cursor()
        c.execute("DELETE FROM invoices")
        try:
            c.execute("DELETE FROM sqlite_sequence WHERE name='invoices'")
        except sqlite3.OperationalError:
            pass  # sequence table may not exist yet
        conn.commit()

        c.execute("SELECT COUNT(*) FROM vendors")
        vendor_count = c.fetchone()[0]
        conn.close()
        print(f"[OK] Invoices table cleared. ({vendor_count} standard vendors ready)")
    else:
        print("[INFO] erp_data.db not found; will be created fresh on server start.")

    # 2. Reset Suspended HITL Tasks
    suspended_count = 0
    for f in glob.glob("logs/suspended_tasks/*.json"):
        try:
            os.remove(f)
            suspended_count += 1
        except Exception:
            pass
    print(f"[OK] Suspended HITL task queue cleared ({suspended_count} files removed).")

    # 3. Reset Background Jobs
    jobs_count = 0
    for f in glob.glob("logs/jobs/*.json"):
        try:
            os.remove(f)
            jobs_count += 1
        except Exception:
            pass
    print(f"[OK] Background worker jobs cleared ({jobs_count} files removed).")

    # 4. Reset Previous Task Logs & Completion Reports
    logs_count = 0
    for pattern in ["logs/task_*.json", "logs/task_completion_*.*", "logs/screenshots/*.png"]:
        for f in glob.glob(pattern):
            try:
                os.remove(f)
                logs_count += 1
            except Exception:
                pass
    print(f"[OK] Previous task execution logs & screenshots cleared ({logs_count} files removed).")

    # 5. Reset Cryptographic Audit Ledger
    ledger_path = Path("logs/compliance_audit_ledger.jsonl")
    if ledger_path.exists():
        ledger_path.write_text("", encoding="utf-8")
        print("[OK] Cryptographic audit ledger reset to clean genesis state.")

    print("=" * 60)
    print("Environment is 100% clean and ready for demo recording!")
    print("=" * 60)


if __name__ == "__main__":
    reset_environment()
