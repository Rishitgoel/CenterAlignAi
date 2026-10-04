from tools.base import Tool, ToolResult
from tools.browser_operator import BrowserOperatorTool
from tools.document_extractor import DocumentExtractorTool
from tools.erp_client import ERPClientTool
from tools.file_parser import FileParserTool
from tools.file_writer import FileWriterTool
from tools.registry import ToolRegistry


def get_default_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(FileParserTool())
    registry.register(ERPClientTool())
    registry.register(FileWriterTool())
    registry.register(BrowserOperatorTool())
    registry.register(DocumentExtractorTool())
    return registry


__all__ = [
    "Tool",
    "ToolResult",
    "ToolRegistry",
    "FileParserTool",
    "ERPClientTool",
    "FileWriterTool",
    "BrowserOperatorTool",
    "DocumentExtractorTool",
    "get_default_registry",
]
