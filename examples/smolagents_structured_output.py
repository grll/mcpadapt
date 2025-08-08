"""
Minimal example showcasing the difference between using structured output
and not using it with smolagents CodeAgent.

This demonstrates how CodeAgent needs fewer iterations when it knows
the output structure beforehand.
"""

import os
from textwrap import dedent

from dotenv import load_dotenv
from mcp import StdioServerParameters
from smolagents import CodeAgent, InferenceClientModel

from mcpadapt.core import MCPAdapt
from mcpadapt.smolagents_adapter import SmolAgentsAdapter

# Load environment variables
load_dotenv()

# Minimal MCP server that returns product information
server_script = dedent(
    """
    from mcp.server.fastmcp import FastMCP
    
    mcp = FastMCP("Product Server")
    
    @mcp.tool()
    def get_product_info(product_id: str) -> dict:
        '''Get detailed information about a product'''
        # Simulate a product database lookup
        products = {
            "laptop-123": {
                "name": "UltraBook Pro",
                "price": 1299,
                "stock": 15,
                "specs": {
                    "cpu": "Intel i7",
                    "ram": "16GB",
                    "storage": "512GB SSD"
                }
            }
        }
        return products.get(product_id, {"error": "Product not found"})
    
    mcp.run()
    """
)


def demo_without_structured_output():
    """Demo showing CodeAgent without structured output support."""
    print("\n=== Demo WITHOUT structured output ===\n")

    # Use the adapter WITHOUT structured output
    with MCPAdapt(
        StdioServerParameters(
            command="uv", args=["run", "python", "-c", server_script]
        ),
        SmolAgentsAdapter(structured_output=False),  # Disabled
    ) as tools:
        model = InferenceClientModel(token=os.getenv("HF_TOKEN"))
        agent = CodeAgent(tools=tools, model=model)

        # Ask for specific nested information
        result = agent.run(
            "What is the RAM specification of laptop-123? "
            "Return just the RAM value as a string."
        )
        print(f"Result: {result}")


def demo_with_structured_output():
    """Demo showing CodeAgent with structured output support."""
    print("\n=== Demo WITH structured output ===\n")

    # Use the adapter WITH structured output
    with MCPAdapt(
        StdioServerParameters(
            command="uv", args=["run", "python", "-c", server_script]
        ),
        SmolAgentsAdapter(structured_output=True),  # Enabled
    ) as tools:
        model = InferenceClientModel(token=os.getenv("HF_TOKEN"))
        agent = CodeAgent(tools=tools, model=model)

        # Ask for the same nested information
        result = agent.run(
            "What is the RAM specification of laptop-123? "
            "Return just the RAM value as a string."
        )
        print(f"Result: {result}")


if __name__ == "__main__":
    # Run both demos
    demo_without_structured_output()
    demo_with_structured_output()
