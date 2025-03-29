"""
Example of using the Google GenAI adapter with MCPAdapt.

This example shows how to use the Google GenAI adapter with MCP to call a airbnb tool.

Note: this whole example also work seamlessly synchronously.
"""

import os

from google import genai  # type: ignore
from google.genai import types  # type: ignore
from mcp import StdioServerParameters

from mcpadapt.core import MCPAdapt
from mcpadapt.google_genai_adapter import GoogleGenAIAdapter

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)  # Replace with your actual API key setup


# Create server parameters for stdio connection
server_params = StdioServerParameters(
    command="npx",  # Executable
    args=[
        "-y",
        "@openbnb/mcp-server-airbnb",
        "--ignore-robots-txt",
    ],  # Optional command line arguments
    env=None,  # Optional environment variables
)


async def run():
    async with MCPAdapt(
        server_params,
        GoogleGenAIAdapter(),
    ) as adapted_tools:
        # unpack tools and tool_functions
        google_tools, tool_functions = zip(*adapted_tools)
        tool_functions = dict(tool_functions)

        prompt = "I want to book an apartment in Paris for 2 nights. 03/28 - 03/30"

        # Send request with function declarations
        response = client.models.generate_content(
            model="gemini-2.0-flash",  # Or your preferred model supporting function calling
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.7,
                tools=google_tools,
            ),  # Example other config
        )

        # Check for a function call
        if response.candidates[0].content.parts[0].function_call:
            function_call = response.candidates[0].content.parts[0].function_call
            print(f"Function to call: {function_call.name}")
            print(f"Arguments: {function_call.args}")
            # In a real app, you would call your function here:
            print(function_call.name)
            print(function_call.args)
            result = await tool_functions[function_call.name](function_call.args)

            # here you could use result.isError to check if the tool call was successful
            # or just extract the content assuming it's text:
            text_content = result.content[0].text
            print(text_content)
            # sent new request with function call
        else:
            print("No function call found in the response.")
            print(response.text)


if __name__ == "__main__":
    import asyncio

    asyncio.run(run())
