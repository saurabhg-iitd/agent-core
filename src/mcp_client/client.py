import base64
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.types import (
    TextContent as MCPTextContent,
    ImageContent as MCPImageContent,
    EmbeddedResource as MCPEmbeddedResource,
    TextResourceContents,
)
from strands.tools.mcp.mcp_types import MCPToolResult

LITELLM_MCP_ENDPOINT = "http://litellm.prod-we.com/mcp"
LITELLM_API_KEY = "Bearer sk-ETFcYN4ay5SmXs5B1NEXpg"

MIME_TO_FORMAT = {
    "image/jpeg": "jpeg",
    "image/png": "png",
    "image/gif": "gif",
    "image/webp": "webp",
}


class AsyncMCPSession:
    """Wraps MCP ClientSession as a drop-in for MCPClient — no background thread."""

    def __init__(self, session: ClientSession):
        self._session = session

    def _map_content(self, content):
        if isinstance(content, MCPTextContent):
            return {"text": content.text}
        elif isinstance(content, MCPImageContent):
            return {
                "image": {
                    "format": MIME_TO_FORMAT.get(content.mimeType, "jpeg"),
                    "source": {"bytes": base64.b64decode(content.data)},
                }
            }
        elif isinstance(content, MCPEmbeddedResource):
            resource = content.resource
            if isinstance(resource, TextResourceContents):
                return {"text": resource.text}
        return None

    async def call_tool_async(self, tool_use_id, name, arguments=None, read_timeout_seconds=None, meta=None):
        try:
            result = await self._session.call_tool(name, arguments or {})
            contents = [c for item in result.content if (c := self._map_content(item)) is not None]
            tool_result = MCPToolResult(
                status="error" if result.isError else "success",
                toolUseId=tool_use_id,
                content=contents,
            )
            if result.isError is not None:
                tool_result["isError"] = result.isError
            return tool_result
        except Exception as e:
            return MCPToolResult(
                status="error",
                toolUseId=tool_use_id,
                content=[{"text": f"Tool execution failed: {str(e)}"}],
            )


def get_litellm_transport():
    return streamablehttp_client(
        LITELLM_MCP_ENDPOINT,
        headers={"x-litellm-api-key": LITELLM_API_KEY},
    )
