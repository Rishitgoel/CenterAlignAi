from tools.base import Tool, ToolResult
from tools.erp_client import ERPClientTool
from tools.file_parser import FileParserTool
from tools.file_writer import FileWriterTool
from tools.registry import ToolRegistry


def get_default_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(FileParserTool())
    registry.register(ERPClientTool())
    registry.register(FileWriterTool())
    return registry


__all__ = [
    "Tool",
    "ToolResult",
    "ToolRegistry",
    "FileParserTool",
    "ERPClientTool",
    "FileWriterTool",
    "get_default_registry",
]
