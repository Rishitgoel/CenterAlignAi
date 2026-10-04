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
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        "gemini-3.5-flash-lite",
    ]
