"""
On-demand evaluation for a single AgentCore runtime session.

Usage:
    python scripts/run_ondemand_eval.py <runtime_session_uuid> [--wait SECONDS]

Example:
    agentcore invoke '{"prompt":"What is 10 plus 15?"}'
    # Session: <uuid>  ← use this UUID (not payload session_id)
    python scripts/run_ondemand_eval.py <uuid> --wait 300

Prerequisite:
    Agent must pass trace_attributes={"session.id": session_id} to Strands Agent (see main.py).
    aws/spans log group must exist — run scripts/setup_observability.py if missing.
"""
import argparse
import os
import sys
import time

import boto3
from bedrock_agentcore_starter_toolkit import Evaluation
from bedrock_agentcore_starter_toolkit.operations.observability.client import ObservabilityClient
from bedrock_agentcore_starter_toolkit.operations.constants import InstrumentationScopes

AGENT_ID = "wheelseyedemo_Agent-L3yc137oAy"
REGION = os.getenv("AWS_REGION", "ap-south-1")
SPANS_LOG_GROUP = "aws/spans"
RUNTIME_LOG_GROUP = f"/aws/bedrock-agentcore/runtimes/{AGENT_ID}-DEFAULT"

os.environ.setdefault("AWS_DEFAULT_REGION", REGION)


def spans_log_group_exists() -> bool:
    logs = boto3.client("logs", region_name=REGION)
    try:
        resp = logs.describe_log_groups(logGroupNamePrefix=SPANS_LOG_GROUP, limit=1)
        return any(g["logGroupName"] == SPANS_LOG_GROUP for g in resp.get("logGroups", []))
    except Exception:
        return False


def _run_insights_query(logs_client, log_group: str, query: str, start_ms: int, end_ms: int) -> list:
    """Run a CloudWatch Logs Insights query and return raw result rows."""
    try:
        resp = logs_client.start_query(
            logGroupName=log_group,
            startTime=start_ms // 1000,
            endTime=end_ms // 1000,
            queryString=query,
        )
    except logs_client.exceptions.ResourceNotFoundException:
        return []

    query_id = resp["queryId"]
    for _ in range(60):
        result = logs_client.get_query_results(queryId=query_id)
        if result["status"] == "Complete":
            return result.get("results", [])
        if result["status"] in ("Failed", "Cancelled", "Timeout"):
            return []
        time.sleep(2)
    return []


def count_spans_for_session(session_id: str) -> tuple[int, int]:
    """Return (total_spans, strands_spans) for a session in aws/spans."""
    from datetime import datetime, timedelta

    obs = ObservabilityClient(region_name=REGION)
    end = datetime.now()
    start = end - timedelta(hours=2)
    start_ms = int(start.timestamp() * 1000)
    end_ms = int(end.timestamp() * 1000)

    try:
        spans = obs.query_spans_by_session(session_id, start_ms, end_ms, AGENT_ID)
    except Exception:
        return 0, 0

    strands = 0
    for span in spans:
        raw = span.raw_message or {}
        scope = raw.get("scope", {}) if isinstance(raw, dict) else {}
        scope_name = scope.get("name", "") if isinstance(scope, dict) else ""
        if scope_name == InstrumentationScopes.STRANDS:
            strands += 1
    return len(spans), strands


def wait_for_spans(session_id: str, max_wait: int) -> tuple[int, int]:
    """Poll until spans appear in aws/spans or timeout."""
    print(f"Waiting up to {max_wait}s for spans in aws/spans (indexing can take 2-5 min)...")
    deadline = time.time() + max_wait
    attempt = 0
    while time.time() < deadline:
        attempt += 1
        total, strands = count_spans_for_session(session_id)
        if total > 0:
            print(f"  Found {total} span(s) ({strands} Strands) after ~{attempt * 15}s")
            return total, strands
        remaining = int(deadline - time.time())
        print(f"  [{attempt}] No spans yet — retrying in 15s ({remaining}s left)")
        time.sleep(15)
    return 0, 0


