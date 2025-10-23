"""
Test cases for fault tolerance features in MCPAdapt.

This module tests the fail_fast, on_connection_error, and failed_connections
tracking features added to improve fault tolerance when connecting to multiple
MCP servers.
"""

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
def failing_server_script():
    """A script that fails to start"""
    return dedent(
        """
        import sys
        # Exit immediately to simulate a failing server
        sys.exit(1)
        """
    )


# ========== Synchronous Tests ==========


def test_fail_fast_default_behavior(failing_server_script):
    """Test that fail_fast=True (default) raises exception when server fails"""
    with pytest.raises(Exception):
        with MCPAdapt(
            StdioServerParameters(
                command="uv", args=["run", "python", "-c", failing_server_script]
            ),
            DummyAdapter(),
        ):
            pass


def test_fail_fast_true_explicit(failing_server_script):
    """Test that fail_fast=True explicitly set raises exception when server fails"""
    with pytest.raises(Exception):
        with MCPAdapt(
            StdioServerParameters(
                command="uv", args=["run", "python", "-c", failing_server_script]
            ),
            DummyAdapter(),
            fail_fast=True,
        ):
            pass


def test_fail_fast_false_single_failing_server(failing_server_script):
    """Test that fail_fast=False with single failing server returns empty tools"""
    with MCPAdapt(
        StdioServerParameters(
            command="uv", args=["run", "python", "-c", failing_server_script]
        ),
        DummyAdapter(),
        fail_fast=False,
    ) as tools:
        assert len(tools) == 0


def test_fail_fast_false_mixed_servers(echo_server_script, failing_server_script):
    """Test that fail_fast=False skips failing server and uses successful one"""
    with MCPAdapt(
        [
            StdioServerParameters(
                command="uv", args=["run", "python", "-c", failing_server_script]
            ),
            StdioServerParameters(
                command="uv", args=["run", "python", "-c", echo_server_script]
            ),
        ],
        DummyAdapter(),
        fail_fast=False,
    ) as tools:
        # Should only have tools from the successful server
        assert len(tools) == 1
        assert tools[0]({"text": "hello"}).content[0].text == "Echo: hello"


def test_fail_fast_false_multiple_mixed_servers(
    echo_server_script, failing_server_script
):
    """Test that fail_fast=False works with multiple failing and successful servers"""
    with MCPAdapt(
        [
            StdioServerParameters(
                command="uv", args=["run", "python", "-c", failing_server_script]
            ),
            StdioServerParameters(
                command="uv", args=["run", "python", "-c", echo_server_script]
            ),
            StdioServerParameters(
                command="uv", args=["run", "python", "-c", failing_server_script]
            ),
            StdioServerParameters(
                command="uv", args=["run", "python", "-c", echo_server_script]
            ),
        ],
        DummyAdapter(),
        fail_fast=False,
    ) as tools:
        # Should have tools from the 2 successful servers
        assert len(tools) == 2
        assert tools[0]({"text": "hello"}).content[0].text == "Echo: hello"
        assert tools[1]({"text": "world"}).content[0].text == "Echo: world"


def test_on_connection_error_callback(failing_server_script):
    """Test that on_connection_error callback is called when connection fails"""
    callback_invocations = []

    def error_callback(server_params, exception):
        callback_invocations.append((server_params, exception))

    with MCPAdapt(
        StdioServerParameters(
            command="uv", args=["run", "python", "-c", failing_server_script]
        ),
        DummyAdapter(),
        fail_fast=False,
        on_connection_error=error_callback,
    ):
        pass

    # Callback should have been called once
    assert len(callback_invocations) == 1
    server_params, exception = callback_invocations[0]
    assert isinstance(server_params, StdioServerParameters)
    assert isinstance(exception, Exception)


def test_on_connection_error_callback_multiple_failures(
    echo_server_script, failing_server_script
):
    """Test that on_connection_error is called for each failed connection"""
    callback_invocations = []

    def error_callback(server_params, exception):
        callback_invocations.append((server_params, exception))

    with MCPAdapt(
        [
            StdioServerParameters(
                command="uv", args=["run", "python", "-c", failing_server_script]
            ),
            StdioServerParameters(
                command="uv", args=["run", "python", "-c", echo_server_script]
            ),
            StdioServerParameters(
                command="uv", args=["run", "python", "-c", failing_server_script]
            ),
        ],
        DummyAdapter(),
        fail_fast=False,
        on_connection_error=error_callback,
    ) as tools:
        assert len(tools) == 1

    # Callback should have been called twice (for two failing servers)
    assert len(callback_invocations) == 2
    for server_params, exception in callback_invocations:
        assert isinstance(server_params, StdioServerParameters)
        assert isinstance(exception, Exception)


