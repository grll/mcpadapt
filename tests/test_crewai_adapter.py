import ast
import re

from textwrap import dedent

import pytest
from mcp import StdioServerParameters

from mcpadapt.core import MCPAdapt
from mcpadapt.crewai_adapter import CrewAIAdapter
from tests._server_utils import launch_mcp_server, terminate_mcp_server


def extract_and_eval_dict(text):
    # Match the first outermost curly brace block
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("No dictionary-like structure found in the string.")

    dict_str = match.group(0)

    try:
        # Safer than eval for parsing literals
        parsed_dict = ast.literal_eval(dict_str)
        return parsed_dict
    except Exception as e:
        raise ValueError(f"Failed to evaluate dictionary: {e}")


@pytest.fixture
def echo_server_script():
    return dedent(
        '''
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP("Echo Server")

        @mcp.tool()
        def echo_tool(text: str) -> str:
            """Echo the input text"""
            return f"Echo: {text}"
        
        mcp.run()
        '''
    )


@pytest.fixture
def custom_script_with_custom_arguments():
    return dedent(
        """
        from mcp.server.fastmcp import FastMCP
        from typing import Literal
        from enum import Enum
        from pydantic import BaseModel

        class Animal(BaseModel):
            legs: int
            name: str

        mcp = FastMCP("Server")

        @mcp.tool()
        def custom_tool(
            text: Literal["ciao", "hello"],
            animal: Animal,
            env: str | None = None,

        ) -> str:
            pass

        mcp.run()
        """
    )


@pytest.fixture
def custom_script_with_custom_list():
    return dedent(
        """
        from mcp.server.fastmcp import FastMCP
        from pydantic import BaseModel

        class Point(BaseModel):
            x: float
            y: float

        mcp = FastMCP("Server")

        @mcp.tool()
        def custom_tool(
            points: list[Point],

        ) -> str:
            pass

        mcp.run()
        """
    )


@pytest.fixture
def echo_server_sse_script():
    return dedent(
        '''
        import os
        from mcp.server.fastmcp import FastMCP

        port = int(os.environ.get("MCP_TEST_PORT", "8000"))

        mcp = FastMCP("Echo Server", host="127.0.0.1", port=port)

        @mcp.tool()
        def echo_tool(text: str) -> str:
            """Echo the input text"""
            return f"Echo: {text}"

        mcp.run("sse")
        '''
    )


@pytest.fixture
def echo_server_optional_script():
    return dedent(
        '''
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP("Echo Server")

        @mcp.tool()
        def echo_tool_optional(text: str | None = None) -> str:
            """Echo the input text, or return a default message if no text is provided"""
            if text is None:
                return "No input provided"
            return f"Echo: {text}"

        @mcp.tool()
        def echo_tool_default_value(text: str = "empty") -> str:
            """Echo the input text, default to 'empty' if no text is provided"""
            return f"Echo: {text}"

        @mcp.tool()
        def echo_tool_union_none(text: str | None) -> str:
            """Echo the input text, but None is not specified by default."""
            if text is None:
                return "No input provided"
            return f"Echo: {text}"
        
        mcp.run()
        '''
    )


@pytest.fixture
async def echo_sse_server(echo_server_sse_script):
    try:
        process, port = launch_mcp_server(echo_server_sse_script)
    except RuntimeError as exc:
        pytest.skip(str(exc))

    try:
        yield {"url": f"http://127.0.0.1:{port}/sse"}
    finally:
        terminate_mcp_server(process)


def test_basic_sync(echo_server_script):
    with MCPAdapt(
        StdioServerParameters(
            command="uv", args=["run", "python", "-c", echo_server_script]
        ),
        CrewAIAdapter(),
    ) as tools:
        assert len(tools) == 1
        assert tools[0].name == "echo_tool"
        assert tools[0].run(text="hello") == "Echo: hello"


