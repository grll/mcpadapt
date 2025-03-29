from textwrap import dedent

import pytest
from mcp import StdioServerParameters

from mcpadapt.core import MCPAdapt
from mcpadapt.google_genai_adapter import GoogleGenAIAdapter


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
        GoogleGenAIAdapter(),
    ) as adapted_tools:
        tools, tool_functions = zip(*adapted_tools)
        tool_functions = dict(tool_functions)
        assert len(tools) == 1
        assert tools[0].function_declarations[0].name == "echo_tool"
        assert (
            tool_functions["echo_tool"]({"text": "hello"}).content[0].text
            == "Echo: hello"
        )


def test_basic_sync_sse(echo_sse_server):
    sse_serverparams = echo_sse_server
    with MCPAdapt(
        sse_serverparams,
        GoogleGenAIAdapter(),
    ) as adapted_tools:
        tools, tool_functions = zip(*adapted_tools)
        tool_functions = dict(tool_functions)
        assert len(tools) == 1
        assert tools[0].function_declarations[0].name == "echo_tool"
        assert (
            tool_functions["echo_tool"]({"text": "hello"}).content[0].text
            == "Echo: hello"
        )


def test_optional_sync(echo_server_optional_script):
    with MCPAdapt(
        StdioServerParameters(
            command="uv", args=["run", "python", "-c", echo_server_optional_script]
        ),
        GoogleGenAIAdapter(),
    ) as adapted_tools:
        tools, tool_functions = zip(*adapted_tools)
        tool_functions = dict(tool_functions)
        assert len(tools) == 3
        assert tools[0].function_declarations[0].name == "echo_tool_optional"
        assert (
            tool_functions["echo_tool_optional"]({"text": "hello"}).content[0].text
            == "Echo: hello"
        )
        assert (
            tool_functions["echo_tool_optional"]({}).content[0].text
            == "No input provided"
        )
        assert tools[1].function_declarations[0].name == "echo_tool_default_value"
        assert (
            tool_functions["echo_tool_default_value"]({"text": "hello"}).content[0].text
            == "Echo: hello"
        )
        assert (
            tool_functions["echo_tool_default_value"]({}).content[0].text
            == "Echo: empty"
        )
        assert tools[2].function_declarations[0].name == "echo_tool_union_none"
        assert (
            tool_functions["echo_tool_union_none"]({"text": "hello"}).content[0].text
            == "Echo: hello"
        )
