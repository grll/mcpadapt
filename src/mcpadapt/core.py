"""Core module for the MCPAdapt library.

This module contains the core functionality for the MCPAdapt library. It provides the
basic interfaces and classes for adapting tools from MCP to the desired Agent framework.
"""

import asyncio
import threading
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from functools import partial
from typing import Any, Callable, Coroutine, AsyncGenerator
from datetime import timedelta

import mcp
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamablehttp_client


class ToolAdapter(ABC):
    """A basic interface for adapting tools from MCP to the desired Agent framework."""

    @abstractmethod
    def adapt(
        self,
        func: Callable[[dict | None], mcp.types.CallToolResult],
        mcp_tool: mcp.types.Tool,
    ):
        """Adapt a single tool from MCP to the desired Agent framework.

        The MCP protocol will provide a name, description and inputSchema in JSON Schema
        format. This needs to be adapted to the desired Agent framework.

        Note that the function is synchronous (not a coroutine) you can use
        :meth:`ToolAdapter.async_adapt` if you need to use the tool asynchronously.

        Args:
            func: The function to be called (will call the tool via the MCP protocol).
            mcp_tool: The tool to adapt.

        Returns:
            The adapted tool.
        """
        pass

    def async_adapt(
        self,
        afunc: Callable[[dict | None], Coroutine[Any, Any, mcp.types.CallToolResult]],
        mcp_tool: mcp.types.Tool,
    ):
        """Adapt a single tool from MCP to the desired Agent framework.

        The MCP protocol will provide a name, description and inputSchema in JSON Schema
        format. This needs to be adapted to the desired Agent framework.

        Note that the function is asynchronous (a coroutine) you can use
        :meth:`ToolAdapter.adapt` if you need to use the tool synchronously.

        Args:
            afunc: The coroutine to be called.
            mcp_tool: The tool to adapt.

        Returns:
            The adapted tool.
        """
        raise NotImplementedError(
            "Async adaptation is not supported for this Agent framework."
        )


@asynccontextmanager
async def mcptools(
    serverparams: StdioServerParameters | dict[str, Any],
    client_session_timeout_seconds: float | timedelta | None = 5,
) -> AsyncGenerator[tuple[ClientSession, list[mcp.types.Tool]], None]:
    """Async context manager that yields tools from an MCP server.

    Note: the session can be then used to call tools on the MCP server but it's async.
    Use MCPAdapt instead if you need to use the tools synchronously.

    Args:
        serverparams: Parameters passed to either the stdio client or sse client.
            * if StdioServerParameters, run the MCP server using the stdio protocol.
            * if dict, assume the dict corresponds to parameters to an sse MCP server.
        client_session_timeout_seconds: Timeout for the client session in seconds.

    Yields:
        A tuple containing the active ClientSession and a list of MCP tools.

    Usage:
    >>> async with mcptools(StdioServerParameters(command="uv", args=["run", "src/echo.py"])) as (session, tools):
    >>>     print(tools)
    """
    client_context_manager: Any  # To store the selected client context manager

    if isinstance(serverparams, StdioServerParameters):
        client_context_manager = stdio_client(serverparams)
    elif isinstance(serverparams, dict):
        transport_type = serverparams.get("transport")
        params_copy = serverparams.copy()
        params_copy.pop("transport", None)  # Remove transport, not needed by underlying clients

        if transport_type == "streamable_http":
            if "url" not in params_copy:
                raise ValueError("Missing 'url' in serverparams for streamable_http transport")
            client_context_manager = streamablehttp_client(**params_copy)
        elif transport_type == "sse" or transport_type is None:  # Default to sse
            client_context_manager = sse_client(**params_copy)
        else:
            raise ValueError(f"Unsupported transport type: {transport_type} in serverparams dictionary.")
    else:
        raise ValueError(
            f"Invalid serverparams type. Expected StdioServerParameters or dict, found `{type(serverparams)}`"
        )

    timeout_delta = None
    if isinstance(client_session_timeout_seconds, float):
        timeout_delta = timedelta(seconds=client_session_timeout_seconds)
    elif isinstance(client_session_timeout_seconds, timedelta):
        timeout_delta = client_session_timeout_seconds

    read_fn: Callable
    write_fn: Callable
    # _get_session_id_fn is captured if present but not directly used by ClientSession constructor.

    async with client_context_manager as client_output:
        if len(client_output) == 3:  # streamablehttp_client
            read_fn, write_fn, _get_session_id_fn = client_output
        elif len(client_output) == 2:  # stdio_client or sse_client
            read_fn, write_fn = client_output
        else:
            raise RuntimeError(
                f"Unexpected output from client context manager. Expected 2 or 3 values, got {len(client_output)}."
            )

        async with ClientSession(
            read_fn,
            write_fn,
            timeout_delta,
        ) as session:
            # Initialize the connection and get the tools from the mcp server
            await session.initialize()
            tools_result = await session.list_tools()
            yield session, tools_result.tools


