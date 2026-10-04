from pathlib import Path
from typing import Any, Dict
from tools.base import Tool, ToolResult


class FileWriterTool(Tool):
    name: str = "file_writer"
    description: str = (
        "Writes completion reports, summaries, or audit logs to a local file. "
        "Creates parent folders automatically if needed."
    )
    parameters_schema: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Destination file path.",
            },
            "content": {
                "type": "string",
                "description": "Content string to write.",
            },
        },
        "required": ["file_path", "content"],
    }

    async def execute(self, params: Dict[str, Any]) -> ToolResult:
        file_path_str = params.get("file_path")
        content = params.get("content")

        if not file_path_str or content is None:
            return ToolResult(
                success=False,
                error="file_writer requires both 'file_path' and 'content' parameters.",
            )

        try:
            target = Path(file_path_str)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            bytes_written = len(content.encode("utf-8"))
            return ToolResult(
                success=True,
                data={
                    "file_path": str(target),
                    "bytes_written": bytes_written,
                    "status": "written",
                },
                metadata={"file_path": str(target), "bytes_written": bytes_written},
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"FileWriter error: {str(e)}",
            )