# Fails if enums, unions, or pydantic classes are not included in the
# generated schema
def test_basic_sync_custom_arguments(custom_script_with_custom_arguments):
    with MCPAdapt(
        StdioServerParameters(
            command="uv",
            args=["run", "python", "-c", custom_script_with_custom_arguments],
        ),
        CrewAIAdapter(),
    ) as tools:
        tools_dict = extract_and_eval_dict(tools[0].description)
        assert tools_dict != {}
        assert tools_dict["properties"] != {}
        # Enum tests
        assert "enum" in tools_dict["properties"]["text"]
        assert "hello" in tools_dict["properties"]["text"]["enum"]
        assert "ciao" in tools_dict["properties"]["text"]["enum"]
        # Pydantic class tests
        assert tools_dict["properties"]["animal"]["properties"] != {}
        assert tools_dict["properties"]["animal"]["properties"]["legs"] != {}
        assert tools_dict["properties"]["animal"]["properties"]["name"] != {}
        # Union tests
        assert "anyOf" in tools_dict["properties"]["env"]
        assert tools_dict["properties"]["env"]["anyOf"] != []
        types = [opt.get("type") for opt in tools_dict["properties"]["env"]["anyOf"]]
        assert "null" in types
        assert "string" in types


# Raises KeyError
# if the pydantic objects list is not correctly resolved with $ref handling
# within mcp_tool.inputSchema
def test_basic_sync_custom_list(custom_script_with_custom_list):
    with MCPAdapt(
        StdioServerParameters(
            command="uv", args=["run", "python", "-c", custom_script_with_custom_list]
        ),
        CrewAIAdapter(),
    ) as tools:
        tools_dict = extract_and_eval_dict(tools[0].description)
        assert tools_dict != {}
        assert tools_dict["properties"] != {}
        # Pydantic class tests
        assert tools_dict["properties"]["points"]["items"] != {}


def test_basic_sync_sse(echo_sse_server):
    sse_serverparams = echo_sse_server
    with MCPAdapt(
        sse_serverparams,
        CrewAIAdapter(),
    ) as tools:
        assert len(tools) == 1
        assert tools[0].name == "echo_tool"
        assert tools[0].run(text="hello") == "Echo: hello"


def test_optional_sync(echo_server_optional_script):
    with MCPAdapt(
        StdioServerParameters(
            command="uv", args=["run", "python", "-c", echo_server_optional_script]
        ),
        CrewAIAdapter(),
    ) as tools:
        assert len(tools) == 3
        assert tools[0].name == "echo_tool_optional"
        assert tools[0].run(text="hello") == "Echo: hello"
        assert tools[0].run() == "No input provided"
        assert tools[1].name == "echo_tool_default_value"
        assert tools[1].run(text="hello") == "Echo: hello"
        assert tools[1].run() == "Echo: empty"
        assert tools[2].name == "echo_tool_union_none"
        assert tools[2].run(text="hello") == "Echo: hello"


@pytest.fixture
def mcp_server_that_rejects_none_script():
    return dedent(
        """
        import mcp.types as types
        from mcp.server.lowlevel import Server
        from mcp.server.stdio import stdio_server
        import anyio

        app = Server("mcp-strict-server")

        @app.call_tool()
        async def call_tool(name: str, arguments: dict | None) -> list[types.TextContent]:
            if name != "strict_tool":
                raise ValueError(f"Unknown tool: {name}")
            
            # Simulate GitHub MCP server behavior - reject None values
            if arguments:
                for key, value in arguments.items():
                    if value is None:
                        # MCP servers that reject None values raise an error
                        raise RuntimeError(f"parameter {key} is not of type string, is <nil>")
            
            required = arguments.get("required") if arguments else None
            optional = arguments.get("optional") if arguments else None  
            another_optional = arguments.get("another_optional") if arguments else None
            
            return [types.TextContent(
                type="text",
                text=f"Required: {required}, Optional: {optional}, Another: {another_optional}"
            )]

        @app.list_tools()
        async def list_tools() -> list[types.Tool]:
            return [
                types.Tool(
                    name="strict_tool",
                    description="A tool that expects only string values",
                    inputSchema={
                        "type": "object",
                        "required": ["required"],
                        "properties": {
                            "required": {
                                "type": "string",
                                "description": "Required parameter",
                            },
                            "optional": {
                                "type": "string", 
                                "description": "Optional parameter",
                            },
                            "another_optional": {
                                "type": "string",
                                "description": "Another optional parameter",
                            }
                        },
                    },
                )
            ]

        async def arun():
            async with stdio_server() as streams:
                await app.run(
                    streams[0], streams[1], app.create_initialization_options()
                )

        anyio.run(arun)
        """
    )


