"""This module implements the CrewAI adapter.

CrewAI tools support only sync functions for their tools.

Example Usage:
>>> with MCPAdapt(StdioServerParameters(command="uv", args=["run", "src/echo.py"]), CrewAIAdapter()) as tools:
>>>     print(tools)
"""

from typing import Any, Callable, Coroutine, Type

import jsonref  # type: ignore
import mcp
from crewai.tools import BaseTool  # type: ignore
from pydantic import BaseModel

from mcpadapt.core import ToolAdapter
from mcpadapt.utils.modeling import create_model_from_json_schema

json_type_mapping: dict[str, Type] = {
    "string": str,
    "number": float,
    "integer": int,
    "boolean": bool,
    "object": dict,
    "array": list,
}


class CrewAIAdapter(ToolAdapter):
    """Adapter for `crewai`.

    Note that `crewai` support only sync tools so we write adapt for sync tools only.

    Warning: if the mcp tool name is a python keyword, starts with digits or contains
    dashes, the tool name will be sanitized to become a valid python function name.

    """

    def adapt(
        self,
        func: Callable[[dict | None], mcp.types.CallToolResult],
        mcp_tool: mcp.types.Tool,
    ) -> BaseTool:
        """Adapt a MCP tool to a CrewAI tool.

        Args:
            func: The function to adapt.
            mcp_tool: The MCP tool to adapt.

        Returns:
            A CrewAI tool.
        """
        ToolInput = create_model_from_json_schema(mcp_tool.inputSchema)

        class CrewAIMCPTool(BaseTool):
            name: str = mcp_tool.name
            description: str = mcp_tool.description or ""
            args_schema: Type[BaseModel] = ToolInput

            def _run(self, *args: Any, **kwargs: Any) -> Any:
                print("args", args)
                print("kwargs", kwargs)
                return func(kwargs).content[0].text  # type: ignore

            def _generate_description(self):
                args_schema = {
                    k: v
                    for k, v in jsonref.replace_refs(
                        self.args_schema.model_json_schema()
                    ).items()
                    if k != "$defs"
                }
                self.description = f"Tool Name: {self.name}\nTool Arguments: {args_schema}\nTool Description: {self.description}"

        return CrewAIMCPTool()

    async def async_adapt(
        self,
        afunc: Callable[[dict | None], Coroutine[Any, Any, mcp.types.CallToolResult]],
        mcp_tool: mcp.types.Tool,
    ) -> Any:
        raise NotImplementedError("async is not supported by the CrewAI framework.")


if __name__ == "__main__":
    from mcp import StdioServerParameters

    from mcpadapt.core import MCPAdapt

    with MCPAdapt(
        StdioServerParameters(command="uv", args=["run", "src/echo.py"]),
        CrewAIAdapter(),
    ) as tools:
        print(tools)
        print(tools[0].run(text="hello"))
