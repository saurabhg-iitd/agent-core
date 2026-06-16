import os
from strands.models import BedrockModel

MODEL_ID = "apac.anthropic.claude-sonnet-4-20250514-v1:0"

def load_model() -> BedrockModel:
    return BedrockModel(
        model_id=MODEL_ID,
        region_name=os.getenv("AWS_REGION", "ap-south-1"),
        streaming=True,
    )