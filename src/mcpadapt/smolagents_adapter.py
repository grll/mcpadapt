"""This module implements the SmolAgents adapter.

SmolAgents do not support async tools, so this adapter will only work with the sync
context manager.

Features:
- Converts MCP tools to SmolAgents tools
- Supports outputSchema for structured output (MCP spec 2025-06-18+)
- Simple output type detection: structured (object) vs plain text (string)
- Handles both structured data and text content
- Validates output against schema (with warnings, non-strict)
- Backwards compatible with tools without outputSchema

Example Usage:
>>> with MCPAdapt(StdioServerParameters(command="uv", args=["run", "src/echo.py"]), SmolAgentsAdapter()) as tools:
>>>     print(tools)

>>> # Enable structured output features
>>> with MCPAdapt(server_params, SmolAgentsAdapter(structured_output=True)) as tools:
>>>     # Tools now support outputSchema, structuredContent, JSON parsing, etc.

Structured Output Architecture:

The adapter uses a two-level parameter system for clean separation of concerns:

1. `structured_output` (Adapter-level, user-facing):
   - Set by user when creating SmolAgentsAdapter(structured_output=True/False)
   - Controls global behavior for all tools created by this adapter instance
   - Determines whether to process outputSchema from MCP tools
   - Default: False (for backwards compatibility)

2. `use_structured_features` (Tool-level, internal):
   - Passed to each individual MCPAdaptTool during creation
   - Always equals the adapter's structured_output value
   - Controls how each tool processes its output (structuredContent, JSON parsing, etc.)
   - Allows each tool to operate independently without referencing parent adapter

Flow: User Intent → Adapter Config → Schema Processing → Tool Creation → Tool Behavior
      structured_output=True → self.structured_output → outputSchema extraction → use_structured_features=True → Enhanced processing

Output Schema Support:
The adapter supports MCP outputSchema with a simplified approach:
- If outputSchema is provided → output_type = "object" (structured data expected)
- If no outputSchema → output_type = "string" (plain text expected)

When an MCP tool provides an outputSchema, the adapter will:
1. Use structuredContent if available from the MCP tool response
2. Parse JSON from text content if structured data is expected but not provided
3. Validate output against the schema (warnings only, not strict)
4. Fall back to returning text as-is for backwards compatibility

Backwards Compatibility:
- structured_output=False (default): Uses original simple text-only behavior
- structured_output=True: Enables enhanced features while maintaining fallback compatibility
- No breaking changes to existing code

This avoids making assumptions about which specific JSON Schema types MCP officially
supports, focusing on the fundamental distinction between structured vs. unstructured output.
"""

import json
import keyword
import logging
import re
from io import BytesIO
from typing import TYPE_CHECKING, Any, Callable, Coroutine, Union

import jsonref  # type: ignore
import mcp
import smolagents  # type: ignore
from smolagents.utils import _is_package_available  # type: ignore

from mcpadapt.core import ToolAdapter

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    import torch
    from PIL.Image import Image as PILImage


def _sanitize_function_name(name):
    """
    A function to sanitize function names to be used as a tool name.
    Prevent the use of dashes or other python keywords as function names by tool.
    """
    # Replace dashes with underscores
    name = name.replace("-", "_")

    # Remove any characters that aren't alphanumeric or underscore
    name = re.sub(r"[^\w_]", "", name)

    # Ensure it doesn't start with a number
    if name[0].isdigit():
        name = f"_{name}"

    # Check if it's a Python keyword
    if keyword.iskeyword(name):
        name = f"{name}_"

    return name


def _validate_output_against_schema(
    output: Any,
    schema: dict[str, Any] | None,
    tool_name: str,
    strict: bool = False
) -> Any:
    """
    Optionally validate output against schema.

    Since we simplified to only "object" vs "string" output types, this just does
    basic validation that structured output was provided when a schema exists.

    Args:
        output: The output to validate
        schema: The JSON schema to validate against
        tool_name: Tool name for error messages
        strict: If True, raise exception on validation failure; if False, just log warning

    Returns:
        The original output (unchanged)

    Raises:
        ValueError: If strict=True and validation fails
    """
    if not schema:
        return output

    # Basic check: if there's a schema, we expect some kind of structured data
    # (not just a plain string, unless the schema specifically expects a string)
    schema_type = schema.get("type")
    if schema_type != "string" and isinstance(output, str):
        error_msg = f"tool {tool_name} has outputSchema but returned plain text instead of structured data"
        if strict:
            raise ValueError(error_msg)
        else:
            logger.warning(error_msg)

    return output


