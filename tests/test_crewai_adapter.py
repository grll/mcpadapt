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
def complex_types_server_script():
    return dedent(
        '''
        from mcp.server.fastmcp import FastMCP
        from typing import Dict, List, Optional

        mcp = FastMCP("Complex Types Server")

        @mcp.tool()
        def tool_with_object(config: Dict[str, str]) -> str:
            """Tool that takes an object parameter"""
            return f"Received config with {len(config)} keys"

        @mcp.tool()
        def tool_with_optional_object(config: Optional[Dict[str, str]] = None) -> str:
            """Tool that takes an optional object parameter"""
            if config is None:
                return "No config provided"
            return f"Received config with {len(config)} keys"

        @mcp.tool()
        def tool_with_number(value: float) -> str:
            """Tool that takes a number parameter"""
            return f"Received value: {value}"

        @mcp.tool()
        def tool_with_optional_number(value: Optional[float] = None) -> str:
            """Tool that takes an optional number parameter"""
            if value is None:
                return "No value provided"
            return f"Received value: {value}"

        mcp.run()
        '''
    )


@pytest.fixture
def nested_objects_server_script():
    return dedent(
        '''
        from mcp.server.fastmcp import FastMCP
        from typing import Dict, Optional, List, Any

        mcp = FastMCP("Nested Objects Server")

        @mcp.tool()
        def tool_with_nested_objects(config: Dict[str, Dict[str, Any]]) -> str:
            """Tool that takes a nested object parameter"""
            return f"Received config with {len(config)} sections"

        @mcp.tool()
        def tool_with_optional_nested(config: Optional[Dict[str, Optional[Dict[str, Any]]]] = None) -> str:
            """Tool that takes an optional nested object parameter with optional inner objects"""
            if config is None:
                return "No config provided"
            sections = sum(1 for v in config.values() if v is not None)
            return f"Received config with {sections} valid sections"

        mcp.run()
        '''
    )


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


def test_object_parameters_sync(complex_types_server_script):
    with MCPAdapt(
        StdioServerParameters(
            command="uv", args=["run", "python", "-c", complex_types_server_script]
        ),
        CrewAIAdapter(),
    ) as tools:
        # Test required object parameter
        tool_with_object = [t for t in tools if t.name == "tool_with_object"][0]
        assert (
            tool_with_object.run(config={"key": "value"})
            == "Received config with 1 keys"
        )

        # This should raise a validation error since None is not a dict
        with pytest.raises(ValueError):  # Or appropriate exception from Pydantic
            tool_with_object.run(config=None)

        # Test optional object parameter
        tool_with_optional_object = [
            t for t in tools if t.name == "tool_with_optional_object"
        ][0]
        assert (
            tool_with_optional_object.run(config={"key": "value"})
            == "Received config with 1 keys"
        )
        assert tool_with_optional_object.run() == "No config provided"  # Default None
        assert (
            tool_with_optional_object.run(config=None) == "No config provided"
        )  # Explicit None


def test_number_parameters_sync(complex_types_server_script):
    with MCPAdapt(
        StdioServerParameters(
            command="uv", args=["run", "python", "-c", complex_types_server_script]
        ),
        CrewAIAdapter(),
    ) as tools:
        # Test required number parameter
        tool_with_number = [t for t in tools if t.name == "tool_with_number"][0]
        assert tool_with_number.run(value=42.5) == "Received value: 42.5"

        # This should raise a validation error since None is not a number
        with pytest.raises(ValueError):  # Or appropriate exception from Pydantic
            tool_with_number.run(value=None)

        # Test optional number parameter
        tool_with_optional_number = [
            t for t in tools if t.name == "tool_with_optional_number"
        ][0]
        assert tool_with_optional_number.run(value=42.5) == "Received value: 42.5"
        assert tool_with_optional_number.run() == "No value provided"  # Default None
        assert (
            tool_with_optional_number.run(value=None) == "No value provided"
        )  # Explicit None


def test_nested_objects_sync(nested_objects_server_script):
    with MCPAdapt(
        StdioServerParameters(
            command="uv", args=["run", "python", "-c", nested_objects_server_script]
        ),
        CrewAIAdapter(),
    ) as tools:
        # Test nested objects parameter
        tool_with_nested_objects = [
            t for t in tools if t.name == "tool_with_nested_objects"
        ][0]
        assert (
            tool_with_nested_objects.run(
                config={"section1": {"key1": "value1"}, "section2": {"key2": "value2"}}
            )
            == "Received config with 2 sections"
        )

        # Test optional nested parameter
        tool_with_optional_nested = [
            t for t in tools if t.name == "tool_with_optional_nested"
        ][0]

        # Test with fully populated nested objects
        assert (
            tool_with_optional_nested.run(
                config={"section1": {"key1": "value1"}, "section2": {"key2": "value2"}}
            )
            == "Received config with 2 valid sections"
        )

        # Test with some null inner objects
        assert (
            tool_with_optional_nested.run(
                config={"section1": {"key1": "value1"}, "section2": None}
            )
            == "Received config with 1 valid sections"
        )

        # Test with null outer object
        assert tool_with_optional_nested.run() == "No config provided"
