"""This module implements the SmolAgents adapter.

SmolAgents do not support async tools, so this adapter will only work with the sync
context manager.

Example Usage:
>>> with MCPAdapt(StdioServerParameters(command="uv", args=["run", "src/echo.py"]), SmolAgentAdapter()) as tools:
>>>     print(tools)
"""

import logging
from typing import Any, Callable, Coroutine

import jsonref  # type: ignore
import mcp
import smolagents  # type: ignore

from mcpadapt.core import ToolAdapter

logger = logging.getLogger(__name__)


class SmolAgentsAdapter(ToolAdapter):
    """Adapter for the `smolagents` framework.

    Note that the `smolagents` framework do not support async tools at this time so we
    write only the adapt method.
    """

    def adapt(
        self,
        func: Callable[[dict | None], mcp.types.CallToolResult],
        mcp_tool: mcp.types.Tool,
    ) -> smolagents.Tool:
        """Adapt a MCP tool to a SmolAgents tool.

        Args:
            func: The function to adapt.
            mcp_tool: The MCP tool to adapt.

        Returns:
            A SmolAgents tool.
        """

        class MCPAdaptTool(smolagents.Tool):
            def __init__(
                self,
                name: str,
                description: str,
                inputs: dict[str, dict[str, str]],
                output_type: str,
            ):
                self.name = name
                self.description = description
                self.inputs = inputs
                self.output_type = output_type
                self.is_initialized = True
                self.skip_forward_signature_validation = True

            def forward(self, *args, **kwargs) -> str:
                if len(args) > 0:
                    if len(args) == 1 and isinstance(args[0], dict) and not kwargs:
                        mcp_output = func(args[0])
                    else:
                        raise ValueError(
                            f"tool {self.name} does not support multiple positional arguments or combined positional and keyword arguments"
                        )
                else:
                    mcp_output = func(kwargs)

                if len(mcp_output.content) == 0:
                    raise ValueError(f"tool {self.name} returned an empty content")

                if len(mcp_output.content) > 1:
                    logger.warning(
                        f"tool {self.name} returned multiple content, using the first one"
                    )

                if not isinstance(mcp_output.content[0], mcp.types.TextContent):
                    raise ValueError(
                        f"tool {self.name} returned a non-text content: `{type(mcp_output.content[0])}`"
                    )

                return mcp_output.content[0].text  # type: ignore

        # make sure jsonref are resolved
        input_schema = {
            k: v
            for k, v in jsonref.replace_refs(mcp_tool.inputSchema).items()
            if k != "$defs"
        }

        # make sure mandatory `description` and `type` is provided for each arguments:
        for k, v in input_schema["properties"].items():
            if "description" not in v:
                input_schema["properties"][k]["description"] = "see tool description"
            if "type" not in v:
                input_schema["properties"][k]["type"] = "string"

        tool = MCPAdaptTool(
            name=mcp_tool.name,
            description=mcp_tool.description or "",
            inputs=input_schema["properties"],
            output_type="string",
        )

        return tool

    async def async_adapt(
        self,
        afunc: Callable[[dict | None], Coroutine[Any, Any, mcp.types.CallToolResult]],
        mcp_tool: mcp.types.Tool,
    ) -> smolagents.Tool:
        raise NotImplementedError("async is not supported by the SmolAgents framework.")


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
        SmolAgentsAdapter(),
    ) as tools:
        print(tools)
        # that's all that goes into the system prompt:
        print(tools[0].name)
        print(tools[0].description)
        print(tools[0].inputs)
        print(tools[0].output_type)