def test_none_values_filtered_from_kwargs(mcp_server_that_rejects_none_script):
    """Test that None values are filtered out before being sent to MCP tool.

    This test reproduces issue #46 where None values in kwargs cause MCP servers
    to reject the request with 'parameter is not of type string, is <nil>' error.
    """
    with MCPAdapt(
        StdioServerParameters(
            command="uv",
            args=["run", "python", "-c", mcp_server_that_rejects_none_script],
        ),
        CrewAIAdapter(),
    ) as tools:
        assert len(tools) == 1
        tool = tools[0]
        assert tool.name == "strict_tool"

        # This should work - only required parameter
        result = tool.run(required="test")
        assert "Required: test" in result

        # This should work - explicit non-None values
        result = tool.run(required="test", optional="value1", another_optional="value2")
        assert "Required: test" in result
        assert "Optional: value1" in result
        assert "Another: value2" in result

        # After the fix - CrewAI passes None values but they are filtered out
        # before being sent to the MCP server if the schema doesn't allow null
        result = tool.run(required="test", optional=None, another_optional=None)

        # The fix filters out None values, so the server receives only {"required": "test"}
        # and returns a successful response with None for the optional parameters
        assert "Required: test" in result
        assert "Optional: None" in result
        assert "Another: None" in result
        # Most importantly, no error message about "is not of type string, is <nil>"
        assert "parameter" not in result or "is <nil>" not in result


@pytest.fixture
def multiple_content_server_script():
    return dedent(
        """
        import mcp.types as types
        from mcp.server.lowlevel import Server
        from mcp.server.stdio import stdio_server
        import anyio

        app = Server("multiple-content-server")

        @app.call_tool()
        async def call_tool(name: str, arguments: dict | None) -> list[types.TextContent]:
            if name != "multiple_content_tool":
                raise ValueError(f"Unknown tool: {name}")

            # Return multiple content responses
            return [
                types.TextContent(type="text", text="First response"),
                types.TextContent(type="text", text="Second response"),
                types.TextContent(type="text", text="Third response")
            ]

        @app.list_tools()
        async def list_tools() -> list[types.Tool]:
            return [
                types.Tool(
                    name="multiple_content_tool",
                    description="A tool that returns multiple content items",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                    },
                )
            ]

        async def arun():
            async with stdio_server() as streams:
                await app.run(
                    streams[0], streams[1], app.create_initialization_options()
                )

        anyio.run(arun)
        """
    )


def test_multiple_content_response_handling(multiple_content_server_script):
    """Test that multiple content responses return a string representation of the list."""
    with MCPAdapt(
        StdioServerParameters(
            command="uv",
            args=["run", "python", "-c", multiple_content_server_script],
        ),
        CrewAIAdapter(),
    ) as tools:
        assert len(tools) == 1
        tool = tools[0]
        assert tool.name == "multiple_content_tool"

        result = tool.run()
        # Should return string representation of list of text contents
        expected = str(["First response", "Second response", "Third response"])
        assert result == expected


@pytest.fixture
def empty_union_server_script():
    """Server that returns a tool with a schema containing only null types in anyOf."""
    return dedent(
        """
        import mcp.types as types
        from mcp.server.lowlevel import Server
        from mcp.server.stdio import stdio_server
        import anyio

        app = Server("empty-union-server")

        @app.list_tools()
        async def list_tools() -> list[types.Tool]:
            return [
                types.Tool(
                    name="problematic_tool",
                    description="Tool with empty union after null filtering",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "nullable_only": {
                                "anyOf": [
                                    {"type": "null"}
                                ]
                            },
                            "type_array_null_only": {
                                "type": ["null"]
                            }
                        },
                    },
                )
            ]

        @app.call_tool()
        async def call_tool(name: str, arguments: dict | None) -> list[types.TextContent]:
            return [types.TextContent(type="text", text="Success")]

        async def arun():
            async with stdio_server() as streams:
                await app.run(
                    streams[0], streams[1], app.create_initialization_options()
                )

        anyio.run(arun)
        """
    )


def test_empty_union_type_error(empty_union_server_script):
    """Test that empty unions (anyOf with only null types) do not raise TypeError.

    This test reproduced issue #71 where schemas with anyOf containing only
    null types cause 'Cannot take a Union of no types' error.
    """
    with MCPAdapt(
        StdioServerParameters(
            command="uv",
            args=["run", "python", "-c", empty_union_server_script],
        ),
        CrewAIAdapter(),
    ) as tools:
        assert len(tools) == 1
