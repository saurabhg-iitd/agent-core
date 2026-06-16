from strands import Agent, tool
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from model.load import load_model

app = BedrockAgentCoreApp()

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
    agent = Agent(
        model=load_model(),
        system_prompt="You are a helpful assistant for Wheelseye. Use tools when appropriate.",
        tools=[add_numbers, get_word_count],
    )

    stream = agent.stream_async(payload.get("prompt", "Hello!"))

    async for event in stream:
        if "data" in event and isinstance(event["data"], str):
            yield event["data"]

if __name__ == "__main__":
    app.run()