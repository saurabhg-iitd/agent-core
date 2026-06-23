"""
On-demand evaluation for a single AgentCore runtime session.

Usage:
    python scripts/run_ondemand_eval.py <runtime_session_uuid>

Example:
    agentcore invoke '{"prompt":"What is 10 plus 15?"}'
    # Session: b99794a2-5de1-4579-9b61-e107341afbdc  ← use this UUID
    sleep 60
    python scripts/run_ondemand_eval.py b99794a2-5de1-4579-9b61-e107341afbdc

Prerequisite:
    aws/spans log group must exist. If eval fails with "Log group not found: aws/spans",
    run: python scripts/setup_observability.py
"""
import os
import sys

import boto3
from bedrock_agentcore_starter_toolkit import Evaluation

AGENT_ID = "wheelseyedemo_Agent-L3yc137oAy"
REGION = os.getenv("AWS_REGION", "ap-south-1")
SPANS_LOG_GROUP = "aws/spans"

os.environ.setdefault("AWS_DEFAULT_REGION", REGION)


def spans_log_group_exists() -> bool:
    logs = boto3.client("logs", region_name=REGION)
    try:
        resp = logs.describe_log_groups(logGroupNamePrefix=SPANS_LOG_GROUP, limit=1)
        return any(g["logGroupName"] == SPANS_LOG_GROUP for g in resp.get("logGroups", []))
    except Exception:
        return False


def main():
    session_id = sys.argv[1] if len(sys.argv) > 1 else None
    if not session_id:
        print("Usage: python scripts/run_ondemand_eval.py <runtime_session_uuid>")
        print("Use the Session UUID from `agentcore invoke` output, not payload session_id.")
        sys.exit(1)

    if not spans_log_group_exists():
        print(f"ERROR: CloudWatch log group '{SPANS_LOG_GROUP}' does not exist in {REGION}.")
        print("Evaluation requires OTEL spans in aws/spans.")
        print("\nFix:")
        print("  python scripts/setup_observability.py")
        print("  # wait 10-15 min for X-Ray destination ACTIVE, invoke agent, wait 60s, retry")
        sys.exit(1)

    eval_client = Evaluation(region=REGION)

    print(f"Evaluating session: {session_id}")
    print(f"Agent: {AGENT_ID}  Region: {REGION}\n")

    try:
        results = eval_client.run(
            agent_id=AGENT_ID,
            session_id=session_id,
            evaluators=["Builtin.Helpfulness", "Builtin.GoalSuccessRate"],
        )
    except Exception as e:
        if "No spans found" in str(e):
            print(f"\nNo spans found for session {session_id}.")
            print("Try:")
            print("  1. Invoke the agent again and use the NEW session UUID")
            print("  2. Wait 60-90 seconds after invoke before running eval")
            print("  3. Confirm X-Ray destination is ACTIVE:")
            print("       aws xray get-trace-segment-destination --region ap-south-1")
        raise

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


if __name__ == "__main__":
    main()
