"""
Dataset evaluation — runs agent against fixed test scenarios and scores results.
Run once to create dataset, then reuse dataset_id for future runs.
"""
from bedrock_agentcore.evaluation import DatasetClient
from bedrock_agentcore_starter_toolkit import Evaluation

REGION = "ap-south-1"
AGENT_ID = "wheelseyedemo_Agent-L3yc137oAy"

client = DatasetClient(region_name=REGION)

# Step 1: Create dataset with test scenarios
print("Creating dataset...")
ds = client.create_dataset_and_wait(
    datasetName="wheelseyedemo_test_dataset",
    schemaType="AGENTCORE_EVALUATION_PREDEFINED_V1",
    source={
        "inlineExamples": {
            "examples": [
                {
                    "scenario_id": "TC-01",
                    "turns": [{"input": "Add 5 and 3"}],
                    "assertions": ["Response contains 8"],
                },
                {
                    "scenario_id": "TC-02",
                    "turns": [{"input": "Count words in hello world foo bar"}],
                    "assertions": ["Response contains 4"],
                },
                {
                    "scenario_id": "TC-03",
                    "turns": [{"input": "What can you help me with?"}],
                    "assertions": ["Response mentions tools or capabilities"],
                },
            ]
        }
    },
)
dataset_id = ds["datasetId"]
print(f"Dataset created: {dataset_id}")

# Step 2: Publish version
print("Publishing version 1...")
client.create_dataset_version_and_wait(datasetId=dataset_id)
print("Version 1 published")

# Step 3: Run evaluation
print("\nRunning dataset evaluation...")
eval_client = Evaluation()
results = eval_client.run_dataset(
    agent_id=AGENT_ID,
    dataset_id=dataset_id,
    dataset_version=1,
    evaluators=["Builtin.Helpfulness", "Builtin.GoalSuccessRate"],
)

print("\n=== Results ===")
for r in results:
    print(f"\nScenario : {r.scenario_id}")
    print(f"  Score  : {r.value:.2f}")
    print(f"  Label  : {r.label}")

# Uncomment to delete dataset after testing:
# client.delete_dataset_and_wait(datasetId=dataset_id)
# print("Dataset deleted")
