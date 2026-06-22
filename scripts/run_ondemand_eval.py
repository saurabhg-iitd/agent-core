"""
Usage: python scripts/run_ondemand_eval.py <session_id>
Example: python scripts/run_ondemand_eval.py sess-1
"""
import sys
from bedrock_agentcore_starter_toolkit import Evaluation

eval_client = Evaluation()

session_id = sys.argv[1] if len(sys.argv) > 1 else "sess-1"

print(f"Evaluating session: {session_id} ...")

results = eval_client.run(
    agent_id="wheelseyedemo_Agent-L3yc137oAy",
    session_id=session_id,
    evaluators=["Builtin.Helpfulness", "Builtin.GoalSuccessRate"],
)

successful = results.get_successful_results()
failed = results.get_failed_results()

print(f"\nSuccessful: {len(successful)}  |  Failed: {len(failed)}")

for result in successful:
    print(f"\n  Evaluator : {result.evaluator_name}")
    print(f"  Score     : {result.value:.2f}")
    print(f"  Label     : {result.label}")
    if result.explanation:
        print(f"  Reason    : {result.explanation[:200]}")

for result in failed:
    print(f"\n  [FAILED] {result.evaluator_name}: {result.error_message}")
