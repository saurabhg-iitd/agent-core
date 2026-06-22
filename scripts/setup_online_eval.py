from bedrock_agentcore_starter_toolkit import Evaluation

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
    auto_create_execution_role=True,
    enable_on_create=True,
)

print(f"Config ID: {config['onlineEvaluationConfigId']}")
print(f"Status:    {config['status']}")
print("\nManage with:")
print("  agentcore pause online-eval wheelseyedemo_online_eval")
print("  agentcore resume online-eval wheelseyedemo_online_eval")
