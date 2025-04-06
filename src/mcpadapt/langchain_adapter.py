"""This module implements the LangChain adapter.

LangChain tools support both sync and async functions for their tools so we can
leverage both in our implementation.

Example Usage:
>>> with MCPAdapt(StdioServerParameters(command="uv", args=["run", "src/echo.py"]), LangChainAdapter()) as tools:
>>>     print(tools)
"""

import keyword
import logging
import re
from functools import partial
from typing import Any, Callable, Coroutine

import jsonref
import langchain_core
import mcp
from langchain.tools import BaseTool

from mcpadapt.core import ToolAdapter

log = logging.getLogger(__name__)

JSON_SCHEMA_TO_PYTHON_TYPES = {
    "string": "str",
    "number": "float",
    "integer": "int",
    "object": "dict",
    "array": "list",
    "boolean": "bool",
    "null": "None",
}


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


def _generate_tool_class(
    name: str,
    description: str,
    input_schema: dict[str, Any],
    async_func: bool = False,
    parse_docstring: bool = True,
) -> str:
    """Generate a tool BaseTool class for `langchain` from MCP tool information.

    Note we use the simpliest '@tool' decorator for now.

    Args:
        name: the name of the tool as used in the MCP protocol
        description: the description of the tool as used in the MCP protocol
        input_schema: the input schema of the tool as used in the MCP protocol
        async_func: whether the function is async or not
        parse_docstring: whether to parse the docstring as a Google-Style docstring

    Returns:
        the generated langchain tool class as a string to be executed with exec.
    """
    resolved_json_schema = jsonref.replace_refs(input_schema)
    properties = resolved_json_schema.get("properties", {})

    # construct typed signature based on input schema
    # TODO: this could be better and handle nested objects...
    tool_params = []
    for k, v in properties.items():
        tool_params.append(f"{k}: {JSON_SCHEMA_TO_PYTHON_TYPES[v['type']]}")
    tool_params = ", ".join(tool_params)

    argument = "{" + ", ".join(f"'{k}': {k}" for k in properties.keys()) + "}"

    # change def statement and return statement based on async_func
    def_statement = "def"
    return_statement = f"return func({argument}).content[0].text"
    if async_func:
        def_statement = "async def"
        return_statement = f"return (await func({argument})).content[0].text"

    # define the decorator based on parse_docstring
    decorator = "@tool(parse_docstring=True)" if parse_docstring else "@tool"

    class_template = f'''
{decorator}
{def_statement} {name}({tool_params}) -> str:
    """{description}"""
    {return_statement}
'''.strip()

    return class_template


def _instanciate_tool(
    mcp_tool_name: str,
    generate_class_template: Callable[[bool], str],
    func: Callable[[dict | None], mcp.types.CallToolResult]
    | Callable[[dict | None], Coroutine[Any, Any, mcp.types.CallToolResult]],
) -> BaseTool:
    """Instanciate a tool from a class template and a function wrapping the mcp tool_call.

    Args:
        mcp_tool_name: the name of the tool as used in the MCP protocol
        generate_class_template: a function that generates the class template
            (with or without parsing the docstring)
        func: the function wrapping the mcp tool_call

    Returns:
        the instanciated langchain tool
    """

    # Create namespace and execute the class definition
    namespace = {"tool": langchain_core.tools.tool, "func": func}
    try:
        exec(generate_class_template(True), namespace)
    except ValueError as e:
        if "Found invalid Google-Style docstring." in str(e):
            exec(generate_class_template(False), namespace)

    # Get the class from namespace and instantiate it
    tool = namespace[mcp_tool_name]
    return tool


class LangChainAdapter(ToolAdapter):
    """Adapter for `langchain`.

    Note that `langchain` support both sync and async tools so we
    write adapt for both methods.

    Warning: if the mcp tool name is a python keyword, starts with digits or contains
    dashes, the tool name will be sanitized to become a valid python function name.

    """

    def adapt(
        self,
        func: Callable[[dict | None], mcp.types.CallToolResult],
        mcp_tool: mcp.types.Tool,
    ) -> BaseTool:
        """Adapt a MCP tool to a LangChain tool.

        Args:
            func: The function to adapt.
            mcp_tool: The MCP tool to adapt.

        Returns:
            A LangChain tool.
        """
        mcp_tool_name = _sanitize_function_name(mcp_tool.name)

        generate_class_template = partial(
            _generate_tool_class,
            mcp_tool_name,
            mcp_tool.description,
            mcp_tool.inputSchema,
            False,
        )
        return _instanciate_tool(mcp_tool_name, generate_class_template, func)

    def async_adapt(
        self,
        afunc: Callable[[dict | None], Coroutine[Any, Any, mcp.types.CallToolResult]],
        mcp_tool: mcp.types.Tool,
    ) -> BaseTool:
        """Adapt a MCP tool to a LangChain tool.

        Args:
            afunc: The function to adapt.
            mcp_tool: The MCP tool to adapt.

        Returns:
            A LangChain tool.
        """
        mcp_tool_name = _sanitize_function_name(mcp_tool.name)
        if mcp_tool_name != mcp_tool.name:
            log.warning(f"MCP tool name {mcp_tool.name} sanitized to {mcp_tool_name}")

        generate_class_template = partial(
            _generate_tool_class,
            mcp_tool_name,
            mcp_tool.description,
            mcp_tool.inputSchema,
            True,
        )
        return _instanciate_tool(mcp_tool_name, generate_class_template, afunc)


if __name__ == "__main__":
    import asyncio

    from mcp import StdioServerParameters

    from mcpadapt.core import MCPAdapt

    with MCPAdapt(
        StdioServerParameters(command="uv", args=["run", "src/echo.py"]),
        LangChainAdapter(),
    ) as tools:
        print(tools)
        print(tools[0].invoke("hello"))

    async def main():
        async with MCPAdapt(
            StdioServerParameters(command="uv", args=["run", "src/echo.py"]),
            LangChainAdapter(),
        ) as tools:
            print(tools)
            print(await tools[0].ainvoke("hello"))

    asyncio.run(main())
