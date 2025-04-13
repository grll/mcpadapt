# Quickstart

## Installation

Install mcpadapt for your agentic framework of choice with:

```bash
pip install mcpadapt[agentic-framework]
```

where agentic-framework can be:

* smolagents
* crewai
* langchain
* google-genai
* llamaindex

## Usage


### Standard IO (stdio)

In the most simple case, MCP adapt takes the following form:

```python
from mcp import StdioServerParameters
from mcpadapt.core import MCPAdapt
from mcpadapt.<agentic-framework>_adapter import <AgenticFramework>Adapter

with MCPAdapt(
    StdioServerParameters(command="uv", args=["run", "src/echo.py"]),
    <AgenticFramework>Adapter(),
) as tools:
    # tools is a list of tools 100% compatible with your agentic framework.
    ...
```

In this setup:

1. You define your MCP server parameters using the official Python SDK
2. You import the MCPAdapt core and the appropriate adapter for your agentic framework
3. You wrap your agent's code within the MCPAdapt context manager

Behind the scenes, MCPAdapt launches your MCP server in a subprocess and handles all communication between your agentic framework and the MCP server. When your agent uses a tool, MCPAdapt transparently routes the call to the corresponding MCP server tool and returns the results in your framework's expected format.

If your agentic framework support async then you can also use MCPAdapt with async:

```python
from mcp import StdioServerParameters
from mcpadapt.core import MCPAdapt
from mcpadapt.<agentic-framework>_adapter import <AgenticFramework>Adapter

async with MCPAdapt(
    StdioServerParameters(command="uv", args=["run", "src/echo.py"]),
    <AgenticFramework>Adapter(),
) as tools:
    # tools is a list of tools 100% compatible with your agentic framework.
    ...
```

### SSE (Server-Sent Events) Support

MCPAdapt supports SSE for both synchronous and asynchronous operations. Here's how to use it:

```python
from mcpadapt.core import MCPAdapt
from mcpadapt.<framework>_adapter import <Framework>Adapter

async with MCPAdapt(
    {
        "url": "http://127.0.0.1:8000/sse",
        # Optional parameters:
        # "headers": {"Authorization": "Bearer token"},
        # "timeout": 5,  # Connection timeout in seconds
        # "sse_read_timeout": 300  # SSE read timeout in seconds (default: 5 minutes)
    },
    <Framework>Adapter()
) as tools:
    # 'tools' contains framework-compatible tools
    ...
```

To use SSE, simply provide a configuration dictionary instead of StdioServerParameters. The configuration accepts the following parameters:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| url | str | Yes | - | The SSE endpoint URL |
| headers | dict[str, Any] | No | None | Custom HTTP headers |
| timeout | float | No | 5 | Connection timeout in seconds |
| sse_read_timeout | float | No | 300 | SSE read timeout in seconds |

These parameters are passed directly to the MCP Python SDK's SSE client. For more details, see the [official MCP Python SDK documentation](https://github.com/modelcontextprotocol/python-sdk/blob/c2ca8e03e046908935d089a2ceed4e80b0c29a24/src/mcp/client/sse.py#L22C11-L22C21).

### Multiple MCP Servers

In all cases, you can provide multiple MCP Server parameters as a list:

```python
from mcp import StdioServerParameters
from mcpadapt.core import MCPAdapt
from mcpadapt.<framework>_adapter import <Framework>Adapter

with MCPAdapt(
    [
        StdioServerParameters(command="uv", args=["run", "src/echo1.py"]),
        StdioServerParameters(command="uv", args=["run", "src/echo2.py"]),
    ],
    <AgenticFramework>Adapter(),
) as tools:
    # tools is now a flattened list of tools from the 2 MCP servers.
    ...
```

## Examples

We provide guided examples of usage for each framework in their respective guides:

* [SmolAgents Guide](guide/smolagents.md)
* [CrewAI Guide](guide/crewai.md)
* [LangChain Guide](guide/langchain.md)
* [Google GenAI Guide](guide/google-genai.md)