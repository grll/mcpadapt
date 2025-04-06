# Smolagents

MCPAdapt offers two ways to integrate with HuggingFace Smolagents. Let's explore both options:

## Option 1: Direct Smolagents Integration

Install the package with MCP support:

```bash
pip install smolagents[mcp]
```

### Creating a Simple Echo Server

First, create an MCP server using FastMCP notation (from the official python-sdk):

```python
# echo.py
from mcp.server.fastmcp import FastMCP
from pydantic import Field

# Create server
mcp = FastMCP("Echo Server")


@mcp.tool()
def echo_tool(text: str = Field(description="The text to echo")) -> str:
    """Echo the input text

    Args:
        text (str): The text to echo

    Returns:
        str: The echoed text
    """
    return text
  
mcp.run()
```

### Using the Echo Server

Here's how to interact with the server:

```python
from mcp import StdioServerParameters
from smolagents import CodeAgent, HfApiModel  # type: ignore
from smolagents.tools import ToolCollection

serverparams = StdioServerParameters(command="uv", args=["run", "echo.py"])

with ToolCollection.from_mcp(serverparams) as tool_collection:
    agent = CodeAgent(tools=tools, model=HfApiModel())
    agent.run("Can you echo something?")
```

### Real-World Example: PubMed MCP Server

Most often, you'll use pre-built MCP servers. Here's an example using the PubMed MCP server:

```python
import os

from mcp import StdioServerParameters
from smolagents import CodeAgent, HfApiModel  # type: ignore
from smolagents.tools import ToolCollection

with ToolCollection.from_mcp(
    StdioServerParameters(
        command="uvx",
        args=["--quiet", "pubmedmcp@0.1.3"],
        env={"UV_PYTHON": "3.12", **os.environ},
    ),
) as tools:
    # print(tools[0](request={"term": "efficient treatment hangover"}))
    agent = CodeAgent(tools=tools, model=HfApiModel())
    agent.run("Find studies about hangover?")
```

#### Important Notes:
- Always use the `--quiet` flag with uvx to prevent output interference with the stdio transport protocol
- Including `**os.environ` helps resolve paths in the subprocess but consider security implications of sending your environment variable to the MCP server.
- Remote MCP servers are supported via Server Sent Events (SSE). See the [quickstart SSE guide](../quickstart.md#sse-server-sent-events-support)


## Option 2: MCPAdapt Smolagents Adapter

Alternatively, you can use the MCPAdapt smolagents adapter:

```python
import os

from mcp import StdioServerParameters
from smolagents import CodeAgent, HfApiModel  # type: ignore

from mcpadapt.core import MCPAdapt
from mcpadapt.smolagents_adapter import SmolAgentsAdapter

with MCPAdapt(
    StdioServerParameters(
        command="uvx",
        args=["--quiet", "pubmedmcp@0.1.3"],
        env={"UV_PYTHON": "3.12", **os.environ},
    ),
    SmolAgentsAdapter(),
) as tools:
    agent = CodeAgent(tools=tools, model=HfApiModel())
    agent.run("Find studies about hangover?")
```

This approach achieves the same result but uses MCPAdapt directly with its smolagents adapter.

## Full Working Code Example

You a fully working script of this example [here](https://github.com/grll/mcpadapt/blob/main/examples/smolagents_pubmed.py)





