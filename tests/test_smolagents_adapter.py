from textwrap import dedent

import pytest
from mcp import StdioServerParameters

from mcpadapt.core import MCPAdapt
from mcpadapt.smolagents_adapter import SmolAgentsAdapter


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
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP("Echo Server", host="127.0.0.1", port=8000)

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
    import subprocess
    import time

    # Start the SSE server process with its own process group
    process = subprocess.Popen(
        ["python", "-c", echo_server_sse_script],
    )

    # Give the server a moment to start up
    time.sleep(1)

    try:
        yield {"url": "http://127.0.0.1:8000/sse"}
    finally:
        # Clean up the process when test is done
        process.kill()
        process.wait()


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

def test_image_tool():
    mcp_server_script = dedent(
        '''
        import io
        import random
        from mcp.server.fastmcp import FastMCP, Image as FastMCPImage
        from PIL import Image, ImageDraw

        mcp = FastMCP("Image Server")

        @mcp.tool("test_image")
        def test_image() -> FastMCPImage:
            width = 100
            height = 100
        
            random.seed(42)
            image = Image.new("RGB", (width, height))
            draw = ImageDraw.Draw(image)
        
            for x in range(0, width, 2):
                for y in range(0, height, 2):
                    color = (
                        random.randint(0, 255),
                        random.randint(0, 255),
                        random.randint(0, 255),
                    )
                    draw.rectangle([x, y, x + 1, y + 1], fill=color)
        
            buffer = io.BytesIO()
            image.save(buffer, format='PNG')
            buffer.seek(0)
            return FastMCPImage(data=buffer.read(), format='png')

        mcp.run()
        '''
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
        assert image_content.size == (100, 100)

def test_audio_tool():
    mcp_server_script = dedent(
        '''
        import os
        import torch
        import tempfile
        import torchaudio
        import base64
        from mcp.server.fastmcp import FastMCP
        from mcp.types import AudioContent

        mcp = FastMCP("Audio Server")

        @mcp.tool("test_audio")
        def test_audio() -> AudioContent:
        
            duration: float = 2.0
            sample_rate: int = 16000
            amplitude: float = 0.3
        
            # Generate random noise
            num_samples = int(duration * sample_rate)
            audio = amplitude * torch.randn(1, num_samples)
        
            # Convert to WAV bytes
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                tmp_path = tmp_file.name
        
            try:
                # Save audio to temporary file
                torchaudio.save(tmp_path, audio, sample_rate)
        
                # Read the file back as bytes
                with open(tmp_path, "rb") as f:
                    wav_bytes = f.read()
        
            finally:
                # Clean up temporary file
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
        
            return AudioContent(type="audio", data=base64.b64encode(wav_bytes).decode(), mimeType="audio/wav")

        mcp.run()
        '''
    )
    with MCPAdapt(
        StdioServerParameters(
            command="uv", args=["run", "python", "-c", mcp_server_script]
        ),
        SmolAgentsAdapter(),
    ) as tools:
        from torch import Tensor
        assert len(tools) == 1
        assert tools[0].name == "test_audio"
        audio_content = tools[0]()
        assert isinstance(audio_content, Tensor)