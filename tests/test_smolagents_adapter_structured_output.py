from textwrap import dedent
import logging

import pytest
from mcp import StdioServerParameters

from mcpadapt.core import MCPAdapt
from mcpadapt.smolagents_adapter import SmolAgentsAdapter


def test_weather_sync():
    weather_server_script = dedent(
        """
        from mcp.server.fastmcp import FastMCP
        from typing import Any

        mcp = FastMCP("Weather Server")

        @mcp.tool()
        def weather_tool(location: str) -> dict[str, Any]:
            '''Get the weather for a given location'''
            return {
                "weather": "sunny",
                "temperature": 70,
                "humidity": 50,
                "wind_speed": 10,
            }

        mcp.run()
        """
    )
    with MCPAdapt(
        StdioServerParameters(
            command="uv", args=["run", "python", "-c", weather_server_script]
        ),
        SmolAgentsAdapter(structured_output=True),
    ) as tools:
        assert len(tools) == 1
        tool = tools[0]
        assert tool.name == "weather_tool"

        # Check tool properties and the auto-generated output schema
        assert tool.output_type == "object"
        assert tool.output_schema is not None

        # Verify the schema's structure and types
        assert tool.output_schema.get("type") == "object"
        assert tool.output_schema.get("additionalProperties") is True
        assert isinstance(tool.output_schema.get("title"), str)

        # Verify the tool call works as expected
        assert tool(location="New York") == {
            "weather": "sunny",
            "temperature": 70,
            "humidity": 50,
            "wind_speed": 10,
        }


def test_validation_warning_for_unparseable_json(caplog):
    """Tests that a warning is logged for unparseable JSON when a structured object is expected."""
    server_script = dedent(
        '''
        from mcp.server.fastmcp import FastMCP
        from typing import Any

        mcp = FastMCP("Validation Server")

        @mcp.tool()
        def returns_unparseable_text() -> dict[str, Any]:
            """
            This tool's type hint suggests a dict, which implies a structured
            output is expected. However, it returns a non-JSON string.
            FastMCP's runtime validation should catch this and return an error.
            """
            # Note: We return a string from a function hinted to return a dict.
            # This is bad practice, but tests client-side robustness.
            return "this is not a valid json object" # type: ignore

        mcp.run()
        '''
    )

    with MCPAdapt(
        StdioServerParameters(
            command="uv", args=["run", "python", "-c", server_script]
        ),
        SmolAgentsAdapter(structured_output=True),
    ) as tools:
        assert len(tools) == 1
        tool = tools[0]
        assert tool.name == "returns_unparseable_text"
        assert tool.output_type == "object"

        # The tool call returns an error string from FastMCP's validation.
        # We check that it's a string containing "error" to keep the test robust.
        result = tool()
        assert isinstance(result, str)
        assert "error" in result.lower()

        # We also check that our adapter logged a warning.
        # We check for the log level and the key concept ("unparseable"),
        # making the test robust against future changes to the log message.
        assert any(
            r.levelno == logging.WARNING and "unparseable" in r.message.lower()
            for r in caplog.records
        )


def test_list_cities_tool():
    """Ensure list outputs are wrapped into a dict and schema reflects this."""
    list_cities_server_script = dedent(
        '''
        from mcp.server.fastmcp import FastMCP
        from typing import Any

        mcp = FastMCP("Cities Server")

        # Lists are wrapped automatically by FastMCP as {"result": list}
        @mcp.tool()
        def list_cities() -> list[str]:
            """Get a list of cities"""
            return ["London", "Paris", "Tokyo"]

        mcp.run()
        '''
    )
    with MCPAdapt(
        StdioServerParameters(
            command="uv", args=["run", "python", "-c", list_cities_server_script]
        ),
        SmolAgentsAdapter(structured_output=True),
    ) as tools:
        assert len(tools) == 1
        tool = tools[0]
        assert tool.name == "list_cities"

        # Schema checks
        assert tool.output_type == "object"
        schema = tool.output_schema
        assert isinstance(schema, dict)
        assert schema.get("type") == "object"
        properties = schema.get("properties")
        assert isinstance(properties, dict)
        assert "result" in properties
        # The result property should describe an array of strings
        assert properties["result"].get("type") == "array"
        items = properties["result"].get("items", {})
        # Items type may not always be present, but if it is, should be string
        if isinstance(items, dict) and "type" in items:
            assert items["type"] == "string"

        # Call the tool and verify the wrapper structure
        result = tool()
        assert isinstance(result, dict)
        assert result["result"] == ["London", "Paris", "Tokyo"]

        # Check the actual city names returned
        cities = result["result"]
        assert "London" in cities
        assert "Paris" in cities
        assert "Tokyo" in cities


def test_simple_text_tool():
    """Tests structured output with fallback to string output."""
    server_script = dedent(
        """
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP("Simple Server")

        @mcp.tool()
        def hello_world():
            '''Returns a simple greeting.'''
            return "hello world"

        mcp.run()
        """
    )

    with MCPAdapt(
        StdioServerParameters(
            command="uv", args=["run", "python", "-c", server_script]
        ),
        SmolAgentsAdapter(structured_output=True),
    ) as tools:
        assert len(tools) == 1
        tool = tools[0]
        assert tool.name == "hello_world"

        # Verify that a simple string output results in "string" type and no schema
        assert tool.output_type == "string"
        assert tool.output_schema is None

        # Call the tool and check the output
        result = tool()
        assert result == "hello world"

