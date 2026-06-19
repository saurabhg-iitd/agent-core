from mcp.client.streamable_http import streamablehttp_client
from strands.tools.mcp.mcp_client import MCPClient

LITELLM_MCP_ENDPOINT = "http://litellm.prod-we.com/mcp"
LITELLM_API_KEY = "Bearer sk-ETFcYN4ay5SmXs5B1NEXpg"

def get_litellm_mcp_client() -> MCPClient:
    return MCPClient(lambda: streamablehttp_client(
        LITELLM_MCP_ENDPOINT,
        headers={"x-litellm-api-key": LITELLM_API_KEY},
    ))
