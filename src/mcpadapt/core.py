"""Core module for the MCPAdapt library.

This module contains the core functionality for the MCPAdapt library. It provides the
basic interfaces and classes for adapting tools from MCP to the desired Agent framework.
"""

import asyncio
import threading
from abc import ABC, abstractmethod
from contextlib import AsyncExitStack, asynccontextmanager
from functools import partial
from typing import Any, AsyncGenerator, Callable, Coroutine

import mcp
from mcp import ClientSession, StdioServerParameters
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client


class ToolAdapter(ABC):
    """A basic interface for adapting tools from MCP to the desired Agent framework."""

    @abstractmethod
    def adapt(
        self,
        func: Callable[[dict | None], mcp.types.CallToolResult],
        mcp_tool: mcp.types.Tool,
    ) -> Any:
        """Adapt a single tool from MCP to the desired Agent framework.

        The MCP protocol will provide a name, description and inputSchema in JSON Schema
        format. This needs to be adapted to the desired Agent framework.

        Note that the function is synchronous (not a coroutine) you can use
        :meth:`ToolAdapter.async_adapt` if you need to use the tool asynchronously.

        Args:
            func: The function to be called (will call the tool via the MCP protocol).
            mcp_tool: The tool to adapt.

        Returns:
            The adapted tool in the agentic framework of choice.
        """
        pass

    def async_adapt(
        self,
        afunc: Callable[[dict | None], Coroutine[Any, Any, mcp.types.CallToolResult]],
        mcp_tool: mcp.types.Tool,
    ) -> Any:
        """Adapt a single tool from MCP to the desired Agent framework.

        The MCP protocol will provide a name, description and inputSchema in JSON Schema
        format. This needs to be adapted to the desired Agent framework.

        Note that the function is asynchronous (a coroutine) you can use
        :meth:`ToolAdapter.adapt` if you need to use the tool synchronously.

        Args:
            afunc: The coroutine to be called.
            mcp_tool: The tool to adapt.

        Returns:
            The adapted tool in the agentic framework of choice.
        """
        raise NotImplementedError(
            "Async adaptation is not supported for this Agent framework."
        )


