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
