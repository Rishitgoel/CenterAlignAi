import json
from typing import Dict, List, Optional
from tools.base import Tool


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def list_tools(self) -> List[Dict]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "parameters_schema": t.parameters_schema,
            }
            for t in self._tools.values()
        ]

    def get_tools_prompt(self) -> str:
        descriptions = []
        for tool in self._tools.values():
            descriptions.append(
                f"Tool: {tool.name}\n"
                f"Description: {tool.description}\n"
                f"Parameters Schema: {json.dumps(tool.parameters_schema, indent=2)}\n"
            )
        return "\n".join(descriptions)