class MCPAdapt:
    """The main class for adapting MCP tools to the desired Agent framework.

    This class can be used either as a sync or async context manager.

    If running synchronously, it will run the MCP server in a separate thread and take
    care of making the tools synchronous without blocking the server.

    If running asynchronously, it will use the async context manager and return async
    tools.

    Dependening on what your Agent framework supports choose the approriate method. If
    async is supported it is recommended.

    Important Note: adapters need to implement the async_adapt method to support async
    tools.

    Usage:
    >>> # sync usage
    >>> with MCPAdapt(StdioServerParameters(command="uv", args=["run", "src/echo.py"]), SmolAgentAdapter()) as tools:
    >>>     print(tools)

    >>> # async usage
    >>> async with MCPAdapt(StdioServerParameters(command="uv", args=["run", "src/echo.py"]), SmolAgentAdapter()) as tools:
    >>>     print(tools)

    >>> # async usage with sse
    >>> async with MCPAdapt(dict(host="127.0.0.1", port=8000), SmolAgentAdapter()) as tools:
    >>>     print(tools)
    """

    def __init__(
        self, serverparams: StdioServerParameters | dict[str, Any], adapter: ToolAdapter
    ):
        # attributes we receive from the user.
        self.serverparams = serverparams
        self.adapter = adapter

        # session and tools get set by the async loop during initialization.
        self.session: ClientSession | None = None
        self.mcp_tools: list[mcp.types.Tool] | None = None

        # all attributes used to manage the async loop and separate thread.
        self.loop = asyncio.new_event_loop()
        self.task = None
        self.ready = threading.Event()
        self.thread = threading.Thread(target=self._run_loop, daemon=True)

        # start the loop in a separate thread and wait till ready synchronously.
        self.thread.start()
        self.ready.wait()

    def _run_loop(self):
        """Runs the event loop in a separate thread (for synchronous usage)."""
        asyncio.set_event_loop(self.loop)

        async def setup():
            # mcptools will yield a tuple (session, tools_list)
            # here we only have one serverparam so we don't need a list
            # and we can unpack directly
            async with mcptools(self.serverparams) as (session, tools_list):
                self.session = session
                self.mcp_tools = tools_list
                self.ready.set()  # Signal initialization is complete
                await asyncio.Event().wait()  # Keep session alive until stopped

        self.task = self.loop.create_task(setup())
        try:
            self.loop.run_until_complete(self.task)
        except asyncio.CancelledError:
            # This is expected when closing.
            pass

    def tools(self) -> list[Any]:
        """Returns the tools from the MCP server adapted to the desired Agent framework.

        This is what is yielded if used as a context manager otherwise you can access it
        directly via this method.

        Only use this when you start the client in synchronous context or by :meth:`start`.

        An equivalent async method is available if your Agent framework supports it:
        see :meth:`atools`.

        """
        if not self.session or not self.mcp_tools:
            raise RuntimeError("Session not initialized or no tools found.")

        def _sync_call_tool(name: str, arguments: dict | None = None) -> mcp.types.CallToolResult:
            if not self.session:
                raise RuntimeError("Session not available for sync call.")
            return asyncio.run_coroutine_threadsafe(
                self.session.call_tool(name, arguments), self.loop
            ).result()

        return [
            self.adapter.adapt(partial(_sync_call_tool, tool.name), tool)
            for tool in self.mcp_tools
        ]

    def start(self):
        """Start the client in synchronous context."""
        if not self.thread.is_alive():
            # Re-initialize thread if it was stopped and start() is called again.
            # This might be needed if close() was called and then start() is called again.
            self.loop = asyncio.new_event_loop()
            self.task = None
            self.ready = threading.Event()
            self.thread = threading.Thread(target=self._run_loop, daemon=True)
            self.thread.start()
        self.ready.wait()

    def close(self):
        """Clean up resources and stop the client."""
        if self.task and not self.task.done():
            self.loop.call_soon_threadsafe(self.task.cancel)
        if self.thread.is_alive():
            self.thread.join()
        if not self.loop.is_closed():
            self.loop.close()

    def __enter__(self):
        # self.start() is already called in __init__ for sync usage
        return self.tools()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    # -- add support for async context manager as well if the agent framework supports it.
    async def atools(self) -> list[Any]:
        """Returns the tools from the MCP server adapted to the desired Agent framework.

        This is what is yielded if used as an async context manager otherwise you can
        access it directly via this method.

        Only use this when you start the client in asynchronous context.

        An equivalent sync method is available if your Agent framework supports it:
        see :meth:`tools`.
        """
        if not self.session or not self.mcp_tools:
            raise RuntimeError("Async session not initialized or no tools found.")

        return [
            self.adapter.async_adapt(partial(self.session.call_tool, tool.name), tool)
            for tool in self.mcp_tools
        ]

    async def __aenter__(self) -> list[Any]:
        self._ctxmanager = mcptools(self.serverparams)
        self.session, self.mcp_tools = await self._ctxmanager.__aenter__()
        return await self.atools() # Use await here as atools is async

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if hasattr(self, '_ctxmanager'): # Ensure _ctxmanager was set
             await self._ctxmanager.__aexit__(exc_type, exc_val, exc_tb)


if __name__ == "__main__":

    class DummyAdapter(ToolAdapter):
        def adapt(
            self,
            func: Callable[[dict | None], mcp.types.CallToolResult],
            mcp_tool: mcp.types.Tool,
        ):
            return func

        def async_adapt(
            self,
            afunc: Callable[
                [dict | None], Coroutine[Any, Any, mcp.types.CallToolResult]
            ],
            mcp_tool: mcp.types.Tool,
        ):
            return afunc

    with MCPAdapt(
        StdioServerParameters(command="uv", args=["run", "src/echo.py"]),
        DummyAdapter(),
    ) as dummy_tools:
        print(dummy_tools)
        print(dummy_tools[0]({"text": "hello"})) # Corrected: direct call
        # print(dummy_tools[0].forward({"text": "hello"})) # Old incorrect call

    async def main():
        async with MCPAdapt(
            StdioServerParameters(command="uv", args=["run", "src/echo.py"]),
            DummyAdapter(),
        ) as dummy_tools:
            print(dummy_tools)
            print(await dummy_tools[0]({"text": "hello"})) # Corrected: direct call
            # print(await dummy_tools[0].forward({"text": "hello"})) # Old incorrect call

    asyncio.run(main())
