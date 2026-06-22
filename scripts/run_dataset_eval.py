"""
Dataset evaluation — invokes agent for each test scenario and scores results.
"""
import subprocess
import json
import time
import os
from bedrock_agentcore_starter_toolkit import Evaluation

AGENT_ID = "wheelseyedemo_Agent-L3yc137oAy"
os.environ.setdefault("AWS_DEFAULT_REGION", "ap-south-1")

TEST_CASES = [
    {
        "scenario_id": "TC-01",
        "prompt": "Add 5 and 3",
        "session_id": "dataset-eval-tc01",
        "actor_id": "eval-user",
        "reference": "The answer should be 8",
    },
    {
        "scenario_id": "TC-02",
        "prompt": "Count words in hello world foo bar",
        "session_id": "dataset-eval-tc02",
        "actor_id": "eval-user",
        "reference": "The answer should be 4",
    },
    {
        "scenario_id": "TC-03",
        "prompt": "What can you help me with?",
        "session_id": "dataset-eval-tc03",
        "actor_id": "eval-user",
        "reference": "Response should mention tools or capabilities",
    },
]

def invoke_agent(tc):
    payload = json.dumps({
        "prompt": tc["prompt"],
        "session_id": tc["session_id"],
        "actor_id": tc["actor_id"],
    })
    result = subprocess.run(
        ["agentcore", "invoke", payload],
        capture_output=True, text=True
    )
    return result.stdout.strip()

eval_client = Evaluation()

print("=== Dataset Evaluation ===\n")

for tc in TEST_CASES:
    print(f"[{tc['scenario_id']}] Invoking: {tc['prompt']}")
    response = invoke_agent(tc)
    print(f"  Response: {response[:100]}")

print("\nWaiting 30s for spans to propagate...")
time.sleep(30)

print("\n=== Scoring ===\n")

for tc in TEST_CASES:
    print(f"[{tc['scenario_id']}] Evaluating session: {tc['session_id']}")
    try:
        results = eval_client.run(
            agent_id=AGENT_ID,
            session_id=tc["session_id"],
            evaluators=["Builtin.Helpfulness", "Builtin.GoalSuccessRate"],
        )
        successful = results.get_successful_results()
        for r in successful:
            print(f"  {r.evaluator_name}: {r.value:.2f} ({r.label})")
        if not successful:
            print("  No results yet (spans may need more time)")
    except Exception as e:
        print(f"  Error: {e}")
    print()
