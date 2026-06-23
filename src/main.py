from strands import Agent, tool
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from mcp import ClientSession
from strands.tools.mcp.mcp_agent_tool import MCPAgentTool
from mcp_client.client import AsyncMCPSession, get_litellm_transport
from model.load import load_model
import os

app = BedrockAgentCoreApp()

MEMORY_ID = os.getenv("MEMORY_ID", "wheelseyedemoMemory-XWdvwK9w90")

@tool
def add_numbers(a: int, b: int) -> int:
    """Return the sum of two numbers"""
    return a + b

@tool
def get_word_count(text: str) -> int:
    """Count the number of words in a text string"""
    return len(text.split())

@app.entrypoint
async def invoke(payload, context):
    from bedrock_agentcore.memory.integrations.strands.session_manager import AgentCoreMemorySessionManager
    from bedrock_agentcore.memory.integrations.strands.config import AgentCoreMemoryConfig

    session_id = payload.get("session_id", "default-session")
    actor_id = payload.get("actor_id", "default-user")

    config = AgentCoreMemoryConfig(
        memory_id=MEMORY_ID,
        session_id=session_id,
        actor_id=actor_id,
        batch_size=1,
        async_mode=True,
    )

    session_manager = AgentCoreMemorySessionManager(
        agentcore_memory_config=config,
        region_name=os.getenv("AWS_REGION", "ap-south-1"),
    )

    async with get_litellm_transport() as (read, write, _):
        async with ClientSession(read, write) as mcp_session:
            await mcp_session.initialize()
            tools_result = await mcp_session.list_tools()
            proxy = AsyncMCPSession(mcp_session)
            mcp_tools = [MCPAgentTool(t, proxy) for t in tools_result.tools]

            agent = Agent(
                model=load_model(),
                system_prompt="You are a helpful assistant for Wheelseye. Use tools when appropriate.",
                tools=[add_numbers, get_word_count, *mcp_tools],
                session_manager=session_manager,
            )

            parts = []
            async for event in agent.stream_async(payload.get("prompt", "Hello!")):
                if "data" in event and isinstance(event["data"], str):
                    parts.append(event["data"])
            return "".join(parts)

if __name__ == "__main__":
    app.run()
