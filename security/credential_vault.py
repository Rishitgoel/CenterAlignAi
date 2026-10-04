import re
from typing import Any, Dict, Optional, Set


class CredentialVault:
    """Enterprise credential manager and sensitive token redaction filter (SOC2 / HIPAA / ISO 27001).

    Safely stores secret keys, injects authentication tokens into tool calls at runtime,
    and strips sensitive secrets from LLM prompt contexts and audit logs.
    """

    def __init__(self):
        self._secrets: Dict[str, str] = {}
        self._sensitive_values: Set[str] = set()

        # Regex patterns for common sensitive tokens (API keys, passwords, bearer tokens)
        self._patterns = [
            re.compile(r"(?i)(bearer\s+)[A-Za-z0-9_\-\.]{16,}", re.IGNORECASE),
            re.compile(r"(?i)(api[_-]?key[\"'\s:=]+)[\"']?([A-Za-z0-9_\-]{16,})[\"']?", re.IGNORECASE),
            re.compile(r"(?i)(password[\"'\s:=]+)[\"']?([^\s\"',]+)[\"']?", re.IGNORECASE),
            re.compile(r"(?i)(secret[\"'\s:=]+)[\"']?([A-Za-z0-9_\-]{16,})[\"']?", re.IGNORECASE),
        ]

    def store_secret(self, key: str, value: str):
        """Stores a credential key-value pair and registers it for redaction."""
        if not value or len(value.strip()) < 4:
            return
        self._secrets[key] = value
        self._sensitive_values.add(value)

    def get_secret(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Retrieves a credential key without exposing it to public inspection."""
        return self._secrets.get(key, default)

    def redact_text(self, text: str) -> str:
        """Sanitizes text by replacing registered secrets and sensitive token patterns with [REDACTED]."""
        if not text or not isinstance(text, str):
            return text

        redacted = text
        # 1. Exact match replacements for registered secrets
        for secret in self._sensitive_values:
            if secret in redacted:
                masked = f"[REDACTED_{secret[:3]}...{secret[-2:]}]" if len(secret) > 6 else "[REDACTED]"
                redacted = redacted.replace(secret, masked)

        # 2. Pattern-based redaction
        for pattern in self._patterns:
            redacted = pattern.sub(r"\1[REDACTED_SECRET]", redacted)

        return redacted

    def redact_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively sanitizes dictionary fields and values."""
        clean: Dict[str, Any] = {}
        for k, v in data.items():
            # Check key name
            is_sensitive_key = any(s in k.lower() for s in ["password", "secret", "token", "auth", "api_key", "apikey"])
            if isinstance(v, str):
                if is_sensitive_key:
                    clean[k] = "[REDACTED_SECRET]"
                else:
                    clean[k] = self.redact_text(v)
            elif isinstance(v, dict):
                clean[k] = self.redact_dict(v)
            elif isinstance(v, list):
                clean[k] = [self.redact_dict(item) if isinstance(item, dict) else (self.redact_text(item) if isinstance(item, str) else item) for item in v]
            else:
                clean[k] = v
        return clean


credential_vault = CredentialVault()