class SmolAgentsAdapter(ToolAdapter):
    """Adapter for the `smolagents` framework.

    Note that the `smolagents` framework do not support async tools at this time so we
    write only the adapt method.

    Warning: if the mcp tool name is a python keyword, starts with digits or contains
    dashes, the tool name will be sanitized to become a valid python function name.

    """

    def __init__(self, structured_output: bool = False):
        """Initialize the SmolAgentsAdapter.

        Args:
            structured_output: If True, enable structured output features including
                              outputSchema support and structured content handling.
                              If False, use the original simple behavior.
                              Defaults to False for backwards compatibility.
        """
        self.structured_output = structured_output

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

        # Extract and resolve outputSchema if present (only when structured_output=True)
        output_schema = None
        if self.structured_output and hasattr(mcp_tool, 'outputSchema') and mcp_tool.outputSchema:
            try:
                output_schema = jsonref.replace_refs(mcp_tool.outputSchema)
            except Exception as e:
                logger.warning(f"Failed to resolve outputSchema for tool {mcp_tool.name}: {e}")
                output_schema = mcp_tool.outputSchema  # Use unresolved schema as fallback

        # Determine output_type based on mode and schema
        if self.structured_output and output_schema:
            output_type = "object"  # Structured data expected
        else:
            output_type = "string"  # Plain text expected

        class MCPAdaptTool(smolagents.Tool):
            def __init__(
                self,
                name: str,
                description: str,
                inputs: dict[str, dict[str, str]],
                output_type: str,
                output_schema: dict[str, Any] | None = None,
                use_structured_features: bool = False,
            ):
                self.name = _sanitize_function_name(name)
                self.description = description
                self.inputs = inputs
                self.output_type = output_type
                self.output_schema = output_schema
                self.use_structured_features = use_structured_features
                self.is_initialized = True
                self.skip_forward_signature_validation = True

            def forward(self, *args, **kwargs) -> Any:
                if len(args) > 0:
                    if len(args) == 1 and isinstance(args[0], dict) and not kwargs:
                        mcp_output = func(args[0])
                    else:
                        raise ValueError(
                            f"tool {self.name} does not support multiple positional arguments or combined positional and keyword arguments"
                        )
                else:
                    mcp_output = func(kwargs)

                # Early exit for empty content
                if not mcp_output.content:
                    raise ValueError(f"tool {self.name} returned an empty content")

                # Handle structured features if enabled
                if self.use_structured_features:
                    # Prioritize structuredContent if available
                    if hasattr(mcp_output, 'structuredContent') and mcp_output.structuredContent is not None:
                        return _validate_output_against_schema(
                            mcp_output.structuredContent, self.output_schema, self.name, strict=False
                        )

                # Handle multiple content warning (unified for both modes)
                if len(mcp_output.content) > 1:
                    warning_msg = (
                        f"tool {self.name} returned multiple content items but no structuredContent. Using the first content item."
                        if self.use_structured_features
                        else f"tool {self.name} returned multiple content, using the first one"
                    )
                    logger.warning(warning_msg)

                # Get the first content item
                content_item = mcp_output.content[0]
                if not isinstance(content_item, mcp.types.TextContent):
                    raise ValueError(
                        f"tool {self.name} returned a non-text content: `{type(content_item)}`"
                    )

                text_content = content_item.text  # type: ignore

                # Apply structured processing if enabled and expecting structured output
                if self.use_structured_features and self.output_type == "object" and text_content:
                    try:
                        parsed_data = json.loads(text_content)
                        return _validate_output_against_schema(
                            parsed_data, self.output_schema, self.name, strict=False
                        )
                    except json.JSONDecodeError:
                        logger.warning(
                            f"tool {self.name} expected structured output but got unparseable text: {text_content[:100]}..."
                        )
                        # Fall through to return text as-is for backwards compatibility

                # Return simple text content (works for both modes)
                return text_content

        tool = MCPAdaptTool(
            name=mcp_tool.name,
            description=mcp_tool.description or "",
            inputs=input_schema["properties"],
            output_type=output_type,
            output_schema=output_schema,
            use_structured_features=self.structured_output,
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
