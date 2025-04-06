# Langchain

MCPAdapt offers integration with LangChain through its adapter system. Let's explore how to use MCPAdapt with LangChain.

## Using MCPAdapt LangChain Adapter

First, ensure you have the necessary dependencies installed:

```bash
pip install mcpadapt[langchain]
```

### Creating a Simple Echo Server

Let's start with a basic example using a simple echo server:

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

### Using the Echo Server with LangChain

Here's how to interact with the server using LangChain:

```python
import os
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from mcp import StdioServerParameters

from mcpadapt.core import MCPAdapt
from mcpadapt.langchain_adapter import LangChainAdapter

# Initialize MCPAdapt with LangChain adapter
async with MCPAdapt(
    StdioServerParameters(command="uv", args=["run", "echo.py"]),
    LangChainAdapter(),
) as tools:
    # Create the agent
    memory = MemorySaver()
    model = ChatAnthropic(
        model_name="claude-3-5-sonnet-20241022",
        max_tokens_to_sample=8192
    )
    agent_executor = create_react_agent(model, tools, checkpointer=memory)

    # Use the agent
    config = {"configurable": {"thread_id": "abc123"}}
    async for event in agent_executor.astream(
        {
            "messages": [
                HumanMessage(content="Echo 'Hello, World!'")
            ]
        },
        config,
    ):
        print(event)
        print("----")
```

### Real-World Example: PubMed MCP Server

In reality you are more likely to use MCP servers defined by the community.
Here's how to use the PubMed MCP server with LangChain for a more practical example:

```python
import os
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from mcp import StdioServerParameters

from mcpadapt.core import MCPAdapt
from mcpadapt.langchain_adapter import LangChainAdapter

# Load environment variables
load_dotenv()
if not os.environ.get("ANTHROPIC_API_KEY"):
    raise ValueError("ANTHROPIC_API_KEY must be set in your environment variables")

async with MCPAdapt(
    StdioServerParameters(
        command="uvx",
        args=["--quiet", "pubmedmcp@0.1.3"],
        env={"UV_PYTHON": "3.12", **os.environ},
    ),
    LangChainAdapter(),
) as tools:
    # Create the agent
    memory = MemorySaver()
    model = ChatAnthropic(
        model_name="claude-3-5-sonnet-20241022",
        max_tokens_to_sample=8192
    )
    agent_executor = create_react_agent(model, tools, checkpointer=memory)

    # Use the agent
    config = {"configurable": {"thread_id": "abc123"}}
    async for event in agent_executor.astream(
        {
            "messages": [
                HumanMessage(
                    content="Find relevant studies on alcohol hangover and treatment."
                )
            ]
        },
        config,
    ):
        print(event)
        print("----")
```

#### Important Notes:
- Always use the `--quiet` flag with uvx to prevent output interference with the stdio transport protocol
- Including `**os.environ` helps resolve paths in the subprocess but consider security implications
- Remote MCP servers are supported via Server Sent Events (SSE). See the [quickstart SSE guide](../quickstart.md#sse-server-sent-events-support)
- Make sure to set your ANTHROPIC_API_KEY in your environment variables or .env file
- The examples use Claude 3.5 Sonnet, but you can use any LangChain-compatible model
- Both synchronous and asynchronous implementations are supported, but async is preferred for better performance

## Full Working Code Example

You can find a fully working script of this example [here](https://github.com/grll/mcpadapt/blob/main/examples/langchain_pubmed.py)

