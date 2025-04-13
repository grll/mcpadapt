# MCP Adapt

![PyPI version](https://img.shields.io/pypi/v/mcpadapt)
![Python versions](https://img.shields.io/pypi/pyversions/mcpadapt)
![Tests](https://github.com/grll/mcpadapt/actions/workflows/ci.yml/badge.svg)
![License](https://img.shields.io/github/license/grll/mcpadapt)
![PyPI downloads](https://img.shields.io/pypi/dm/mcpadapt)
![GitHub Repo stars](https://img.shields.io/github/stars/grll/mcpadapt)

[MCPadapt](https://github.com/grll/mcpadapt) let you **seamlessly** use 1000+ MCP server "tools" with many agentic frameworks including [HuggingFace Smolagents](https://github.com/huggingface/smolagents), [crewAI](https://github.com/crewAIInc/crewAI), [langchain](https://github.com/langchain-ai/langchain), [google-genai](https://github.com/GoogleCloudPlatform/generative-ai) and more to come.

MCPAdapt supports all transport protocols available in MCP, including:

* Standard I/O (stdio) for local tool execution.
* Server-Sent Events (SSE) for real-time streaming communication.

Dependencies are efficiently managed through optional extras, allowing you to install only the frameworks you need. This means you can use MCPAdapt with your preferred framework without installing unnecessary dependencies for other frameworks that you don't use.

## Why MCPAdapt?

There are dozens of agentic frameworks available today, each implementing their own Tool class with different signatures and functionality. The MCP community has developed thousands of MCP servers each with many powerful tools representing a huge opportunity for improving agents capabilities. Yet not all agentic frameworks support the MCP protocol.

Popular MCP tool directories like [glama.ai](https://glama.ai/mcp/servers) and [smithery.ai](https://smithery.ai/) showcase the vast ecosystem of tools your agents could leverage - from data analysis and web automation to complex reasoning and specialized domain tools. MCPAdapt makes it simple to unlock this potential by providing seamless integration between your preferred agent framework and any MCP server.

## How MCPAdapt works?

MCPAdapt consists of two main components:

1. A core component that handles all the complexity of managing MCP server lifecycle in both synchronous and asynchronous contexts. This core functionality is shared and leveraged across the different agentic frameworks.

2. Framework-specific adapters that transform MCP server tools into the appropriate format for each agent framework. These adapters are simple subclasses that convert MCP tools into the specific Tool classes, functions, or signatures required by frameworks like Langchain, CrewAI, or Smolagents.

This architecture allows MCPAdapt to provide consistent MCP server management while seamlessly integrating with the unique requirements of each agentic framework.

When we can we also integrate MCPAdapt directly in the target agentic framework. This is the case for Smolagents where mcpadapt is available and directly integrated there. 

## Installation

```bash
pip install mcpadapt[agentic-framework]
```

where agentic-framework can be:

* smolagents
* crewai
* langchain
* google-genai
* llamaindex

## Basic Usage

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

We also support SSE and provide detailed example for each particular framework see [link].

## Contribute

This project can grow bigger, support more agentic framework and more functionality with your help.
We are commited to review your work, suggestion and issues quickly and carefully.

As an example contribution, adding an adapter for a new framework is quite straight forward:

1. create a new module in `src/mcpadapt/<agentic-framework>_adapter.py`:
```python
class <AgenticFramework>Adapter(ToolAdapter):
    def adapt(
        self,
        func: Callable[[dict | None], mcp.types.CallToolResult],
        mcp_tool: mcp.types.Tool,
    ) -> YourFramework.Tool:
        # HERE implement how the adapter should convert a simple function and mcp_tool (JSON Schema)
        # into your framework tool. see smolagents_adapter.py for an example
    
    def async_adapt(
        self,
        afunc: Callable[[dict | None], Coroutine[Any, Any, mcp.types.CallToolResult]],
        mcp_tool: mcp.types.Tool,
    ) -> YourFramework.Tool:
        # if your framework supports async function even better use async_adapt.
```
2. add test, documentation and submit your PR for review.

## Contributors

We acknowledge the work and thanks every contributors and maintainers for their contributions.

Core Maintainers:

* [@grll](https://github.com/grll)

Contributors:

* [@murawakimitsuhiro](https://github.com/murawakimitsuhiro)
* [@joejoe2](https://github.com/joejoe2)
* [@tisDDM](https://github.com/tisDDM)
* [@sysradium](https://github.com/sysradium)