def diagnose_spans(session_id: str) -> None:
    """Print detailed span diagnostics."""
    from datetime import datetime, timedelta

    logs = boto3.client("logs", region_name=REGION)
    end = datetime.now()
    start = end - timedelta(hours=2)
    start_ms = int(start.timestamp() * 1000)
    end_ms = int(end.timestamp() * 1000)

    total, strands = count_spans_for_session(session_id)
    print(f"\n--- Span diagnostics for session {session_id} ---")
    print(f"  aws/spans (with agent filter): {total} total, {strands} Strands")

    # Broader query — session only, no agent_id parse filter
    broad_query = f"""fields @timestamp, traceId, name, `attributes.session.id`, `resource.attributes.cloud.resource_id`
| filter `attributes.session.id` = '{session_id}'
| sort @timestamp desc
| limit 10"""
    rows = _run_insights_query(logs, SPANS_LOG_GROUP, broad_query, start_ms, end_ms)
    print(f"  aws/spans (session only, no agent filter): {len(rows)} row(s)")
    for row in rows[:3]:
        fields = {f["field"]: f.get("value") for f in row}
        print(f"    - {fields.get('name', '?')} trace={fields.get('traceId', '?')[:16]}...")

    # Check otel-rt-logs stream on runtime log group
    otel_query = f"""fields @timestamp, traceId, name
| filter `attributes.session.id` = '{session_id}'
| sort @timestamp desc
| limit 5"""
    otel_rows = _run_insights_query(logs, RUNTIME_LOG_GROUP, otel_query, start_ms, end_ms)
    print(f"  runtime otel-rt-logs for session: {len(otel_rows)} row(s)")

    if total == 0 and len(rows) == 0:
        print("\n  Spans not indexed yet. Wait 2-5 minutes after invoke and retry.")
        print("  Deploy note says observability can take up to 10 minutes on first launch.")
    elif total == 0 and len(rows) > 0:
        print("\n  Spans exist but agent_id filter may be excluding them.")
        print("  Try: agentcore eval run -a", AGENT_ID, "-s", session_id)
    if strands == 0 and total > 0:
        print("\n  Platform spans found but no Strands spans.")
        print("  Verify main.py has trace_attributes={'session.id': session_id} and redeploy.")


def main():
    parser = argparse.ArgumentParser(description="Run on-demand AgentCore evaluation")
    parser.add_argument("session_id", help="Runtime session UUID from agentcore invoke output")
    parser.add_argument(
        "--wait",
        type=int,
        default=300,
        help="Seconds to poll for spans before eval (default: 300)",
    )
    parser.add_argument("--no-wait", action="store_true", help="Skip polling, run eval immediately")
    args = parser.parse_args()

    if not spans_log_group_exists():
        print(f"ERROR: CloudWatch log group '{SPANS_LOG_GROUP}' does not exist in {REGION}.")
        print("Run: python scripts/setup_observability.py")
        sys.exit(1)

    session_id = args.session_id
    eval_client = Evaluation(region=REGION)

    print(f"Evaluating session: {session_id}")
    print(f"Agent: {AGENT_ID}  Region: {REGION}\n")

    if not args.no_wait:
        total, strands = wait_for_spans(session_id, args.wait)
        if total == 0:
            diagnose_spans(session_id)
            print("\nERROR: No spans found after waiting. See diagnostics above.")
            sys.exit(1)
        if strands == 0:
            print("WARNING: No Strands spans yet — eval may return empty results.")

    try:
        results = eval_client.run(
            agent_id=AGENT_ID,
            session_id=session_id,
            evaluators=["Builtin.Helpfulness", "Builtin.GoalSuccessRate"],
        )
    except Exception as e:
        if "No spans found" in str(e):
            print(f"\nNo spans found for session {session_id} at eval time.")
        diagnose_spans(session_id)
        raise

    successful = results.get_successful_results()
    failed = results.get_failed_results()

    print(f"\nSuccessful: {len(successful)}  |  Failed: {len(failed)}")

    if not successful and not failed:
        print("\nNo evaluation results.")
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
