import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import httpx
from tools.base import Tool, ToolResult


class OpenAPITool(Tool):
    """Dynamically synthesized tool wrapping an individual OpenAPI endpoint operation."""

    def __init__(
        self,
        name: str,
        description: str,
        path: str,
        method: str,
        parameters_schema: Dict[str, Any],
        base_url: str,
    ):
        self.name = name
        self.description = description
        self.path = path
        self.method = method.upper()
        self.parameters_schema = parameters_schema
        self.base_url = base_url.rstrip("/")

    async def execute(self, params: Dict[str, Any]) -> ToolResult:
        url = f"{self.base_url}{self.path}"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                if self.method == "GET":
                    resp = await client.get(url, params=params)
                elif self.method == "POST":
                    resp = await client.post(url, json=params)
                elif self.method == "PUT":
                    resp = await client.put(url, json=params)
                elif self.method == "DELETE":
                    resp = await client.delete(url, params=params)
                else:
                    return ToolResult(success=False, error=f"Unsupported HTTP method: {self.method}")

                is_ok = 200 <= resp.status_code < 300
                data = resp.json() if "application/json" in resp.headers.get("content-type", "") else resp.text

                return ToolResult(
                    success=is_ok,
                    data=data,
                    error=None if is_ok else f"API Error ({resp.status_code}): {resp.text}",
                    metadata={"status_code": resp.status_code, "method": self.method, "url": url},
                )
        except Exception as e:
            return ToolResult(success=False, error=f"OpenAPI tool call failed: {str(e)}")


class OpenAPILoader:
    """Ingests arbitrary OpenAPI v3 / Swagger specs and generates callable tools dynamically."""

    @staticmethod
    def load_from_spec(spec_data: Dict[str, Any], base_url: str) -> List[Tool]:
        tools: List[Tool] = []
        paths = spec_data.get("paths", {})

        for path, path_item in paths.items():
            for method, operation in path_item.items():
                if method.lower() not in ["get", "post", "put", "delete"]:
                    continue

                operation_id = operation.get("operationId") or f"{method.lower()}_{path.strip('/').replace('/', '_')}"
                summary = operation.get("summary") or operation.get("description") or f"Execute {method.upper()} {path}"
                clean_name = f"api_{operation_id.replace('-', '_')}"

                # Build parameters schema
                properties: Dict[str, Any] = {}
                required_props: List[str] = []

                # Extract query / path parameters
                for param in operation.get("parameters", []):
                    p_name = param.get("name")
                    p_schema = param.get("schema", {"type": "string"})
                    p_desc = param.get("description", "")
                    properties[p_name] = {
                        "type": p_schema.get("type", "string"),
                        "description": p_desc,
                    }
                    if param.get("required"):
                        required_props.append(p_name)

                # Extract requestBody properties for POST/PUT
                if "requestBody" in operation:
                    content = operation["requestBody"].get("content", {})
                    app_json = content.get("application/json", {})
                    body_schema = app_json.get("schema", {})
                    if "properties" in body_schema:
                        for p_name, p_def in body_schema["properties"].items():
                            properties[p_name] = {
                                "type": p_def.get("type", "string"),
                                "description": p_def.get("description", f"Property {p_name}"),
                            }
                        for req_name in body_schema.get("required", []):
                            if req_name not in required_props:
                                required_props.append(req_name)

                param_schema = {
                    "type": "object",
                    "properties": properties,
                    "required": required_props,
                }

                tool = OpenAPITool(
                    name=clean_name,
                    description=summary,
                    path=path,
                    method=method,
                    parameters_schema=param_schema,
                    base_url=base_url,
                )
                tools.append(tool)

        return tools

    @staticmethod
    def load_from_file(file_path: str, base_url: str) -> List[Tool]:
        p = Path(file_path)
        if not p.exists():
            raise FileNotFoundError(f"OpenAPI spec file not found: {file_path}")
        data = json.loads(p.read_text(encoding="utf-8"))
        return OpenAPILoader.load_from_spec(data, base_url)
