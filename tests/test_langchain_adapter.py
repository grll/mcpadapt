from textwrap import dedent
import mcp
from mcpadapt.core import MCPAdapt
from mcpadapt.langchain_adapter import LangChainAdapter

mcpserver_with_regular_docstring = dedent("""\
    import mcp
    from mcp.server.fastmcp import FastMCP
    
    mcp = FastMCP("Test MCP Server")

    @mcp.tool()
    def echo_tool(text: str) -> str:
        '''Echo the input text'''
        return text
""").strip()

mcpserver_with_google_style_docstring = dedent("""\
    import mcp
    from mcp.server.fastmcp import FastMCP
    
    mcp = FastMCP("Test MCP Server")

    @mcp.tool()
    def echo_tool(text: str) -> str:
        '''Echo the input text

        Args:
            text (str): The text to echo

        Returns:
            str: The echoed text
        '''
        return text
""").strip()


def test_success():
    print("success")
    assert True


def test_langchain_adapter_with_sync_func():
    print("test_langchain_adapter_with_sync_func")
    print(mcpserver_with_regular_docstring)
    serverparams = mcp.StdioServerParameters(
        command="uv",
        args=["run", "python", "-c", mcpserver_with_regular_docstring],
    )
    print(serverparams)
    with MCPAdapt(serverparams, LangChainAdapter()) as tools:
        print(tools)
        assert len(tools) == 1
        assert tools[0].name == "echo_tool"
        assert tools[0].description == "Echo the input text"
        assert tools[0].args == {"text": str}


# @pytest.mark.parametrize("mcpserver_script", [mcpserver_with_regular_docstring, mcpserver_with_google_style_docstring])
# def test_langchain_adapter_with_sync_func(mcpserver_script):
#     serverparams = mcp.StdioServerParameters(
#         command="python",
#         args=["-c", mcpserver_script],
#     )

#     with MCPAdapt(serverparams, LangChainAdapter()) as tools:
#         assert len(tools) == 1
#         assert tools[0].name == "echo_tool"
#         assert tools[0].description == "Echo the input text"
#         assert tools[0].args == {"text": str}

# @pytest.mark.asyncio
# @pytest.mark.parametrize("mcpserver_script", [mcpserver_with_regular_docstring, mcpserver_with_google_style_docstring])
# async def test_langchain_adapter_with_async_func(mcpserver_script):
#     serverparams = mcp.StdioServerParameters(
#         command="python",
#         args=["-c", mcpserver_script],
#     )

#     async with MCPAdapt(serverparams, LangChainAdapter()) as tools:
#         assert len(tools) == 1
#         assert tools[0].name == "echo_tool"
#         assert tools[0].description == "Echo the input text"
#         assert tools[0].args == {"text": str}
