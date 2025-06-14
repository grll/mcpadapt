import time
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
def update_server_script():
    return dedent(
        '''
        from mcp.server.fastmcp import FastMCP
        
        mcp = FastMCP("Echo Server")
        
        def new_tool(text: str) -> str:
            """New tool"""
            return f"New: {text}"
        
        def update_tool():
            mcp.add_tool(new_tool)
        
        updated = False
        
        @mcp.tool()
        def echo_tool(text: str) -> str:
            """Echo the input text"""
            # update tool when invoke
            global updated
            if not updated:
                update_tool()
                updated = True
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


@pytest.fixture
def echo_server_streamable_http_script():
    return dedent(
        '''
        from mcp.server.fastmcp import FastMCP
        
        mcp = FastMCP("Echo Server", host="127.0.0.1", port=8000, stateless_http=True, json_response=True)
        
        @mcp.tool()
        def echo_tool(text: str) -> str:
            """Echo the input text"""
            return f"Echo: {text}"

        mcp.run("streamable-http")
        '''
    )


@pytest.fixture
async def echo_streamable_http_server(echo_server_streamable_http_script):
    import subprocess

    # Start the SSE server process with its own process group
    process = subprocess.Popen(
        ["python", "-c", echo_server_streamable_http_script],
    )

    # Give the server a moment to start up
    time.sleep(1)

    try:
        yield {"url": "http://127.0.0.1:8000/mcp", "transport": "streamable-http"}
    finally:
        # Clean up the process when test is done
        process.kill()
        process.wait()


@pytest.fixture
def slow_start_server_script():
    return dedent(
        '''
        import time
        from mcp.server.fastmcp import FastMCP

        # Sleep for 2 seconds to simulate slow startup
        time.sleep(2)
        
        mcp = FastMCP("Slow Server")

        @mcp.tool()
        def echo_tool(text: str) -> str:
            """Echo the input text"""
            return f"Echo: {text}"
        
        mcp.run()
        '''
    )


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


def test_basic_sync_update_tools(update_server_script):
    adapter = MCPAdapt(
        StdioServerParameters(
            command="uv", args=["run", "python", "-c", update_server_script]
        ),
        DummyAdapter(),
    )
    with adapter as tools:
        assert len(tools) == 1
        assert tools[0]({"text": "hello"}).content[0].text == "Echo: hello"
        # get latest tools
        tools = adapter.tools()
        assert len(tools) == 2
        # assert all tools are valid
        res = (
            tools[0]({"text": "hello"}).content[0].text,
            tools[1]({"text": "hello"}).content[0].text,
        )
        assert "Echo: hello" in res
        assert "New: hello" in res


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


async def test_basic_async_update_tools(update_server_script):
    adapter = MCPAdapt(
        StdioServerParameters(
            command="uv", args=["run", "python", "-c", update_server_script]
        ),
        DummyAdapter(),
    )
    async with adapter as tools:
        assert len(tools) == 1
        assert (await tools[0]({"text": "hello"})).content[0].text == "Echo: hello"
        # get latest tools
        tools = await adapter.atools()
        assert len(tools) == 2
        # assert all tools are valid
        res = (
            (await tools[0]({"text": "hello"})).content[0].text,
            (await tools[1]({"text": "hello"})).content[0].text,
        )
        assert "Echo: hello" in res
        assert "New: hello" in res


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


def test_basic_sync_streamable_http(echo_streamable_http_server):
    http_serverparams = echo_streamable_http_server
    with MCPAdapt(
        http_serverparams,
        DummyAdapter(),
    ) as tools:
        assert len(tools) == 1
        assert tools[0]({"text": "hello"}).content[0].text == "Echo: hello"


async def test_basic_async_streamable_http(echo_streamable_http_server):
    http_serverparams = echo_streamable_http_server
    async with MCPAdapt(
        http_serverparams,
        DummyAdapter(),
    ) as tools:
        assert len(tools) == 1
        assert (await tools[0]({"text": "hello"})).content[0].text == "Echo: hello"


def test_connect_timeout(slow_start_server_script):
    """Test that connect_timeout raises TimeoutError when server starts slowly"""
    with pytest.raises(
        TimeoutError, match="Couldn't connect to the MCP server after 1 seconds"
    ):
        with MCPAdapt(
            StdioServerParameters(
                command="uv", args=["run", "python", "-c", slow_start_server_script]
            ),
            DummyAdapter(),
            connect_timeout=1,  # 1 second timeout, server takes 2 seconds to start
        ):
            pass


def test_client_session_timeout_parameter_propagation(echo_server_script):
    """Test that client_session_timeout_seconds parameter is properly stored and accessible"""
    from datetime import timedelta

    # Test with float value
    adapter_float = MCPAdapt(
        StdioServerParameters(
            command="uv", args=["run", "python", "-c", echo_server_script]
        ),
        DummyAdapter(),
        client_session_timeout_seconds=2.5,
    )
    assert adapter_float.client_session_timeout_seconds == 2.5

    # Test with timedelta value
    timeout_td = timedelta(seconds=3.0)
    adapter_td = MCPAdapt(
        StdioServerParameters(
            command="uv", args=["run", "python", "-c", echo_server_script]
        ),
        DummyAdapter(),
        client_session_timeout_seconds=timeout_td,
    )
    assert adapter_td.client_session_timeout_seconds == timeout_td

    # Test with None value
    adapter_none = MCPAdapt(
        StdioServerParameters(
            command="uv", args=["run", "python", "-c", echo_server_script]
        ),
        DummyAdapter(),
        client_session_timeout_seconds=None,
    )
    assert adapter_none.client_session_timeout_seconds is None

    # Test default value
    adapter_default = MCPAdapt(
        StdioServerParameters(
            command="uv", args=["run", "python", "-c", echo_server_script]
        ),
        DummyAdapter(),
    )
    assert adapter_default.client_session_timeout_seconds == 5
