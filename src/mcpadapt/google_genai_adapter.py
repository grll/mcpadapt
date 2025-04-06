"""This module implements the Google GenAI adapter.

Example Usage:
>>> with MCPAdapt(StdioServerParameters(command="uv", args=["run", "src/echo.py"]), GoogleGenAIAdapter()) as tools:
>>>     print(tools)
"""

import logging
from typing import Any, Callable, Coroutine

import jsonref  # type: ignore
import mcp
from google.genai import types  # type: ignore

from mcpadapt.core import ToolAdapter

logger = logging.getLogger(__name__)


class GoogleGenAIAdapter(ToolAdapter):
    """Adapter for the `google.genai` package.

    Note that the `google.genai` package do not support async tools at this time so we
    write only the adapt method.
    """

    def adapt(
        self,
        func: Callable[[dict | None], mcp.types.CallToolResult],
        mcp_tool: mcp.types.Tool,
    ) -> tuple[
        types.Tool, tuple[str, Callable[[dict | None], mcp.types.CallToolResult]]
    ]:
        """Adapt a MCP tool to a Google GenAI tool.

        Args:
            func: The function to adapt.
            mcp_tool: The MCP tool to adapt.

        Returns:
            A Google GenAI tool.
        """
        # make sure jsonref are resolved
        input_schema = {
            k: v
            for k, v in jsonref.replace_refs(mcp_tool.inputSchema).items()
            if k != "$defs"
        }

        return (
            types.Tool(
                function_declarations=[
                    {
                        "name": mcp_tool.name,
                        "description": mcp_tool.description,
                        "parameters": input_schema,
                    }
                ],
            ),
            (mcp_tool.name, func),
        )

    def async_adapt(
        self,
        func: Callable[[dict | None], Coroutine[Any, Any, mcp.types.CallToolResult]],
        mcp_tool: mcp.types.Tool,
    ) -> tuple[
        types.Tool,
        tuple[
            str, Callable[[dict | None], Coroutine[Any, Any, mcp.types.CallToolResult]]
        ],
    ]:
        """Adapt a MCP tool to a Google GenAI tool.

        Args:
            func: The function to adapt.
            mcp_tool: The MCP tool to adapt.

        Returns:
            A Google GenAI tool.
        """
        # make sure jsonref are resolved
        input_schema = {
            k: v
            for k, v in jsonref.replace_refs(mcp_tool.inputSchema).items()
            if k != "$defs"
        }

        return (
            types.Tool(
                function_declarations=[
                    {
                        "name": mcp_tool.name,
                        "description": mcp_tool.description,
                        "parameters": input_schema,
                    }
                ],
            ),
            (mcp_tool.name, func),
        )


if __name__ == "__main__":
    import os

    from mcp import StdioServerParameters

    from mcpadapt.core import MCPAdapt

    with MCPAdapt(
        StdioServerParameters(
            command="uvx",
            args=["--quiet", "pubmedmcp@0.1.3"],
            env={"UV_PYTHON": "3.12", **os.environ},
        ),
        GoogleGenAIAdapter(),
    ) as tools:
        print(tools[0][1].args[-1])
