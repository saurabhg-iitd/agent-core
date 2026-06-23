"""
On-demand evaluation for a single AgentCore runtime session.

Usage:
    python scripts/run_ondemand_eval.py <runtime_session_uuid>

Example:
    agentcore invoke '{"prompt":"What is 10 plus 15?"}'
    # Session: <uuid>  ← use this UUID (not payload session_id)
    sleep 90
    python scripts/run_ondemand_eval.py <uuid>

Prerequisite:
    Agent must pass trace_attributes={"session.id": session_id} to Strands Agent (see main.py).
    aws/spans log group must exist — run scripts/setup_observability.py if missing.
"""
import os
import sys

import boto3
from bedrock_agentcore_starter_toolkit import Evaluation
from bedrock_agentcore_starter_toolkit.operations.observability.client import ObservabilityClient
from bedrock_agentcore_starter_toolkit.operations.constants import InstrumentationScopes

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


def diagnose_spans(session_id: str) -> None:
    """Print span counts to help debug empty eval results."""
    from datetime import datetime, timedelta

    obs = ObservabilityClient(region_name=REGION)
    end = datetime.now()
    start = end - timedelta(days=1)
    start_ms = int(start.timestamp() * 1000)
    end_ms = int(end.timestamp() * 1000)

    try:
        spans = obs.query_spans_by_session(session_id, start_ms, end_ms, AGENT_ID)
    except Exception as e:
        print(f"  Could not query spans: {e}")
        return

    print(f"  Total spans in aws/spans for session: {len(spans)}")

    strands_count = 0
    for span in spans:
        raw = span.raw_message or {}
        scope = raw.get("scope", {}) if isinstance(raw, dict) else {}
        scope_name = scope.get("name", "") if isinstance(scope, dict) else ""
        if scope_name == InstrumentationScopes.STRANDS:
            strands_count += 1
            print(f"  ✓ Found Strands span: {span.span_name or raw.get('name', '?')}")

    print(f"  Strands spans (strands.telemetry.tracer): {strands_count}")
    if strands_count == 0:
        print("\n  No Strands spans found — evaluation needs these.")
        print("  Fix: redeploy agent with trace_attributes in main.py, invoke again, wait 90s.")


def main():
    session_id = sys.argv[1] if len(sys.argv) > 1 else None
    if not session_id:
        print("Usage: python scripts/run_ondemand_eval.py <runtime_session_uuid>")
        print("Use the Session UUID from `agentcore invoke` output, not payload session_id.")
        sys.exit(1)

    if not spans_log_group_exists():
        print(f"ERROR: CloudWatch log group '{SPANS_LOG_GROUP}' does not exist in {REGION}.")
        print("Run: python scripts/setup_observability.py")
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
            print("Invoke the agent, wait 90s, use the NEW session UUID from invoke output.")
        diagnose_spans(session_id)
        raise

    successful = results.get_successful_results()
    failed = results.get_failed_results()

    print(f"\nSuccessful: {len(successful)}  |  Failed: {len(failed)}")

    if not successful and not failed:
        print("\nNo evaluation results — spans exist but none matched eval filters.")
        print("Diagnosing spans...")
        diagnose_spans(session_id)

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
