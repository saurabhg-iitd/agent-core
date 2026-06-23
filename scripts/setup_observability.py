"""
One-time setup for AgentCore evaluation and GenAI observability.

Evaluation reads OpenTelemetry spans from the CloudWatch log group `aws/spans`.
That log group is created when X-Ray Transaction Search is enabled and traces
are routed to CloudWatch Logs.

Run from EC2 (needs logs:, xray:, and bedrock-agentcore: permissions):

    python scripts/setup_observability.py

Then:
  1. Wait 10-15 minutes for X-Ray trace destination to become ACTIVE
  2. Invoke the agent once: agentcore invoke '{"prompt":"What is 10 plus 15?"}'
  3. Wait ~60 seconds for spans to appear
  4. Run eval: python scripts/run_ondemand_eval.py <runtime-session-uuid>
"""
import os
import sys

import boto3
from botocore.exceptions import ClientError

from bedrock_agentcore_starter_toolkit.services.xray import (
    enable_traces_delivery_for_runtime,
    enable_transaction_search_if_needed,
)

REGION = os.getenv("AWS_REGION", "ap-south-1")
ACCOUNT_ID = os.getenv("AWS_ACCOUNT_ID", "489284938287")
AGENT_ID = os.getenv("AGENT_ID", "wheelseyedemo_Agent-L3yc137oAy")
AGENT_ARN = f"arn:aws:bedrock-agentcore:{REGION}:{ACCOUNT_ID}:runtime/{AGENT_ID}"
SPANS_LOG_GROUP = "aws/spans"

os.environ.setdefault("AWS_DEFAULT_REGION", REGION)


def check_spans_log_group(logs_client) -> bool:
    try:
        resp = logs_client.describe_log_groups(logGroupNamePrefix=SPANS_LOG_GROUP, limit=1)
        groups = [g["logGroupName"] for g in resp.get("logGroups", []) if g["logGroupName"] == SPANS_LOG_GROUP]
        return bool(groups)
    except ClientError as e:
        print(f"  Could not check log groups: {e}")
        return False


def check_xray_destination_status(xray_client) -> str:
    try:
        resp = xray_client.get_trace_segment_destination()
        return resp.get("Status", "UNKNOWN")
    except ClientError as e:
        return f"ERROR: {e}"


def main():
    print("=== AgentCore Observability Setup ===\n")
    print(f"Region : {REGION}")
    print(f"Agent  : {AGENT_ID}\n")

    logs_client = boto3.client("logs", region_name=REGION)
    xray_client = boto3.client("xray", region_name=REGION)

    print("Step 1: Enable X-Ray Transaction Search (routes traces → CloudWatch Logs / aws/spans)")
    tx_ok = enable_transaction_search_if_needed(REGION, ACCOUNT_ID)
    print(f"  Result: {'OK' if tx_ok else 'FAILED — check IAM (logs:PutResourcePolicy, xray:*)'}\n")

    print("Step 2: Enable traces delivery for AgentCore runtime")
    traces_result = enable_traces_delivery_for_runtime(
        agent_id=AGENT_ID,
        agent_arn=AGENT_ARN,
        region=REGION,
    )
    print(f"  Status: {traces_result.get('status', 'unknown')}")
    if traces_result.get("error"):
        print(f"  Error : {traces_result['error']}")
    print()

    print("Step 3: Verify aws/spans log group")
    if check_spans_log_group(logs_client):
        print(f"  ✓ Log group '{SPANS_LOG_GROUP}' exists")
    else:
        print(f"  ✗ Log group '{SPANS_LOG_GROUP}' not found yet")
        print("    It is created automatically after X-Ray destination becomes ACTIVE")
        print("    and the agent is invoked at least once.")

    dest_status = check_xray_destination_status(xray_client)
    print(f"\nStep 4: X-Ray trace segment destination status: {dest_status}")
    if dest_status == "PENDING":
        print("  ⏳ Wait 10-15 minutes, then invoke the agent and retry eval.")
    elif dest_status == "ACTIVE":
        print("  ✓ Ready — invoke the agent, wait ~60s, then run on-demand eval.")

    print("\n=== Next steps ===")
    print("  agentcore invoke '{\"prompt\":\"What is 10 plus 15?\"}'")
    print("  # copy Session UUID from output, wait 60s")
    print("  python scripts/run_ondemand_eval.py <session-uuid>")
    print("\nOptional — online eval (shows in CloudWatch Evaluations tab):")
    print("  python scripts/setup_online_eval.py")

    if not tx_ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
