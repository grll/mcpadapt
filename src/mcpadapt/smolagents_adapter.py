"""This module implements the SmolAgents adapter.

SmolAgents do not support async tools, so this adapter will only work with the sync
context manager.

Features:
- Converts MCP tools to SmolAgents tools
- Supports outputSchema for structured output (MCP spec 2025-06-18+)
- Always uses "object" output_type for maximum flexibility
- Handles text, image, and audio content types
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

Output Type Strategy:
The adapter always uses output_type="object" for maximum flexibility, allowing smolagents
to handle type detection at runtime. This supports all MCP content types:
- TextContent (strings) → handled by smolagents runtime type detection
- ImageContent (PIL Images) → handled by smolagents runtime type detection
- AudioContent (torch Tensors) → handled by smolagents runtime type detection

If structured_output=True, the adapter will:
1. Use structuredContent if available from the MCP tool response
2. Always attempt to parse JSON from text content if structuredContent is absent
3. Fall back to returning text as-is for backwards compatibility

Backwards Compatibility:
- structured_output=False (default): Uses original simple behavior
- structured_output=True: Enables enhanced features while maintaining fallback compatibility
- No breaking changes to existing code
"""

import base64
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

        # Extract and resolve outputSchema if present (only if structured_output=True)
        output_schema = None
        if self.structured_output and hasattr(mcp_tool, 'outputSchema') and mcp_tool.outputSchema:
            try:
                output_schema = jsonref.replace_refs(mcp_tool.outputSchema)
            except Exception as e:
                logger.warning(f"Failed to resolve outputSchema for tool {mcp_tool.name}: {e}")
                output_schema = mcp_tool.outputSchema  # Use unresolved schema as fallback

        # Always use "object" output_type for maximum flexibility
        # Smolagents will handle type detection at runtime
        output_type = "object"

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

            def forward(self, *args, **kwargs) -> Union[str, "PILImage", "torch.Tensor", Any]:
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
                        return mcp_output.structuredContent

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

                # Handle different content types
                if isinstance(content_item, mcp.types.TextContent):
                    text_content = content_item.text

                    # Always try to parse JSON if structured features are enabled and structuredContent is absent
                    if self.use_structured_features and text_content:
                        try:
                            parsed_data = json.loads(text_content)
                            return parsed_data
                        except json.JSONDecodeError:
                            logger.warning(
                                f"tool {self.name} expected structured output but got unparseable text: {text_content[:100]}..."
                            )
                            # Fall through to return text as-is for backwards compatibility

                    # Return simple text content (works for both modes)
                    return text_content

                elif isinstance(content_item, mcp.types.ImageContent):
                    from PIL import Image

                    image_data = base64.b64decode(content_item.data)
                    image = Image.open(BytesIO(image_data))
                    return image

                elif isinstance(content_item, mcp.types.AudioContent):
                    if not _is_package_available("torchaudio"):
                        raise ValueError(
                            "Audio content requires the torchaudio package to be installed. "
                            "Please install it with `uv add mcpadapt[smolagents,audio]`.",
                        )
                    else:
                        import torchaudio  # type: ignore

                        audio_data = base64.b64decode(content_item.data)
                        audio_io = BytesIO(audio_data)
                        audio_tensor, _ = torchaudio.load(audio_io)
                        return audio_tensor

                else:
                    raise ValueError(
                        f"tool {self.name} returned an unsupported content type: {type(content_item)}"
                    )

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
