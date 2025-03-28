"""
FastMCP dummy Echo Server for testing purposes.
"""

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


@mcp.resource("echo://static")
def echo_resource() -> str:
    return "Echo!"


@mcp.resource("echo://{text}")
def echo_template(text: str) -> str:
    """Echo the input text"""
    return f"Echo: {text}"


@mcp.prompt("echo")
def echo_prompt(text: str) -> str:
    return text


if __name__ == "__main__":
    import sys

    print("starting echo server", file=sys.stderr)
    mcp.run()
    print("echo server ended", file=sys.stderr)
