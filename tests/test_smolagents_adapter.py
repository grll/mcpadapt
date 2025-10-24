import logging
from pathlib import Path
from textwrap import dedent

import pytest
from mcp import StdioServerParameters

from mcpadapt.core import MCPAdapt
from mcpadapt.smolagents_adapter import SmolAgentsAdapter
from tests._server_utils import launch_mcp_server, terminate_mcp_server


@pytest.fixture
def echo_server_script():
    return dedent(
        '''
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP("Echo Server")

        @mcp.tool()
        def echo_tool(text: str) -> str:
            """Echo the input text"""
            return f"Echo: {text}"

        mcp.run()
        '''
    )


@pytest.fixture
def echo_server_sse_script():
    return dedent(
        '''
        import os
        from mcp.server.fastmcp import FastMCP

        port = int(os.environ.get("MCP_TEST_PORT", "8000"))

        mcp = FastMCP("Echo Server", host="127.0.0.1", port=port)

        @mcp.tool()
        def echo_tool(text: str) -> str:
            """Echo the input text"""
            return f"Echo: {text}"

        mcp.run("sse")
        '''
    )


@pytest.fixture
def echo_server_optional_script():
    return dedent(
        '''
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP("Echo Server")

        @mcp.tool()
        def echo_tool_optional(text: str | None = None) -> str:
            """Echo the input text, or return a default message if no text is provided"""
            if text is None:
                return "No input provided"
            return f"Echo: {text}"

        @mcp.tool()
        def echo_tool_default_value(text: str = "empty") -> str:
            """Echo the input text, default to 'empty' if no text is provided"""
            return f"Echo: {text}"

        @mcp.tool()
        def echo_tool_union_none(text: str | None) -> str:
            """Echo the input text, but None is not specified by default."""
            if text is None:
                return "No input provided"
            return f"Echo: {text}"

        mcp.run()
        '''
    )


@pytest.fixture
async def echo_sse_server(echo_server_sse_script):
    try:
        process, port = launch_mcp_server(echo_server_sse_script)
    except RuntimeError as exc:
        pytest.skip(str(exc))

    try:
        yield {"url": f"http://127.0.0.1:{port}/sse"}
    finally:
        terminate_mcp_server(process)


def test_basic_sync(echo_server_script):
    with MCPAdapt(
        StdioServerParameters(
            command="uv", args=["run", "python", "-c", echo_server_script]
        ),
        SmolAgentsAdapter(),
    ) as tools:
        assert len(tools) == 1
        assert tools[0].name == "echo_tool"
        assert tools[0](text="hello") == "Echo: hello"


def test_basic_sync_sse(echo_sse_server):
    sse_serverparams = echo_sse_server
    with MCPAdapt(
        sse_serverparams,
        SmolAgentsAdapter(),
    ) as tools:
        assert len(tools) == 1
        assert tools[0].name == "echo_tool"
        assert tools[0](text="hello") == "Echo: hello"


def test_optional_sync(echo_server_optional_script):
    with MCPAdapt(
        StdioServerParameters(
            command="uv", args=["run", "python", "-c", echo_server_optional_script]
        ),
        SmolAgentsAdapter(),
    ) as tools:
        assert len(tools) == 3
        assert tools[0].name == "echo_tool_optional"
        assert tools[0](text="hello") == "Echo: hello"
        assert tools[0]() == "No input provided"
        assert tools[1].name == "echo_tool_default_value"
        assert tools[1](text="hello") == "Echo: hello"
        assert tools[1]() == "Echo: empty"
        assert tools[2].name == "echo_tool_union_none"
        assert tools[2](text="hello") == "Echo: hello"


def test_tool_name_with_dashes():
    mcp_server_script = dedent(
        '''
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP("Echo Server")

        @mcp.tool(name="echo-tool")
        def echo_tool(text: str) -> str:
            """Echo the input text"""
            return f"Echo: {text}"

        mcp.run()
        '''
    )
    with MCPAdapt(
        StdioServerParameters(
            command="uv", args=["run", "python", "-c", mcp_server_script]
        ),
        SmolAgentsAdapter(),
    ) as tools:
        assert len(tools) == 1
        assert tools[0].name == "echo_tool"
        assert tools[0](text="hello") == "Echo: hello"


def test_tool_name_with_keyword():
    mcp_server_script = dedent(
        '''
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP("Echo Server")

        @mcp.tool(name="def")
        def echo_tool(text: str) -> str:
            """Echo the input text"""
            return f"Echo: {text}"

        mcp.run()
        '''
    )
    with MCPAdapt(
        StdioServerParameters(
            command="uv", args=["run", "python", "-c", mcp_server_script]
        ),
        SmolAgentsAdapter(),
    ) as tools:
        assert len(tools) == 1
        assert tools[0].name == "def_"
        assert tools[0](text="hello") == "Echo: hello"


@pytest.fixture
def shared_datadir():
    return Path(__file__).parent / "data"


def test_image_tool(shared_datadir):
    mcp_server_script = dedent(
        f"""
        import os
        from mcp.server.fastmcp import FastMCP, Image

        mcp = FastMCP("Image Server")

        @mcp.tool("test_image")
        def test_image() -> Image:
            path = os.path.join("{shared_datadir}", "random_image.png")
            return Image(path=path, format='png')

        mcp.run()
        """
    )
    with MCPAdapt(
        StdioServerParameters(
            command="uv", args=["run", "python", "-c", mcp_server_script]
        ),
        SmolAgentsAdapter(),
    ) as tools:
        from PIL.ImageFile import ImageFile

        assert len(tools) == 1
        assert tools[0].name == "test_image"
        image_content = tools[0]()
        assert isinstance(image_content, ImageFile)
        assert image_content.size == (256, 256)


def test_audio_tool(shared_datadir):
    try:
        from torchcodec.decoders import AudioDecoder  # noqa: F401
    except ImportError:
        pytest.skip(
            "TorchCodec not installed; install torchcodec to run test_audio_tool. (uv add mcpadapt[audio])"
        )
    except RuntimeError:
        pytest.skip(
            "Couldn't load AudioDecoder from torchcodec. Likely because of runtime depedency (ffmpeg not installed or incompatible torch version)"
        )

    mcp_server_script = dedent(
        f"""
        import os
        import base64
        from mcp.server.fastmcp import FastMCP
        from mcp.types import AudioContent

        mcp = FastMCP("Audio Server")

        @mcp.tool("test_audio")
        def test_audio() -> AudioContent:
            path = os.path.join("{shared_datadir}", "white_noise.wav")
            with open(path, "rb") as f:
                wav_bytes = f.read()

            return AudioContent(type="audio", data=base64.b64encode(wav_bytes).decode(), mimeType="audio/wav")

        mcp.run()
        """
    )
    with MCPAdapt(
        StdioServerParameters(
            command="uv", args=["run", "python", "-c", mcp_server_script]
        ),
        SmolAgentsAdapter(),
    ) as tools:
        from torch import Tensor  # type: ignore

        assert len(tools) == 1
        assert tools[0].name == "test_audio"
        audio_content = tools[0]()
        assert isinstance(audio_content, Tensor)


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
        assert dict_result["weather"] == "sunny"
        assert dict_result["temperature"] == 70

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


def test_structured_output_warning(caplog):
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
