# CrewAI

At the time of writing, MCPAdapt offers integration with CrewAI through its adapter system only. However a PR is underway to integrate directly into CrewAI's framework.

Let's explore how to use MCPAdapt with CrewAI.

## Using MCPAdapt CrewAI Adapter

Ensure you have the necessary dependencies installed and set up your OpenAI API key as required by crewAI:

```bash
pip install mcpadapt[crewai]
```

### Creating a Simple Echo Server

First, create an MCP server using FastMCP notation:

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

Here's how to interact with the server using CrewAI:

```python
import os
from crewai import Agent, Crew, Task
from mcp import StdioServerParameters

from mcpadapt.core import MCPAdapt
from mcpadapt.crewai_adapter import CrewAIAdapter

with MCPAdapt(
    StdioServerParameters(command="uv", args=["run", "echo.py"]),
    CrewAIAdapter(),
) as tools:
    # Create an echo agent
    agent = Agent(
        role="Echo Agent",
        goal="Echo messages back to the user",
        backstory="You help echo messages back to users",
        verbose=True,
        tools=[tools[0]],
    )

    # Create a task
    task = Task(
        description="Echo 'Hello, World!'",
        agent=agent,
        expected_output="The echoed message",
    )

    # Create and run the crew
    crew = Crew(agents=[agent], tasks=[task], verbose=True)
    crew.kickoff()
```

### Real-World Example: PubMed MCP Server

In the real-world, you are most likely to run MCP server already built by the community.
As an example, here's how to use the PubMed MCP server with CrewAI:

```python
import os
from dotenv import load_dotenv
from crewai import Agent, Crew, Task
from mcp import StdioServerParameters

from mcpadapt.core import MCPAdapt
from mcpadapt.crewai_adapter import CrewAIAdapter

# Load environment variables
load_dotenv()
if not os.environ.get("OPENAI_API_KEY"):
    raise ValueError("OPENAI_API_KEY must be set in your environment variables")

# Initialize MCPAdapt with CrewAI adapter
with MCPAdapt(
    StdioServerParameters(
        command="uvx",
        args=["--quiet", "pubmedmcp@0.1.3"],
        env={"UV_PYTHON": "3.12", **os.environ},
    ),
    CrewAIAdapter(),
) as tools:
    # Create a research agent
    agent = Agent(
        role="Research Agent",
        goal="Find studies about hangover",
        backstory="You help find studies about hangover",
        verbose=True,
        tools=[tools[0]],
    )

    # Create a task
    task = Task(
        description="Find studies about hangover",
        agent=agent,
        expected_output="A list of studies about hangover",
    )

    # Create and run the crew
    crew = Crew(agents=[agent], tasks=[task], verbose=True)
    crew.kickoff()
```

#### Important Notes:
- Always use the `--quiet` flag with uvx to prevent output interference with the stdio transport protocol
- Including `**os.environ` helps resolve paths in the subprocess but consider security implications of sending your environment variables to the MCP server
- Remote MCP servers are supported via Server Sent Events (SSE). See the [quickstart SSE guide](../quickstart.md#sse-server-sent-events-support)
- Make sure to set your OPENAI_API_KEY in your environment variables or .env file

## Full Working Code Example

You can find a fully working script of this example [here](https://github.com/grll/mcpadapt/blob/main/examples/crewai_pubmed.py)

