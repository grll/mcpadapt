import re
import keyword


def _sanitize_function_name(name):
    """
    A function to sanitize function names to be used as a tool name.
    Prevent the use of dashes or other python keywords as function names by tool.
    """
    # Replace dashes with underscores
    name = name.replace("-", "_")

    # Remove any characters that aren't alphanumeric or underscore
    name = re.sub(r"[^\w_]", "", name)

    # Ensure it doesn't start with a number
    if name[0].isdigit():
        name = f"_{name}"

    # Check if it's a Python keyword
    if keyword.iskeyword(name):
        name = f"{name}_"

    return name


# class LlamaIndexAdapter(ToolAdapter):
#     def adapt(
#         self,
#         func: Callable[[dict | None], mcp.types.CallToolResult],
#         mcp_tool: mcp.types.Tool,
#     ) -> FunctionTool:
#         mcp_tool_name = _sanitize_function_name(mcp_tool.name)
#         if mcp_tool_name != mcp_tool.name:
#             log.warning(f"MCP tool name {mcp_tool.name} sanitized to {mcp_tool_name}")

#         generate_class_template = partial(
#             _generate_tool_class,
#             mcp_tool_name,
#             mcp_tool.description,
#             mcp_tool.inputSchema,
#             False,
#         )
#         return _instanciate_tool(mcp_tool_name, generate_class_template, func)

#     def async_adapt(
#         self,
#         afunc: Callable[[dict | None], Coroutine[Any, Any, mcp.types.CallToolResult]],
#         mcp_tool: mcp.types.Tool,
#     ) -> BaseTool:
#         mcp_tool_name = _sanitize_function_name(mcp_tool.name)
#         if mcp_tool_name != mcp_tool.name:
#             log.warning(f"MCP tool name {mcp_tool.name} sanitized to {mcp_tool_name}")

#         generate_class_template = partial(
#             _generate_tool_class,
#             mcp_tool_name,
#             mcp_tool.description,
#             mcp_tool.inputSchema,
#             True,
#         )
#         return _instanciate_tool(mcp_tool_name, generate_class_template, afunc)