@asynccontextmanager
async def mcptools(
    serverparams: StdioServerParameters | dict[str, Any],
) -> AsyncGenerator[tuple[ClientSession, list[mcp.types.Tool]], None]:
    """Async context manager that yields tools from an MCP server.

    Note: the session can be then used to call tools on the MCP server but it's async.
    Use MCPAdapt instead if you need to use the tools synchronously.

    Args:
        serverparams: Parameters passed to either the stdio client or sse client.
            * if StdioServerParameters, run the MCP server using the stdio protocol.
            * if dict, assume the dict corresponds to parameters to an sse MCP server.

    Yields:
        A list of tools available on the MCP server.

    Usage:
    >>> async with mcptools(StdioServerParameters(command="uv", args=["run", "src/echo.py"])) as (session, tools):
    >>>     print(tools)
    """
    if isinstance(serverparams, StdioServerParameters):
        client = stdio_client(serverparams)
    elif isinstance(serverparams, dict):
        client = sse_client(**serverparams)
    else:
        raise ValueError(
            f"Invalid serverparams, expected StdioServerParameters or dict found `{type(serverparams)}`"
        )

    async with client as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the connection and get the tools from the mcp server
            await session.initialize()
            tools = await session.list_tools()
            yield session, tools.tools


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
    >>> async with MCPAdapt({"host": "127.0.0.1", "port": 8000}, SmolAgentAdapter()) as tools:
    >>>     print(tools)
    """

    def __init__(
        self,
        serverparams: StdioServerParameters
        | dict[str, Any]
        | list[StdioServerParameters | dict[str, Any]],
        adapter: ToolAdapter,
        connect_timeout: int = 30,
    ):
        """
        Manage the MCP server / client lifecycle and expose tools adapted with the adapter.

        Args:
            serverparams (StdioServerParameters | dict[str, Any] | list[StdioServerParameters | dict[str, Any]):
                MCP server parameters (stdio or sse). Can be a list of you want to connect multiple MCPs at once.
            adapter (ToolAdapter): Adapter to use to convert MCP tools call into agentic framework tools.
            connect_timeout (int): Connection timeout in seconds to the mcp server (default is 30s).

        Raises:
            TimeoutError: When the connection to the mcp server time out.
        """

        if isinstance(serverparams, list):
            self.serverparams = serverparams
        else:
            self.serverparams = [serverparams]

        self.adapter = adapter

        # session and tools get set by the async loop during initialization.
        self.sessions: list[ClientSession] = []
        self.mcp_tools: list[mcp.types.Tool] = []

        # all attributes used to manage the async loop and separate thread.
        self.loop = asyncio.new_event_loop()
        self.task = None

        self.ready = threading.Event()
        self.thread = threading.Thread(target=self._run_loop, daemon=True)

        self.connect_timeout = connect_timeout

    def _run_loop(self):
        """Runs the event loop in a separate thread (for synchronous usage)."""
        asyncio.set_event_loop(self.loop)

        async def setup():
            async with AsyncExitStack() as stack:
                connections = [
                    await stack.enter_async_context(mcptools(params))
                    for params in self.serverparams
                ]
                self.sessions, self.mcp_tools = [list(c) for c in zip(*connections)]
                self.ready.set()  # Signal initialization is complete
                await asyncio.Event().wait()  # Keep session alive until stopped

        self.task = self.loop.create_task(setup())
        try:
            self.loop.run_until_complete(self.task)
        except asyncio.CancelledError:
            pass

    def tools(self) -> list[Any]:
        """Returns the tools from the MCP server adapted to the desired Agent framework.

        This is what is yielded if used as a context manager otherwise you can access it
        directly via this method.

        An equivalent async method is available if your Agent framework supports it:
        see :meth:`atools`.

        """
        if not self.sessions:
            raise RuntimeError("Session not initialized")

        def _sync_call_tool(
            session, name: str, arguments: dict | None = None
        ) -> mcp.types.CallToolResult:
            return asyncio.run_coroutine_threadsafe(
                session.call_tool(name, arguments), self.loop
            ).result()

        return [
            self.adapter.adapt(partial(_sync_call_tool, session, tool.name), tool)
            for session, tools in zip(self.sessions, self.mcp_tools)
            for tool in tools
        ]

    def close(self):
        """Clean up resources and stop the client."""
        if self.task and not self.task.done():
            self.loop.call_soon_threadsafe(self.task.cancel)
        self.thread.join()  # will wait until the task is cancelled to join thread (as it's blocked Event().wait())
        self.loop.close()  # we won't be using the loop anymore we can safely close it

    def __enter__(self):
        self.thread.start()

        # check connection to mcp server is ready
        if not self.ready.wait(timeout=self.connect_timeout):
            raise TimeoutError(
                f"Couldn't connect to the MCP server after {self.connect_timeout} seconds"
            )

        return self.tools()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    # -- add support for async context manager as well if the agent framework supports it.
    def atools(self) -> list[Any]:
        """Returns the tools from the MCP server adapted to the desired Agent framework.

        This is what is yielded if used as an async context manager otherwise you can
        access it directly via this method.

        An equivalent async method is available if your Agent framework supports it:
        see :meth:`atools`.
        """
        return [
            self.adapter.async_adapt(partial(session.call_tool, tool.name), tool)
            for session, tools in zip(self.sessions, self.mcp_tools)
            for tool in tools
        ]

    async def __aenter__(self) -> list[Any]:
        self._ctxmanager = AsyncExitStack()

        connections = [
            await self._ctxmanager.enter_async_context(mcptools(params))
            for params in self.serverparams
        ]

        self.sessions, self.mcp_tools = [list(c) for c in zip(*connections)]

        return self.atools()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
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
        [
            StdioServerParameters(command="uv", args=["run", "src/echo.py"]),
            StdioServerParameters(command="uv", args=["run", "src/echo.py"]),
        ],
        DummyAdapter(),
    ) as dummy_tools:
        print(dummy_tools)
        print(dummy_tools[0]({"text": "hello"}))
        print(dummy_tools[1]({"text": "world"}))

    async def main():
        async with MCPAdapt(
            [
                StdioServerParameters(command="uv", args=["run", "src/echo.py"]),
                StdioServerParameters(command="uv", args=["run", "src/echo.py"]),
            ],
            DummyAdapter(),
        ) as dummy_tools:
            print(dummy_tools)
            print(await dummy_tools[0]({"text": "hello"}))
            print(await dummy_tools[1]({"text": "world"}))

    asyncio.run(main())
