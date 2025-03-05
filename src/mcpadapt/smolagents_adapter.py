"""This module implements the SmolAgents adapter.

SmolAgents do not support async tools, so this adapter will only work with the sync
context manager.

Example Usage:
>>> with MCPAdapt(StdioServerParameters(command="uv", args=["run", "src/echo.py"]), SmolAgentAdapter()) as tools:
>>>     print(tools)
"""

import json
from typing import Any, Callable

import jsonref
import mcp
import smolagents

from mcpadapt.core import ToolAdapter


def _generate_tool_inputs(
    resolved_json_schema: dict[str, Any],
) -> dict[str, dict[str, str]]:
    """
    takes an json_schema as used in the MCP protocol and return an inputs dict for
    smolagents tools. see AUTHORIZED_TYPES in smolagents.tools for the types allowed.
    Note that we consider the json_schema to already have $ref resolved with jsonref for
    example.
    """
    inputs: dict[str, dict[str, str]] = {}
    for k, v in resolved_json_schema.items():
        inputs[k] = {
            "type": v.get("type") or v.get("anyOf")[0].get("type"),
            "description": v.get(
                "description", ""
            ),  # TODO: use google-docstring-parser to parse description of args and pass it here...
        }
        if "default" in v:
            inputs[k]["default"] = (
                f'"{v["default"]}"'
                if isinstance(v["default"], str)
                else str(v["default"])
            )
            inputs[k]["nullable"] = "True"
    return inputs


def _generate_tool_class(
    name: str,
    description: str,
    inputSchema: dict[str, Any],
) -> str:
    """generate a smolagents tool class from the MCP protocol informations.

    Note: we generate code because smolagents is very picky about the signature of the
    forward method matching the inputs name and type.

    Return a string with the class so it's easy to test and debug the generated code.

    Args:
        name: the name of the tool as used in the MCP protocol
        description: the description of the tool as used in the MCP protocol
        inputSchema: the input schema of the tool as used in the MCP protocol

    Returns:
        the generated smolagentstool class as a string to be executed with exec.
        **important**: the class_template need smolagents and func in the namespace to
        be exec. We assume func as being a sync function taking a single dict argument
        and returning a CallToolResult as in:
        func: Callable[[dict | None], mcp.types.CallToolResult]
    """
    resolved_json_schema = jsonref.replace_refs(inputSchema).get("properties", {})
    smolagents_inputs = _generate_tool_inputs(resolved_json_schema)

    # smolagents provide arguments to the forward as follow forward(arg1=..., arg2=...)
    # but MCP call_tool takes a single 'argument' as in func({'arg1': .., 'arg2': ..})
    forward_params = ", ".join(
        f"{k}={v['default']}" if "default" in v else f"{k}"
        for k, v in smolagents_inputs.items()
    )
    argument = "{" + ", ".join(f"'{k}': {k}" for k in smolagents_inputs.keys()) + "}"

    class_template = f'''
class SmolAgentsTool(smolagents.Tool):
    def __init__(self):
        super().__init__()
        self.name = "{name}"
        self.description = """{description}"""
        self.inputs = {json.dumps(smolagents_inputs)}
        self.output_type = "string"
    
    def forward(self, {forward_params}) -> str:
        """
        Forward method with dynamically generated parameters and argument.
        """
        return func({argument}).content[0].text
'''.strip()

    return class_template


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
        class_template = _generate_tool_class(
            mcp_tool.name, mcp_tool.description, mcp_tool.inputSchema
        )

        # Create namespace and execute the class definition
        namespace = {"smolagents": smolagents, "func": func}
        exec(class_template, namespace)

        # Get the class from namespace and instantiate it
        tool = namespace["SmolAgentsTool"]()
        return tool


if __name__ == "__main__":
    from mcp import StdioServerParameters

    from mcpadapt.core import MCPAdapt

    with MCPAdapt(
        StdioServerParameters(command="uv", args=["run", "src/echo.py"]),
        SmolAgentsAdapter(),
    ) as tools:
        print(tools)
