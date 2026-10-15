import json
from typing import Any

from openai import OpenAI

from .models import HandoffResult, MarketplaceOrder
from .order_tools import HandoffRuleError, OrderDesk


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "inspect_seller_assets",
            "description": "List ready and processing deliverables for this order.",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_buyer_update",
            "description": "Record a concise progress update for the buyer.",
            "parameters": {
                "type": "object",
                "properties": {"message": {"type": "string"}},
                "required": ["message"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "handoff_order",
            "description": "Complete handoff after every seller asset is ready and the buyer was updated.",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
]

SYSTEM_PROMPT = """You coordinate a creator marketplace order.
First inspect seller assets. If every asset is ready, send one useful buyer update and hand off the order.
If anything is processing, send one update that names what is pending and stop. Never invent asset state.
Finish with a short factual summary after the tools are done."""


def run_handoff(client: OpenAI, order: MarketplaceOrder, max_rounds: int = 6) -> HandoffResult:
    desk = OrderDesk(order)
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": order.model_dump_json()},
    ]

    for _ in range(max_rounds):
        response = client.chat.completions.create(
            model="auto",
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
        )
        message = response.choices[0].message
        messages.append(message.model_dump(exclude_none=True))
        if not message.tool_calls:
            return desk.result()

        for tool_call in message.tool_calls:
            arguments = json.loads(tool_call.function.arguments or "{}")
            try:
                output = desk.call(tool_call.function.name, arguments)
            except HandoffRuleError as exc:
                output = {"accepted": False, "reason": str(exc)}
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(output),
                }
            )

    raise RuntimeError("The tool loop exceeded its round budget.")
