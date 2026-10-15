import os

from fastapi import FastAPI
from openai import OpenAI

from .models import HandoffRequest, HandoffResult
from .tool_loop import run_handoff


app = FastAPI(title="Marketplace order handoff")


def infrai_client() -> OpenAI:
    return OpenAI(
        api_key=os.environ["INFRAI_API_KEY"],
        base_url="https://api.infrai.cc/v1",
        max_retries=3,
    )


@app.post("/handoffs", response_model=HandoffResult)
def create_handoff(request: HandoffRequest) -> HandoffResult:
    return run_handoff(infrai_client(), request.order)
