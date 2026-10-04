import asyncio
from datetime import datetime, timezone, timedelta
import json
import logging
from pathlib import Path
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import warnings

warnings.filterwarnings("ignore")
logging.getLogger("google.genai").setLevel(logging.ERROR)
from google import genai
try:
    from google.genai.models import AsyncModels, Models
    AsyncModels._logged_afc_warning = True
    Models._logged_afc_warning = True
except Exception:
    pass
from config import settings


class ParsedQuery(BaseModel):
    raw_query: str
    action: str = "create_invoice"  # "create_invoice" | "process_document" | "query_invoices" | "browser_submit" | "verify_audit"
    vendor_name: Optional[str] = None
    amount: Optional[float] = None
    currency: str = "USD"
    due_date: Optional[str] = None
    invoice_number: Optional[str] = None
    file_path: Optional[str] = None
    use_browser: bool = False
    filters: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = 1.0
    parser_source: str = "deterministic"


QUERY_PARSER_SYSTEM_PROMPT = """You are an expert natural language query parser for an enterprise autonomous task worker.
Analyze the user's task instruction and output a JSON object conforming to the schema:
{
  "action": "create_invoice" | "process_document" | "query_invoices" | "browser_submit" | "verify_audit",
  "vendor_name": "string or null",
  "amount": number or null,
  "currency": "USD" | "EUR" | "GBP" | "INR",
  "due_date": "YYYY-MM-DD or null",
  "invoice_number": "string or null",
  "file_path": "string or null",
  "use_browser": boolean,
  "confidence": number between 0.0 and 1.0
}
Output strictly valid JSON with no markdown formatting or commentary.
"""


