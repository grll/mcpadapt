import ast
import re

from textwrap import dedent

import pytest
from mcp import StdioServerParameters

from mcpadapt.core import MCPAdapt
from mcpadapt.crewai_adapter import CrewAIAdapter


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
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP("Echo Server", host="127.0.0.1", port=8000)

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
    import subprocess
    import time

    # Start the SSE server process with its own process group
    process = subprocess.Popen(
        ["python", "-c", echo_server_sse_script],
    )

    # Give the server a moment to start up
    time.sleep(1)

    try:
        yield {"url": "http://127.0.0.1:8000/sse"}
    finally:
        # Clean up the process when test is done
        process.kill()
        process.wait()


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
