from strands import Agent, tool
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from mcp import ClientSession
from strands.tools.mcp.mcp_agent_tool import MCPAgentTool
from mcp_client.client import AsyncMCPSession, get_litellm_transport
from model.load import load_model
import os

app = BedrockAgentCoreApp()

MEMORY_ID = os.getenv("MEMORY_ID", "wheelseyedemoMemory-XWdvwK9w90")
REGION = os.getenv("AWS_REGION", "ap-south-1")
ENABLE_MCP = os.getenv("ENABLE_MCP", "true").lower() in ("true", "1", "yes")
ENABLE_MEMORY = os.getenv("ENABLE_MEMORY", "true").lower() in ("true", "1", "yes")

@tool
def add_numbers(a: int, b: int) -> int:
    """Return the sum of two numbers"""
    return a + b

@tool
def get_word_count(text: str) -> int:
    """Count the number of words in a text string"""
    return len(text.split())

def _build_session_manager(session_id: str, actor_id: str):
    if not ENABLE_MEMORY:
        return None

    from bedrock_agentcore.memory.integrations.strands.session_manager import AgentCoreMemorySessionManager
    from bedrock_agentcore.memory.integrations.strands.config import AgentCoreMemoryConfig

    config = AgentCoreMemoryConfig(
        memory_id=MEMORY_ID,
        session_id=session_id,
        actor_id=actor_id,
        batch_size=1,
        async_mode=True,
    )
    return AgentCoreMemorySessionManager(
        agentcore_memory_config=config,
        region_name=REGION,
    )

def _build_agent(session_manager, mcp_tools, session_id: str):
    kwargs = {
        "model": load_model(),
        "system_prompt": "You are a helpful assistant for Wheelseye. Use tools when appropriate.",
        "tools": [add_numbers, get_word_count, *mcp_tools],
        # Required for AgentCore evaluation — emits strands.telemetry.tracer spans to aws/spans
        "trace_attributes": {"session.id": session_id},
    }
    if session_manager is not None:
        kwargs["session_manager"] = session_manager
    return Agent(**kwargs)

async def _run_agent(agent: Agent, prompt: str) -> str:
    result = await agent.invoke_async(prompt)
    return str(result).strip()

async def _invoke_agent(session_manager, prompt: str, mcp_tools, session_id: str):
    agent = _build_agent(session_manager, mcp_tools, session_id)
    return await _run_agent(agent, prompt)

@app.entrypoint
async def invoke(payload, context):
    session_id = getattr(context, "session_id", None) or payload.get("session_id", "default-session")
    actor_id = payload.get("actor_id", "default-user")
    prompt = payload.get("prompt", "Hello!")

    try:
        session_manager = _build_session_manager(session_id, actor_id)

        if ENABLE_MCP:
            try:
                async with get_litellm_transport() as (read, write, _):
                    async with ClientSession(read, write) as mcp_session:
                        await mcp_session.initialize()
                        tools_result = await mcp_session.list_tools()
                        proxy = AsyncMCPSession(mcp_session)
                        mcp_tools = [MCPAgentTool(t, proxy) for t in tools_result.tools]
                        text = await _invoke_agent(session_manager, prompt, mcp_tools, session_id)
                        return {"result": text}
            except Exception as e:
                app.logger.warning(
                    "MCP unavailable, falling back to local tools: %s: %s",
                    type(e).__name__,
                    e,
                )

        text = await _invoke_agent(session_manager, prompt, [], session_id)
        return {"result": text}
    except Exception as e:
        app.logger.exception("Invoke failed for prompt=%r", prompt)
        return {"error": str(e), "error_type": type(e).__name__}

if __name__ == "__main__":
    app.run()
