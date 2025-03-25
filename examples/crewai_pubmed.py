"""An example of using the LangChain adapter to adapt MCP tools to LangChain tools.

This example uses the PubMed API to search for studies.
"""

import os

from crewai import Agent, Crew, Task  # type: ignore
from dotenv import load_dotenv
from mcp import StdioServerParameters

from mcpadapt.core import MCPAdapt
from mcpadapt.crewai_adapter import CrewAIAdapter

load_dotenv()
if not os.environ.get("OPENAI_API_KEY"):
    raise ValueError(
        "OPENAI_API_KEY is not set. Create a .env file at the root of the project with OPENAI_API_KEY=<your-api-key>"
    )

with MCPAdapt(
    StdioServerParameters(
        command="uvx",
        args=["--quiet", "pubmedmcp@0.1.3"],
        env={"UV_PYTHON": "3.12", **os.environ},
    ),
    CrewAIAdapter(),
) as tools:
    # print(tools[0].run(request={"term": "efficient treatment hangover"}))
    # print(tools[0])
    # print(tools[0].description)
    # Create a simple agent with the pubmcp tool
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

    # Create a crew
    crew = Crew(agents=[agent], tasks=[task], verbose=True)

    # Run the crew
    crew.kickoff()
