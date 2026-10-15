from types import SimpleNamespace

import pytest

from marketplace_handoff.models import MarketplaceOrder, SellerAsset
from marketplace_handoff.order_tools import HandoffRuleError, OrderDesk
from marketplace_handoff.tool_loop import run_handoff


def order_with(status: str = "ready") -> MarketplaceOrder:
    return MarketplaceOrder(
        order_id="order-1042",
        buyer_name="Mina",
        product_title="Launch trailer edit",
        seller_assets=[SellerAsset(name="trailer-master.mp4", status=status)],
    )


def test_handoff_requires_ready_assets_and_a_buyer_update() -> None:
    desk = OrderDesk(order_with("processing"))
    desk.send_buyer_update("The trailer is still rendering.")
    with pytest.raises(HandoffRuleError, match="must all be ready"):
        desk.handoff_order()

    ready_desk = OrderDesk(order_with())
    with pytest.raises(HandoffRuleError, match="buyer an update"):
        ready_desk.handoff_order()

    ready_desk.send_buyer_update("Your trailer and captions are ready.")
    assert ready_desk.handoff_order() == {"handed_off": True, "order_id": "order-1042"}


class FakeCompletions:
    def __init__(self) -> None:
        self.round = 0

    def create(self, **request: object) -> SimpleNamespace:
        self.round += 1
        calls = {
            1: [tool_call("call-1", "inspect_seller_assets", "{}")],
            2: [tool_call("call-2", "send_buyer_update", '{"message":"Your trailer is ready."}')],
            3: [tool_call("call-3", "handoff_order", "{}")],
            4: None,
        }[self.round]
        message = FakeMessage(calls)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class FakeMessage:
    def __init__(self, tool_calls: list[SimpleNamespace] | None) -> None:
        self.tool_calls = tool_calls

    def model_dump(self, exclude_none: bool = True) -> dict[str, object]:
        return {"role": "assistant", "tool_calls": self.tool_calls} if self.tool_calls else {"role": "assistant", "content": "Done"}


def tool_call(call_id: str, name: str, arguments: str) -> SimpleNamespace:
    return SimpleNamespace(id=call_id, function=SimpleNamespace(name=name, arguments=arguments))


def test_loop_executes_the_handoff_sequence() -> None:
    client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions()))
    result = run_handoff(client, order_with())  # type: ignore[arg-type]
    assert result.status == "handed_off"
    assert result.buyer_updates == ["Your trailer is ready."]
