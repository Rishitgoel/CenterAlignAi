import pytest
from agent.query_parser import AIQueryParser, ParsedQuery


def test_query_parser_deterministic_invoice_creation():
    parser = AIQueryParser(api_key=None)
    query = "create invoice for nabhas aircon for 40000 amount after one moth date"
    parsed = parser.parse_deterministic(query)

    assert parsed.action == "create_invoice"
    assert parsed.vendor_name == "Nabhas Aircon"
    assert parsed.amount == 40000.0
    assert "2026-11-" in parsed.due_date
    assert parsed.currency == "USD"
    assert parsed.parser_source == "deterministic"


def test_query_parser_deterministic_browser_intent():
    parser = AIQueryParser(api_key=None)
    query = "open portal and enter invoice for stark industries with $15000 in browser"
    parsed = parser.parse_deterministic(query)

    assert parsed.use_browser is True
    assert parsed.vendor_name == "Stark Industries"
    assert parsed.amount == 15000.0


def test_query_parser_deterministic_file_ingestion():
    parser = AIQueryParser(api_key=None)
    query = "process document demo/invoices/cyberdyne_005.pdf into ERP"
    parsed = parser.parse_deterministic(query)

    assert parsed.action == "process_document"
    assert parsed.file_path == "demo/invoices/cyberdyne_005.pdf"


def test_query_parser_model_cascade_order():
    parser = AIQueryParser(api_key="mock_key")
    assert parser.model_cascade == [
        "gemini-3.5-flash-lite",
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
    ]


def test_query_parser_crm_stage_movement():
    parser = AIQueryParser(api_key=None)
    query = "process tidewater to won state"
    parsed = parser.parse_deterministic(query)

    assert parsed.action == "move_crm_stage"
    assert parsed.vendor_name == "Tidewater"
    assert parsed.target_stage == "won"
    assert parsed.amount == 27000.0
    assert parsed.use_browser is True


def test_planner_crm_stage_plan_generation():
    from agent.planner import Planner
    planner = Planner(api_key=None)
    plan = planner._create_heuristic_plan("process tidewater to won state")

    assert len(plan.steps) == 2
    step_1 = plan.steps[0]
    assert step_1.tool_name == "browser_operator"
    assert step_1.tool_input["action"] == "move_opportunity_stage"
    assert step_1.tool_input["company"] == "Tidewater"
    assert step_1.tool_input["target_stage"] == "won"

    step_2 = plan.steps[1]
    assert step_2.tool_name == "file_writer"
    assert "logs/task_completion_report.md" in step_2.tool_input["file_path"]


def test_query_parser_view_switch():
    parser = AIQueryParser(api_key=None)
    parsed_table = parser.parse_deterministic("switch to table")
    assert parsed_table.action == "switch_view"
    assert parsed_table.target_view == "table"

    parsed_kanban = parser.parse_deterministic("switch to kanban")
    assert parsed_kanban.action == "switch_view"
    assert parsed_kanban.target_view == "kanban"

    parsed_audit = parser.parse_deterministic("switch to audit")
    assert parsed_audit.action == "switch_view"
    assert parsed_audit.target_view == "audit"

    parsed_tasks = parser.parse_deterministic("show task history")
    assert parsed_tasks.action == "switch_view"
    assert parsed_tasks.target_view == "audit"


def test_query_parser_crm_filter():
    parser = AIQueryParser(api_key=None)
    parsed = parser.parse_deterministic("filter deals over 50000")
    assert parsed.action == "filter_crm"
    assert parsed.amount == 50000.0


def test_query_parser_invoice_approval_and_deletion():
    parser = AIQueryParser(api_key=None)
    parsed_approve = parser.parse_deterministic("approve invoice 87")
    assert parsed_approve.action == "approve_invoice"
    assert parsed_approve.invoice_id == 87

    parsed_delete = parser.parse_deterministic("delete invoice 88")
    assert parsed_delete.action == "delete_invoice"
    assert parsed_delete.invoice_id == 88


def test_planner_software_operator_plans():
    from agent.planner import Planner
    planner = Planner(api_key=None)

    plan_view = planner._create_heuristic_plan("switch to table")
    assert plan_view.steps[0].tool_name == "browser_operator"
    assert plan_view.steps[0].tool_input["action"] == "switch_portal_view"

    plan_approve = planner._create_heuristic_plan("approve invoice 87")
    assert plan_approve.steps[0].tool_name == "erp_client"
    assert plan_approve.steps[0].tool_input["action"] == "update_invoice_status"
    assert plan_approve.steps[0].tool_input["invoice_id"] == 87

    plan_delete = planner._create_heuristic_plan("delete invoice 88")
    assert plan_delete.steps[0].tool_name == "erp_client"
    assert plan_delete.steps[0].tool_input["action"] == "delete_invoice"
    assert plan_delete.steps[0].tool_input["invoice_id"] == 88
