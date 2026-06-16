import os
from strands.models import BedrockModel

MODEL_ID = "global.anthropic.claude-sonnet-4-6"

def load_model() -> BedrockModel:
    return BedrockModel(
        model_id=MODEL_ID,
        region_name=os.getenv("AWS_REGION", "ap-south-1"),
        streaming=True,
    )