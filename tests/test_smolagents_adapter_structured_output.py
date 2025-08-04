from textwrap import dedent
import logging

from mcp import StdioServerParameters

from mcpadapt.core import MCPAdapt
from mcpadapt.smolagents_adapter import SmolAgentsAdapter


def test_structured_output_types():
    """Test that structured output returns correct types for different return annotations."""
    server_script = dedent(
        """
        from mcp.server.fastmcp import FastMCP
        from typing import Any

        mcp = FastMCP("Types Server")

        @mcp.tool()
        def dict_tool() -> dict[str, Any]:
            '''Returns a dictionary'''
            return {"weather": "sunny", "temperature": 70}

        @mcp.tool()
        def list_tool() -> list[str]:
            '''Returns a list'''
            return ["London", "Paris", "Tokyo"]

        @mcp.tool()
        def string_tool() -> str:
            '''Returns a string'''
            return "Hello world"

        mcp.run()
        """
    )

    with MCPAdapt(
        StdioServerParameters(
            command="uv", args=["run", "python", "-c", server_script]
        ),
        SmolAgentsAdapter(structured_output=True),
    ) as tools:
        dict_tool, list_tool, string_tool = tools

        # Dict tool: should return dict directly with schema
        assert dict_tool.output_type == "object"
        assert dict_tool.output_schema is not None
        dict_result = dict_tool()
        assert isinstance(dict_result, dict)
        assert dict_result == {"weather": "sunny", "temperature": 70}

        # List tool: should be wrapped in {"result": list} with schema
        assert list_tool.output_type == "object"
        assert list_tool.output_schema is not None
        list_result = list_tool()
        assert isinstance(list_result, dict)
        assert "result" in list_result
        assert set(list_result["result"]) == {"London", "Paris", "Tokyo"}

        # String tool: should be wrapped in {"result": string} with schema
        assert string_tool.output_type == "object"
        assert string_tool.output_schema is not None
        string_result = string_tool()
        assert isinstance(string_result, dict)
        assert "result" in string_result
        assert string_result["result"] == "Hello world"


def test_unparseable_json_warning(caplog):
    """Test that warning is logged when tool returns unparseable JSON for structured output."""
    server_script = dedent(
        '''
        from mcp.server.fastmcp import FastMCP
        from typing import Any

        mcp = FastMCP("Invalid Server")

        @mcp.tool()
        def invalid_tool() -> dict[str, Any]:
            """Tool that returns invalid JSON when dict is expected."""
            return "not valid json" # type: ignore

        mcp.run()
        '''
    )

    with MCPAdapt(
        StdioServerParameters(
            command="uv", args=["run", "python", "-c", server_script]
        ),
        SmolAgentsAdapter(structured_output=True),
    ) as tools:
        tool = tools[0]

        # Tool should still work but return error string
        result = tool()
        assert isinstance(result, str)
        assert "error" in result.lower()

        # Warning should be logged about unparseable JSON
        assert any(
            r.levelno == logging.WARNING and "unparseable" in r.message.lower()
            for r in caplog.records
        )


def test_backwards_compatibility():
    """Test that structured_output=False vs True behave as expected."""
    server_script = dedent(
        """
        from mcp.server.fastmcp import FastMCP
        from typing import Any

        mcp = FastMCP("Compat Server")

        @mcp.tool()
        def data_tool() -> dict[str, Any]:
            return {"status": "ok", "value": 42}

        mcp.run()
        """
    )

    # Legacy mode: structured_output=False
    with MCPAdapt(
        StdioServerParameters(
            command="uv", args=["run", "python", "-c", server_script]
        ),
        SmolAgentsAdapter(structured_output=False),
    ) as legacy_tools:
        tool = legacy_tools[0]
        assert tool.output_schema is None
        assert tool.structured_output is False

        result = tool()
        # Legacy returns JSON string
        assert isinstance(result, str)
        assert "ok" in result

    # Enhanced mode: structured_output=True
    with MCPAdapt(
        StdioServerParameters(
            command="uv", args=["run", "python", "-c", server_script]
        ),
        SmolAgentsAdapter(structured_output=True),
    ) as enhanced_tools:
        tool = enhanced_tools[0]
        assert tool.output_schema is not None
        assert tool.structured_output is True

        result = tool()
        # Enhanced returns dict
        assert isinstance(result, dict)
        assert result["status"] == "ok"
        assert result["value"] == 42