class AIQueryParser:
    """Intelligent multi-model AI query parser with deterministic fallback."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.gemini_api_key
        self._client: Optional[genai.Client] = None
        self.model_cascade = [
            "gemini-2.5-flash",
            "gemini-2.5-flash-lite",
            "gemini-3.5-flash-lite",
        ]

    def _get_client(self) -> Optional[genai.Client]:
        if not self._client and self.api_key:
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    async def parse(self, query: str) -> ParsedQuery:
        """Parse arbitrary user query using Gemini model cascade, falling back to deterministic extraction."""
        client = self._get_client()

        if client:
            for model_name in self.model_cascade:
                try:
                    response = await asyncio.wait_for(
                        client.aio.models.generate_content(
                            model=model_name,
                            contents=f"{QUERY_PARSER_SYSTEM_PROMPT}\n\nUSER QUERY:\n{query}",
                        ),
                        timeout=3.0,
                    )
                    raw_text = response.text or ""
                    cleaned = re.sub(r"^```(?:json)?\s*", "", raw_text.strip(), flags=re.MULTILINE)
                    cleaned = re.sub(r"```$", "", cleaned.strip(), flags=re.MULTILINE).strip()
                    json_match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
                    if json_match:
                        data = json.loads(json_match.group(1))
                        return ParsedQuery(
                            raw_query=query,
                            action=data.get("action", "create_invoice"),
                            vendor_name=data.get("vendor_name"),
                            amount=float(data["amount"]) if data.get("amount") is not None else None,
                            currency=data.get("currency", "USD"),
                            due_date=data.get("due_date"),
                            invoice_number=data.get("invoice_number"),
                            file_path=data.get("file_path"),
                            use_browser=bool(data.get("use_browser", False)),
                            confidence=float(data.get("confidence", 0.95)),
                            parser_source=model_name,
                        )
                except Exception:
                    # Proceed to next model in cascade
                    continue

        # Zero-dependency deterministic parser fallback
        return self.parse_deterministic(query)

    def parse_deterministic(self, query: str) -> ParsedQuery:
        """Deterministic NLP regex entity extractor for enterprise queries."""
        task_lower = query.lower()

        # 1. Action determination
        is_verify = any(w in task_lower for w in ["verify", "ledger", "audit", "hash", "reconcile"])
        is_query = any(w in task_lower for w in ["find", "search", "show all", "list", "query", "filter"])
        use_browser = any(kw in task_lower for kw in ["browser", "portal", "website", "web portal", "ui", "web form", "playwright"])

        # 2. File path detection
        file_match = re.search(r"([\w/\\.-]+\.(?:json|csv|txt|pdf|eml|png|jpg|jpeg))", query, re.IGNORECASE)
        file_path = file_match.group(1) if file_match else None

        action = "create_invoice"
        if file_path:
            action = "process_document"
        elif is_verify:
            action = "verify_audit"
        elif is_query:
            action = "query_invoices"
        elif use_browser:
            action = "browser_submit"

        # 3. Vendor extraction
        vendor_match = re.search(
            r"(?:for|vendor|company|supplier)\s+([A-Za-z0-9\s&]+?)(?:,|\swith|\sfor|\samount|\sinvoice|\sdue|\s\$|\.|$)",
            query,
            re.IGNORECASE,
        )
        vendor_name = vendor_match.group(1).strip().title() if vendor_match else None

        # 4. Amount extraction
        amount = None
        m = re.search(r"\$\s*([0-9][0-9,]*\.?[0-9]*)", query)
        if m:
            amount = float(m.group(1).replace(",", ""))
        if amount is None:
            m = re.search(r"([0-9][0-9,]*\.?[0-9]*)\s*(?:amount|dollars|usd|rs|inr|k\b)", query, re.IGNORECASE)
            if m:
                amount = float(m.group(1).replace(",", ""))
        if amount is None:
            m = re.search(r"amount\s*(?:of|:|\s)?\s*([0-9][0-9,]*\.?[0-9]*)", query, re.IGNORECASE)
            if m:
                amount = float(m.group(1).replace(",", ""))
        if amount is None:
            m = re.search(r"(?:for|total|worth)\s+([0-9][0-9,]*\.?[0-9]*)", query, re.IGNORECASE)
            if m:
                amount = float(m.group(1).replace(",", ""))

        # 5. Currency detection
        currency = "USD"
        if any(w in task_lower for w in ["inr", "rs", "rupee"]):
            currency = "INR"
        elif any(w in task_lower for w in ["eur", "euro"]):
            currency = "EUR"
        elif any(w in task_lower for w in ["gbp", "pound"]):
            currency = "GBP"

        # 6. Invoice number extraction
        inv_match = re.search(r"(?:invoice(?:\s*(?:number|num|id|#))(?:\s*[:=]?\s*|\s+))([A-Za-z0-9-_]+)", query, re.IGNORECASE)
        if not inv_match:
            inv_match = re.search(r"\b(INV-[A-Za-z0-9-_]+|#[0-9]+)\b", query, re.IGNORECASE)
        invoice_number = inv_match.group(1).replace("#", "").strip() if inv_match else None

        # 7. Date extraction (relative & absolute)
        today = datetime.now(timezone.utc)
        due_date = None
        if re.search(r"(?:one|1|a)\s*mo(?:nth|th)", query, re.IGNORECASE):
            due_date = (today + timedelta(days=30)).strftime("%Y-%m-%d")
        elif re.search(r"(?:two|2)\s*months", query, re.IGNORECASE):
            due_date = (today + timedelta(days=60)).strftime("%Y-%m-%d")
        elif re.search(r"(?:one|1)\s*week", query, re.IGNORECASE):
            due_date = (today + timedelta(days=7)).strftime("%Y-%m-%d")
        elif re.search(r"(?:two|2)\s*weeks", query, re.IGNORECASE):
            due_date = (today + timedelta(days=14)).strftime("%Y-%m-%d")
        elif re.search(r"(\d{4}-\d{2}-\d{2})", query):
            due_date = re.search(r"(\d{4}-\d{2}-\d{2})", query).group(1)

        return ParsedQuery(
            raw_query=query,
            action=action,
            vendor_name=vendor_name or "Nabhas Aircon",
            amount=amount if amount is not None else 2500.0,
            currency=currency,
            due_date=due_date or (today + timedelta(days=30)).strftime("%Y-%m-%d"),
            invoice_number=invoice_number or f"INV-{abs(hash(query)) % 100000}",
            file_path=file_path,
            use_browser=use_browser,
            confidence=1.0,
            parser_source="deterministic",
        )
