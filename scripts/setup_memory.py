"""
One-time script to create the AWS Bedrock AgentCore Memory Resource.
Run this ONCE, then copy the printed memory_id into:
  - src/main.py  (MEMORY_ID constant)
  - .bedrock_agentcore.yaml  (memory.memory_id and memory.memory_name)
"""
from bedrock_agentcore.memory import MemoryClient

client = MemoryClient(region_name="ap-south-1")

print("Creating memory resource... (this may take 1-2 minutes)")

memory = client.create_memory_and_wait(
    name="wheelseyedemoMemory",
    strategies=[
        {"semanticMemoryStrategy": {"name": "FactExtractor"}},
        {"summaryMemoryStrategy": {"name": "SessionSummarizer"}},
        {"userPreferenceMemoryStrategy": {"name": "PreferenceLearner"}},
    ],
    event_expiry_days=30,
)

print("\n✅ Memory resource created successfully!")
print(f"   Memory ID  : {memory['memoryId']}")
print(f"   Memory ARN : {memory['memoryArn']}")
print(f"   Status     : {memory['status']}")
print("\nNext steps:")
print("  1. Copy the Memory ID above into src/main.py  →  MEMORY_ID = \"<id>\"")
print("  2. Update .bedrock_agentcore.yaml:")
print("       memory:")
print("         mode: LONG_TERM_MEMORY")
print(f"         memory_id: \"{memory['memoryId']}\"")
print(f"         memory_arn: \"{memory['memoryArn']}\"")
print("         memory_name: \"wheelseyedemoMemory\"")
print("  3. Run: agentcore deploy")
