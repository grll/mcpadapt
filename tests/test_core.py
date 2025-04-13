from textwrap import dedent
from typing import Any, Callable, Coroutine

import mcp
import pytest
from mcp import StdioServerParameters

from mcpadapt.core import MCPAdapt, ToolAdapter


class DummyAdapter(ToolAdapter):
    """A dummy adapter that returns the function as is"""

    def adapt(
        self,
        func: Callable[[dict | None], mcp.types.CallToolResult],
        mcp_tool: mcp.types.Tool,
    ):
        return func

    def async_adapt(
        self,
        afunc: Callable[[dict | None], Coroutine[Any, Any, mcp.types.CallToolResult]],
        mcp_tool: mcp.types.Tool,
    ):
        return afunc


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
        DummyAdapter(),
    ) as tools:
        assert len(tools) == 1
        assert tools[0]({"text": "hello"}).content[0].text == "Echo: hello"


def test_basic_sync_multiple_tools(echo_server_script):
    with MCPAdapt(
        [
            StdioServerParameters(
                command="uv", args=["run", "python", "-c", echo_server_script]
            ),
            StdioServerParameters(
                command="uv", args=["run", "python", "-c", echo_server_script]
            ),
        ],
        DummyAdapter(),
    ) as tools:
        assert len(tools) == 2
        assert tools[0]({"text": "hello"}).content[0].text == "Echo: hello"
        assert tools[1]({"text": "world"}).content[0].text == "Echo: world"


async def test_basic_async(echo_server_script):
    async with MCPAdapt(
        StdioServerParameters(
            command="uv", args=["run", "python", "-c", echo_server_script]
        ),
        DummyAdapter(),
    ) as tools:
        assert len(tools) == 1
        mcp_tool_call_result = await tools[0]({"text": "hello"})
        assert mcp_tool_call_result.content[0].text == "Echo: hello"


async def test_basic_async_multiple_tools(echo_server_script):
    async with MCPAdapt(
        [
            StdioServerParameters(
                command="uv", args=["run", "python", "-c", echo_server_script]
            ),
            StdioServerParameters(
                command="uv", args=["run", "python", "-c", echo_server_script]
            ),
        ],
        DummyAdapter(),
    ) as tools:
        assert len(tools) == 2
        mcp_tool_call_result = await tools[0]({"text": "hello"})
        assert mcp_tool_call_result.content[0].text == "Echo: hello"
        mcp_tool_call_result = await tools[1]({"text": "world"})
        assert mcp_tool_call_result.content[0].text == "Echo: world"


def test_basic_sync_sse(echo_sse_server):
    sse_serverparams = echo_sse_server
    with MCPAdapt(
        sse_serverparams,
        DummyAdapter(),
    ) as tools:
        assert len(tools) == 1
        assert tools[0]({"text": "hello"}).content[0].text == "Echo: hello"


def test_basic_sync_multiple_sse(echo_sse_server):
    sse_serverparams = echo_sse_server
    with MCPAdapt(
        [sse_serverparams, sse_serverparams],
        DummyAdapter(),
    ) as tools:
        assert len(tools) == 2
        assert tools[0]({"text": "hello"}).content[0].text == "Echo: hello"
        assert tools[1]({"text": "world"}).content[0].text == "Echo: world"


async def test_basic_async_sse(echo_sse_server):
    sse_serverparams = echo_sse_server
    async with MCPAdapt(
        sse_serverparams,
        DummyAdapter(),
    ) as tools:
        assert len(tools) == 1
        mcp_tool_call_result = await tools[0]({"text": "hello"})
        assert mcp_tool_call_result.content[0].text == "Echo: hello"


async def test_basic_async_multiple_sse(echo_sse_server):
    sse_serverparams = echo_sse_server
    async with MCPAdapt(
        [sse_serverparams, sse_serverparams],
        DummyAdapter(),
    ) as tools:
        assert len(tools) == 2
        mcp_tool_call_result = await tools[0]({"text": "hello"})
        assert mcp_tool_call_result.content[0].text == "Echo: hello"
        mcp_tool_call_result = await tools[1]({"text": "world"})
        assert mcp_tool_call_result.content[0].text == "Echo: world"
