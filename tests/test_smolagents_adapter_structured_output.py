from textwrap import dedent
import logging

from mcp import StdioServerParameters

from mcpadapt.core import MCPAdapt
from mcpadapt.smolagents_adapter import SmolAgentsAdapter


def test_weather_sync():
    """Tests structured tool output. Expects a output schema and a dict from the tool call."""
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

        # Verify that a simple object output results in "object" type and no schema
        assert tool.output_type == "object"
        assert tool.output_schema is None

        # Call the tool and check the output
        result = tool()
        assert result == "hello world"


def test_backwards_compatibility():
    """Tests that the same tools work consistently with structured_output=False and True.

    This ensures existing code doesn't break when upgrading and that tools
    behave predictably regardless of the structured_output setting.
    """
    server_script = dedent(
        """
        from mcp.server.fastmcp import FastMCP
        from typing import Any

        mcp = FastMCP("Compatibility Server")

        @mcp.tool()
        def simple_text_tool(message: str) -> str:
            '''Returns a simple text message'''
            return f"Echo: {message}"

        @mcp.tool()
        def structured_data_tool(location: str) -> dict[str, Any]:
            '''Returns structured weather data'''
            return {
                "location": location,
                "weather": "sunny",
                "temperature": 22,
                "humidity": 65
            }

        mcp.run()
        """
    )

    # Test with legacy behavior (structured_output=False)
    with MCPAdapt(
        StdioServerParameters(
            command="uv", args=["run", "python", "-c", server_script]
        ),
        SmolAgentsAdapter(structured_output=False),
    ) as legacy_tools:
        # We know the tools are created in order, so we can use simple indexing
        simple_tool_legacy = legacy_tools[0]  # simple_text_tool
        structured_tool_legacy = legacy_tools[1]  # structured_data_tool

        # Verify we got the right tools
        assert simple_tool_legacy.name == "simple_text_tool"
        assert structured_tool_legacy.name == "structured_data_tool"

        # Both tools should have object output_type in legacy mode
        assert simple_tool_legacy.output_type == "object"
        assert structured_tool_legacy.output_type == "object"
        assert simple_tool_legacy.output_schema is None
        assert structured_tool_legacy.output_schema is None
        assert simple_tool_legacy.use_structured_features is False
        assert structured_tool_legacy.use_structured_features is False

        # Call the tools in legacy mode
        simple_result_legacy = simple_tool_legacy(message="test")
        structured_result_legacy = structured_tool_legacy(location="London")

        assert simple_result_legacy == "Echo: test"
        # structured_tool result should be JSON string in legacy mode
        assert isinstance(structured_result_legacy, str)
        assert "London" in structured_result_legacy
        assert "sunny" in structured_result_legacy

    # Test with enhanced behavior (structured_output=True)
    with MCPAdapt(
        StdioServerParameters(
            command="uv", args=["run", "python", "-c", server_script]
        ),
        SmolAgentsAdapter(structured_output=True),
    ) as enhanced_tools:
        # Same tools, same order - much clearer than complex searching
        simple_tool_enhanced = enhanced_tools[0]  # simple_text_tool
        structured_tool_enhanced = enhanced_tools[1]  # structured_data_tool

        # Verify we got the right tools
        assert simple_tool_enhanced.name == "simple_text_tool"
        assert structured_tool_enhanced.name == "structured_data_tool"

        # Both tools get enhanced features and schemas
        assert simple_tool_enhanced.output_type == "object"  # FastMCP auto-generates schema even for object
        assert simple_tool_enhanced.output_schema is not None  # Schema exists for object return type
        assert simple_tool_enhanced.use_structured_features is True

        assert structured_tool_enhanced.output_type == "object"
        assert structured_tool_enhanced.output_schema is not None
        assert structured_tool_enhanced.use_structured_features is True

        # Call the tools in enhanced mode
        simple_result_enhanced = simple_tool_enhanced(message="test")
        structured_result_enhanced = structured_tool_enhanced(location="London")

        # Key behavior differences discovered by this test:

        # Simple text tools - enhanced mode wraps results
        assert isinstance(simple_result_enhanced, dict)
        assert simple_result_enhanced["result"] == "Echo: test"  # Wrapped in result object
        # vs legacy mode returns plain string: "Echo: test"

        # Structured tools show the format difference:
        assert isinstance(structured_result_enhanced, dict)  # Dict in enhanced mode
        assert structured_result_enhanced["location"] == "London"
        assert structured_result_enhanced["weather"] == "sunny"

        # Legacy mode returns JSON string, enhanced mode returns dict
        # But both contain the same underlying data
        import json
        parsed_legacy_result = json.loads(structured_result_legacy)
        assert parsed_legacy_result == structured_result_enhanced  # Same data, different format

        # Backwards compatibility verified:
        # - Legacy mode: Returns raw data (strings as strings, dicts as JSON strings)
        # - Enhanced mode: Returns structured objects (strings wrapped, dicts native)
        # - Both contain the same information, just in different formats
        # - Existing code will keep working, new code gets enhanced features