def test_failed_connections_tracking(failing_server_script):
    """Test that failed_connections list tracks failed connections"""
    adapter = MCPAdapt(
        StdioServerParameters(
            command="uv", args=["run", "python", "-c", failing_server_script]
        ),
        DummyAdapter(),
        fail_fast=False,
    )

    with adapter:
        pass

    # Should have one failed connection tracked
    assert len(adapter.failed_connections) == 1
    server_params, exception = adapter.failed_connections[0]
    assert isinstance(server_params, StdioServerParameters)
    assert isinstance(exception, Exception)


def test_failed_connections_tracking_mixed(echo_server_script, failing_server_script):
    """Test that failed_connections tracks only failed connections in mixed scenario"""
    adapter = MCPAdapt(
        [
            StdioServerParameters(
                command="uv", args=["run", "python", "-c", failing_server_script]
            ),
            StdioServerParameters(
                command="uv", args=["run", "python", "-c", echo_server_script]
            ),
            StdioServerParameters(
                command="uv", args=["run", "python", "-c", failing_server_script]
            ),
        ],
        DummyAdapter(),
        fail_fast=False,
    )

    with adapter as tools:
        assert len(tools) == 1

    # Should have two failed connections tracked
    assert len(adapter.failed_connections) == 2
    for server_params, exception in adapter.failed_connections:
        assert isinstance(server_params, StdioServerParameters)
        assert isinstance(exception, Exception)


# ========== Asynchronous Tests ==========


async def test_fail_fast_false_async_mixed_servers(
    echo_server_script, failing_server_script
):
    """Test async context manager with fail_fast=False and mixed servers"""
    async with MCPAdapt(
        [
            StdioServerParameters(
                command="uv", args=["run", "python", "-c", failing_server_script]
            ),
            StdioServerParameters(
                command="uv", args=["run", "python", "-c", echo_server_script]
            ),
        ],
        DummyAdapter(),
        fail_fast=False,
    ) as tools:
        # Should only have tools from the successful server
        assert len(tools) == 1
        result = await tools[0]({"text": "hello"})
        assert result.content[0].text == "Echo: hello"


async def test_fail_fast_false_async_single_failing_server(failing_server_script):
    """Test async context manager with fail_fast=False and single failing server"""
    async with MCPAdapt(
        StdioServerParameters(
            command="uv", args=["run", "python", "-c", failing_server_script]
        ),
        DummyAdapter(),
        fail_fast=False,
    ) as tools:
        assert len(tools) == 0


async def test_fail_fast_true_async_with_failure(failing_server_script):
    """Test async context manager with fail_fast=True raises exception"""
    with pytest.raises(Exception):
        async with MCPAdapt(
            StdioServerParameters(
                command="uv", args=["run", "python", "-c", failing_server_script]
            ),
            DummyAdapter(),
            fail_fast=True,
        ):
            pass


async def test_on_connection_error_callback_async(failing_server_script):
    """Test that on_connection_error callback works in async context"""
    callback_invocations = []

    def error_callback(server_params, exception):
        callback_invocations.append((server_params, exception))

    async with MCPAdapt(
        StdioServerParameters(
            command="uv", args=["run", "python", "-c", failing_server_script]
        ),
        DummyAdapter(),
        fail_fast=False,
        on_connection_error=error_callback,
    ):
        pass

    # Callback should have been called once
    assert len(callback_invocations) == 1
    server_params, exception = callback_invocations[0]
    assert isinstance(server_params, StdioServerParameters)
    assert isinstance(exception, Exception)


async def test_failed_connections_tracking_async(
    echo_server_script, failing_server_script
):
    """Test that failed_connections tracking works in async context"""
    adapter = MCPAdapt(
        [
            StdioServerParameters(
                command="uv", args=["run", "python", "-c", failing_server_script]
            ),
            StdioServerParameters(
                command="uv", args=["run", "python", "-c", echo_server_script]
            ),
        ],
        DummyAdapter(),
        fail_fast=False,
    )

    async with adapter as tools:
        assert len(tools) == 1

    # Should have one failed connection tracked
    assert len(adapter.failed_connections) == 1
    server_params, exception = adapter.failed_connections[0]
    assert isinstance(server_params, StdioServerParameters)
    assert isinstance(exception, Exception)


async def test_failed_connections_tracking_async_multiple(
    echo_server_script, failing_server_script
):
    """Test that failed_connections tracking works with multiple failures in async context"""
    adapter = MCPAdapt(
        [
            StdioServerParameters(
                command="uv", args=["run", "python", "-c", failing_server_script]
            ),
            StdioServerParameters(
                command="uv", args=["run", "python", "-c", echo_server_script]
            ),
            StdioServerParameters(
                command="uv", args=["run", "python", "-c", failing_server_script]
            ),
        ],
        DummyAdapter(),
        fail_fast=False,
    )

    async with adapter as tools:
        assert len(tools) == 1

    # Should have two failed connections tracked
    assert len(adapter.failed_connections) == 2
    for server_params, exception in adapter.failed_connections:
        assert isinstance(server_params, StdioServerParameters)
        assert isinstance(exception, Exception)
