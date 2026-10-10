"""Offline regressions for MCP execution status through the native Tool call path."""

import pytest
from mcp.types import CallToolResult, ImageContent, TextContent, Tool
from smolagents import Tool as SmolTool

from mcpadapt.smolagents_adapter import MCPToolExecutionError, SmolAgentsAdapter


def adapt_result(result: CallToolResult, structured_output: bool) -> SmolTool:
    definition = Tool(
        name="synthetic_lookup",
        description="Offline synthetic lookup",
        inputSchema={"type": "object", "properties": {}},
    )
    return SmolAgentsAdapter(structured_output=structured_output).adapt(
        lambda arguments: result, definition
    )


@pytest.mark.parametrize("structured_output", [False, True])
@pytest.mark.parametrize("structured_content", [None, {}, {"results": []}])
def test_mcp_error_retains_all_text_and_full_result(
    structured_output: bool, structured_content: dict | None
) -> None:
    result = CallToolResult(
        content=[
            TextContent(type="text", text="Synthetic backend failure"),
            TextContent(type="text", text="Retry after reconnecting"),
        ],
        structuredContent=structured_content,
        isError=True,
    )
    with pytest.raises(MCPToolExecutionError) as exc:
        adapt_result(result, structured_output)()
    assert exc.value.tool_name == "synthetic_lookup"
    assert exc.value.result is result
    assert "isError=True" in str(exc.value)
    assert "Synthetic backend failure" in str(exc.value)
    assert "Retry after reconnecting" in str(exc.value)
    if structured_content is not None:
        assert "structuredContent:" in str(exc.value)


@pytest.mark.parametrize("structured_output", [False, True])
@pytest.mark.parametrize(
    "content",
    [[], [ImageContent(type="image", data="AA==", mimeType="image/png")]],
)
def test_mcp_error_without_text_is_still_an_execution_error(
    structured_output: bool, content: list
) -> None:
    result = CallToolResult(content=content, isError=True)
    with pytest.raises(MCPToolExecutionError, match="isError=True") as exc:
        adapt_result(result, structured_output)()
    assert exc.value.result is result


@pytest.mark.parametrize("explicit_status", [False, True])
@pytest.mark.parametrize(
    "payload", [{}, {"results": []}, {"results": [{"id": "example"}]}]
)
@pytest.mark.parametrize("content", [[], [TextContent(type="text", text="fallback")]])
def test_success_returns_available_structured_content_unchanged(
    explicit_status: bool, payload: dict, content: list
) -> None:
    result = CallToolResult(
        content=content,
        structuredContent=payload,
        **({"isError": False} if explicit_status else {}),
    )
    assert adapt_result(result, True)() is result.structuredContent


@pytest.mark.parametrize("structured_output", [False, True])
def test_valid_empty_lookup_keeps_existing_text_behavior(
    structured_output: bool,
) -> None:
    result = CallToolResult(
        content=[TextContent(type="text", text='{"results": []}')],
        structuredContent={"results": []},
        isError=False,
    )
    assert adapt_result(result, structured_output)() == (
        {"results": []} if structured_output else '{"results": []}'
    )


def test_successful_json_text_fallback() -> None:
    result = CallToolResult(content=[TextContent(type="text", text='{"results": []}')])
    assert adapt_result(result, True)() == {"results": []}


@pytest.mark.parametrize("structured_output", [False, True])
def test_success_with_no_usable_content_preserves_validation(
    structured_output: bool,
) -> None:
    with pytest.raises(ValueError, match="returned an empty content"):
        adapt_result(CallToolResult(content=[]), structured_output)()


def test_smolagents_execution_wraps_error_with_details_and_cause() -> None:
    from smolagents import ToolCallingAgent
    from smolagents.utils import AgentToolExecutionError

    result = CallToolResult(
        content=[TextContent(type="text", text="Synthetic backend failure")],
        structuredContent={"results": [], "code": "BACKEND_UNAVAILABLE"},
        isError=True,
    )
    tool = adapt_result(result, True)
    # Executing a tool does not call the model; no API key or model inference needed.
    agent = ToolCallingAgent(tools=[tool], model=lambda *args, **kwargs: None)
    with pytest.raises(AgentToolExecutionError) as exc:
        agent.execute_tool_call(tool.name, {})
    assert "Synthetic backend failure" in str(exc.value)
    assert "BACKEND_UNAVAILABLE" in str(exc.value)
    assert isinstance(exc.value.__cause__, MCPToolExecutionError)
    assert exc.value.__cause__.result is result


def test_error_with_only_structured_details() -> None:
    result = CallToolResult(
        content=[], structuredContent={"code": "BACKEND_UNAVAILABLE"}, isError=True
    )
    with pytest.raises(MCPToolExecutionError, match="BACKEND_UNAVAILABLE"):
        adapt_result(result, True)()


def test_successful_unparseable_text_still_warns(caplog) -> None:
    result = CallToolResult(content=[TextContent(type="text", text="plain text")])
    assert adapt_result(result, True)() == "plain text"
    assert "unparseable text" in caplog.text
