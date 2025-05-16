"""
Tests for the modeling module, specifically focused on JSON Schema handling.
"""

from textwrap import dedent
import json

import pytest
from mcp import StdioServerParameters

from mcpadapt.core import MCPAdapt
from mcpadapt.crewai_adapter import CrewAIAdapter
from mcpadapt.utils.modeling import create_model_from_json_schema


@pytest.fixture
def json_schema_array_type_server_script():
    """
    Create a server with a tool that uses array notation for type fields.
    This tests handling of JSON Schema 'type': ['string', 'number'] syntax.
    """
    return dedent(
        '''
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP("JSON Schema Array Type Test Server")

        @mcp.tool()
        def multi_type_tool(
            id: str | int,  # This becomes {"type": ["string", "number"]} in JSON Schema
            name: str | None = None,  # Tests nullable with array type
        ) -> str:
            """Test tool with a parameter that accepts multiple types using array notation"""
            id_type = type(id).__name__
            return f"Received ID: {id} (type: {id_type}), Name: {name}"
        
        mcp.run()
        '''
    )


def test_json_schema_array_type_handling(json_schema_array_type_server_script):
    """
    Test that MCPAdapt correctly handles JSON Schema with array notation for types.
    This ensures our fix for 'unhashable type: list' error is working.
    """
    with MCPAdapt(
        StdioServerParameters(
            command="uv",
            args=["run", "python", "-c", json_schema_array_type_server_script],
        ),
        CrewAIAdapter(),
    ) as tools:
        # Verify the tool was successfully loaded
        assert len(tools) == 1
        assert tools[0].name == "multi_type_tool"

        # Test with string type
        result_string = tools[0].run(id="abc123", name="test")
        assert "Received ID: abc123 (type: str)" in result_string

        # Test with integer type
        result_int = tools[0].run(id=42, name="test")
        assert "Received ID: 42 (type: int)" in result_int

        # Test with nullable field
        result_null = tools[0].run(id="xyz789")
        assert "Received ID: xyz789" in result_null
        assert "Name: None" in result_null


def test_json_schema_array_type_with_null(json_schema_array_type_server_script):
    """
    Test that MCPAdapt correctly handles JSON Schema array types that include 'null'.
    This ensures our specific handling of null types works correctly.
    """
    with MCPAdapt(
        StdioServerParameters(
            command="uv",
            args=["run", "python", "-c", json_schema_array_type_server_script],
        ),
        CrewAIAdapter(),
    ) as tools:
        # The second parameter has type ["string", "null"] in JSON Schema
        # and should be properly handled
        tool = tools[0]

        # Test with string value
        result_with_value = tool.run(id="test123", name="some name")
        assert "Name: some name" in result_with_value

        # Test with null value (None in Python)
        result_with_null = tool.run(id="test456", name=None)
        assert "Name: None" in result_with_null


def test_json_schema_inspection(json_schema_array_type_server_script):
    """Print the actual JSON Schema to inspect the structure"""
    import sys

    # Create our adapter but don't use it directly - we just want to inspect
    adapter = MCPAdapt(
        StdioServerParameters(
            command="uv",
            args=["run", "python", "-c", json_schema_array_type_server_script],
        ),
        CrewAIAdapter(),
    )

    # If we can't access private attributes, skip the test
    if not hasattr(adapter, "_sessions"):
        print(
            "\nSkipping schema inspection - cannot access adapter internal structure",
            file=sys.stderr,
        )
        return

    try:
        # Enter the context to initialize connection
        with adapter as _:  # Use underscore to indicate unused variable
            # Now examine the internal state of the adapter
            sessions = adapter._sessions

            if sessions:
                for session_idx, session in enumerate(sessions):
                    if hasattr(session, "_mcp_server") and hasattr(
                        session._mcp_server, "tools"
                    ):
                        mcp_server = session._mcp_server
                        print(
                            f"\n\n=== Session {session_idx} Tools ===", file=sys.stderr
                        )

                        for tool_idx, tool in enumerate(mcp_server.tools):
                            print(
                                f"\nTool {tool_idx}: {getattr(tool, 'name', '[NO NAME]')}",
                                file=sys.stderr,
                            )

                            # Try to inspect the tool object
                            try:
                                print(
                                    f"Tool attrs: {dir(tool)[:10]}...", file=sys.stderr
                                )
                            except Exception as e:
                                print(
                                    f"Could not inspect tool attributes: {str(e)}",
                                    file=sys.stderr,
                                )

                            # Extract and print available schemas
                            for schema_attr in [
                                "param_schema",
                                "inputSchema",
                                "schema",
                            ]:
                                if hasattr(tool, schema_attr) and getattr(
                                    tool, schema_attr
                                ):
                                    print(f"{schema_attr}:", file=sys.stderr)
                                    print(
                                        json.dumps(
                                            getattr(tool, schema_attr), indent=2
                                        ),
                                        file=sys.stderr,
                                    )
    except Exception as e:
        print(f"Error during schema inspection: {e}", file=sys.stderr)


def test_direct_modeling_with_list_type():
    """
    Test the modeling module directly with a schema using list-type notation.
    This test is specifically designed to catch the "unhashable type: 'list'" error.
    """
    # Create a schema with list-type field
    schema = {
        "type": "object",
        "properties": {
            "multi_type_field": {
                "type": ["string", "number"],
                "description": "Field that accepts multiple types",
            },
            "nullable_field": {
                "type": ["string", "null"],
                "description": "Field that is nullable",
            },
        },
    }

    try:
        # Without the fix, this should raise TypeError due to using list as dict key
        model = create_model_from_json_schema(schema)

        # If we get here, the code is working (our fix is in place)
        # Verify the model works as expected
        instance = model(multi_type_field="test")
        assert instance.multi_type_field == "test"

        instance = model(multi_type_field=42)
        assert instance.multi_type_field == 42

        print("\nTest passed: Successfully created model with list-type fields")
    except TypeError as e:
        # The specific error we're trying to fix
        if "unhashable type: 'list'" in str(e):
            import sys

            print(f"\nCaught expected error: {str(e)}", file=sys.stderr)
            print(
                "This error occurs when processing JSON Schema with list-type fields.",
                file=sys.stderr,
            )
            print(
                "JSON Schema allows type: ['string', 'number'] syntax for multiple types.",
                file=sys.stderr,
            )
            pytest.fail(
                "Unable to handle JSON Schema with list-type fields (unhashable type: 'list')"
            )
        else:
            # Some other TypeError we weren't expecting
            raise
