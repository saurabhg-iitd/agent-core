from strands import Agent, tool
from bedrock_agentcore.runtime import BedrockAgentCoreApp
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

    agent = Agent(
        model=load_model(),
        system_prompt="You are a helpful assistant for Wheelseye. Use tools when appropriate.",
        tools=[add_numbers, get_word_count],
        session_manager=session_manager,
    )

    stream = agent.stream_async(payload.get("prompt", "Hello!"))

    async for event in stream:
        if "data" in event and isinstance(event["data"], str):
            yield event["data"]

if __name__ == "__main__":
    app.run()
