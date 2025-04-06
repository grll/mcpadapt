# Google GenAI

MCPAdapt offers integration with Google's genai SDK through its adapter system. Let's explore how to use MCPAdapt with Google GenAI.

## Using MCPAdapt Google GenAI Adapter

First, ensure you have the necessary dependencies installed:

```bash
pip install mcpadapt[google-genai]
```

You'll also need to set up your Google API key. You can get this from the Google AI Studio.

### Creating a Simple Echo Server

First, let's create an MCP server using FastMCP notation:

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

### Using the Echo Server with Google GenAI

Here's how to interact with the server using Google's Generative AI:

```python
import os
from google import genai
from google.genai import types
from mcp import StdioServerParameters

from mcpadapt.core import MCPAdapt
from mcpadapt.google_genai_adapter import GoogleGenAIAdapter

# Initialize Google GenAI client
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Create server parameters
server_params = StdioServerParameters(
    command="uv",
    args=["run", "echo.py"]
)

async def run():
    async with MCPAdapt(
        server_params,
        GoogleGenAIAdapter(),
    ) as adapted_tools:
        # Unpack tools and tool_functions
        google_tools, tool_functions = zip(*adapted_tools)
        tool_functions = dict(tool_functions)

        prompt = "Please echo back 'Hello, World!'"

        # Generate content with function declarations
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.7,
                tools=google_tools,
            ),
        )

        # Handle the function call
        if response.candidates[0].content.parts[0].function_call:
            function_call = response.candidates[0].content.parts[0].function_call
            result = await tool_functions[function_call.name](function_call.args)
            print(result.content[0].text)
        else:
            print("No function call found in the response.")
            print(response.text)

if __name__ == "__main__":
    import asyncio
    asyncio.run(run())
```

### Real-World Example: Airbnb MCP Server

Here's a real-world example using the Airbnb MCP server with Google GenAI:

```python
import os
from google import genai
from google.genai import types
from mcp import StdioServerParameters

from mcpadapt.core import MCPAdapt
from mcpadapt.google_genai_adapter import GoogleGenAIAdapter

# Initialize Google GenAI client
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Create server parameters for Airbnb MCP
server_params = StdioServerParameters(
    command="npx",
    args=[
        "-y",
        "@openbnb/mcp-server-airbnb",
        "--ignore-robots-txt",
    ],
)

async def run():
    async with MCPAdapt(
        server_params,
        GoogleGenAIAdapter(),
    ) as adapted_tools:
        # Unpack tools and tool_functions
        google_tools, tool_functions = zip(*adapted_tools)
        tool_functions = dict(tool_functions)

        prompt = "I want to book an apartment in Paris for 2 nights, March 28-30"

        # Generate content with function declarations
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.7,
                tools=google_tools,
            ),
        )

        # Handle the function call
        if response.candidates[0].content.parts[0].function_call:
            function_call = response.candidates[0].content.parts[0].function_call
            result = await tool_functions[function_call.name](function_call.args)
            print(result.content[0].text)
        else:
            print("No function call found in the response.")
            print(response.text)

if __name__ == "__main__":
    import asyncio
    asyncio.run(run())
```

#### Important Notes:
- Make sure to set your `GEMINI_API_KEY` in your environment variables
- The examples work with both synchronous and asynchronous code
- Remote MCP servers are supported via Server Sent Events (SSE). See the [quickstart SSE guide](../quickstart.md#sse-server-sent-events-support)

## Full Working Code Example

You can find a fully working script of the Airbnb example [here](https://github.com/grll/mcpadapt/blob/main/examples/google_genai.py)