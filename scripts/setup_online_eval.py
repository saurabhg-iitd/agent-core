import os
from bedrock_agentcore_starter_toolkit import Evaluation

os.environ.setdefault("AWS_DEFAULT_REGION", "ap-south-1")

EXECUTION_ROLE_ARN = "arn:aws:iam::489284938287:role/bedrock-read-access"

eval_client = Evaluation()

config = eval_client.create_online_config(
    config_name="wheelseyedemo_online_eval",
    agent_id="wheelseyedemo_Agent-L3yc137oAy",
    sampling_rate=1.0,
    evaluator_list=[
        "Builtin.GoalSuccessRate",
        "Builtin.Helpfulness",
        "Builtin.ToolSelectionAccuracy",
    ],
    config_description="Continuous evaluation of wheelseyedemo agent",
    execution_role_arn=EXECUTION_ROLE_ARN,
    enable_on_create=True,
)

print(f"Config ID: {config['onlineEvaluationConfigId']}")
print(f"Status:    {config['status']}")
print("\nManage with:")
print("  agentcore pause online-eval wheelseyedemo_online_eval")
print("  agentcore resume online-eval wheelseyedemo_online_eval")
