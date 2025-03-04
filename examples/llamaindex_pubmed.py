import os

from mcp import StdioServerParameters
from smolagents import CodeAgent, HfApiModel

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
    print(tools[0](request={"term": "efficient treatment hangover"}))
    agent = CodeAgent(tools=tools, model=HfApiModel())
    agent.run("Find studies about hangover?")
