# MCPAdapt

![PyPI version](https://img.shields.io/pypi/v/mcpadapt)
![Python versions](https://img.shields.io/pypi/pyversions/mcpadapt)
![Tests](https://github.com/grll/mcpadapt/actions/workflows/ci.yml/badge.svg)
![License](https://img.shields.io/github/license/grll/mcpadapt)
![PyPI downloads](https://img.shields.io/pypi/dm/mcpadapt)
![GitHub Repo stars](https://img.shields.io/github/stars/grll/mcpadapt)

Unlock 650+ MCP servers tools in your favorite agentic framework.

Model Context Protocol is an open-source protocol introduced by Anthropic which allows anyone to simply and quickly make tools and resources available as "MCP Servers".

Since its release more than 650 MCP servers have been created giving access to many data & tools to supported "MCP Client".

This project makes calling any MCP servers tools seemless from any agentic framework. Virtually providing your agentic worfklow access to 650+ MCP servers tools.

Look at [glama.ai](https://glama.ai/mcp/servers) or [smithery.ai](https://smithery.ai/) to give you an idea of what your agent could access.

## Installation Instructions

### Smolagents

Smolagents 1.4.1 and above directly ships with mcpadapt integrated in their tool collections object.
It means you can directly use it from smolagents:

```bash
uv add smolagents[mcp]
```

### Other Frameworks

Each agent framework has its own set of optional dependencies to not clutter with useless dependencies.
You choose the flavor you want by adding your framework in brackets in the installation command.

```bash
# with uv
uv add mcpadapt[langchain]

# or with pip
pip install mcpadapt[langchain]
```

Framework supported at the moment: smolagents, langchain, crewAI, google-genai.

You can also add multiple framework comma separated if needed. 

## Usage

⚠️ **Security Warning**: When using MCP servers, especially over SSE (Server-Sent Events), be extremely cautious and only connect to trusted and verified servers. Some adapters use Python's `exec` function internally, which could potentially allow for remote code execution if connected to a malicious server. Always verify the source and security of any MCP server before connecting.

### Smolagents

Since mcpadapt is part of smolagents simple use tool collection from smolagents like:

```python
from mcp import StdioServerParameters
from smolagents.tools import ToolCollection

serverparams = StdioServerParameters(command="uv", args=["run", "src/echo.py"])

with ToolCollection.from_mcp(serverparams) as tool_collection:
    ... # enjoy your tools!
```

### Other Frameworks

MCPAdapt adapt any MCP servers into tools that you can use right in your agentic workflow:

```python
from mcp import StdioServerParameters
from mcpadapt.core import MCPAdapt
from mcpadapt.smolagents_adapter import SmolAgentsAdapter

with MCPAdapt(
    # specify the command to run your favorite MCP server (support also smithery and co.)
    StdioServerParameters(command="uv", args=["run", "src/echo.py"]),
    # or a dict of sse server parameters e.g. {"url": http://localhost:8000, "headers": ...}

    # specify the adapter you want to use to adapt MCP into your tool in this case smolagents.
    SmolAgentsAdapter(),
) as tools:
    # enjoy your smolagents tools as if you wrote them yourself
    ...
```

MCP Adapt supports Smolagents, Langchain, CrewAI, google-genai [pydantic.dev, Llammaindex and more...]*.
*coming soon.

See our examples for more details on how to use.

## Contribute

If your favorite agentic framework is missing no problem add it yourself it's quite easy:

1. create a new module in `src/mcpadapt/{name_of_your_framework}_adapter.py`:

```python
class YourFrameworkAdapter(ToolAdapter):
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

2. and that's it, test that your adapter is working and send us a PR to share it with the world.

## Roadmap

- [x] initial framework for anyone to start creating adapters
- [x] support for smolagents
- [ ] support for pydantic-ai
- [x] support for langchain
- [ ] support for llamaindex
- [ ] support for swarm
- [x] support for crewAI
- [x] support for google genai
- [x] support for remote MCP Servers via SSE
- [x] support for jupyter notebook
- [x] add tests

