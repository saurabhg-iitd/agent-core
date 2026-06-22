"""
Run from local Mac (needs iam:CreateRole permissions).
Creates the evaluation execution role and prints its ARN.
"""
import json
import boto3

REGION = "ap-south-1"
ACCOUNT_ID = "489284938287"
ROLE_NAME = "AgentCoreEvalsSDK-ap-south-1-wheelseyedemo"

iam = boto3.client("iam")

trust_policy = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {"Service": "bedrock.amazonaws.com"},
            "Action": "sts:AssumeRole",
            "Condition": {
                "StringEquals": {"aws:SourceAccount": ACCOUNT_ID},
                "ArnLike": {
                    "aws:SourceArn": f"arn:aws:bedrock-agentcore:{REGION}:{ACCOUNT_ID}:agent-runtime/*"
                },
            },
        }
    ],
}

inline_policy = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream",
            ],
            "Resource": "*",
        },
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents",
            ],
            "Resource": "*",
        },
        {
            "Effect": "Allow",
            "Action": [
                "bedrock-agentcore:GetAgentRuntimeInvocationRecord",
                "bedrock-agentcore:ListAgentRuntimeInvocationRecords",
            ],
            "Resource": f"arn:aws:bedrock-agentcore:{REGION}:{ACCOUNT_ID}:agent-runtime/*",
        },
    ],
}

# Create role
try:
    role = iam.create_role(
        RoleName=ROLE_NAME,
        AssumeRolePolicyDocument=json.dumps(trust_policy),
        Description="Evaluation execution role for wheelseyedemo AgentCore evaluations",
    )
    role_arn = role["Role"]["Arn"]
    print(f"Created role: {role_arn}")
except iam.exceptions.EntityAlreadyExistsException:
    role_arn = f"arn:aws:iam::{ACCOUNT_ID}:role/{ROLE_NAME}"
    print(f"Role already exists: {role_arn}")

# Attach inline policy
iam.put_role_policy(
    RoleName=ROLE_NAME,
    PolicyName="AgentCoreEvalPolicy",
    PolicyDocument=json.dumps(inline_policy),
)
print("Inline policy attached.")
print(f"\nRole ARN: {role_arn}")
print("\nPaste this ARN into scripts/setup_online_eval.py as EXECUTION_ROLE_ARN")
