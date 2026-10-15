from dataclasses import dataclass, field
from typing import Any

from .models import HandoffResult, MarketplaceOrder


class HandoffRuleError(ValueError):
    """Raised when a tool requests an invalid marketplace state transition."""


@dataclass
class OrderDesk:
    order: MarketplaceOrder
    buyer_updates: list[str] = field(default_factory=list)
    handed_off: bool = False

    def inspect_seller_assets(self) -> dict[str, Any]:
        ready = [asset.name for asset in self.order.seller_assets if asset.status == "ready"]
        pending = [asset.name for asset in self.order.seller_assets if asset.status == "processing"]
        return {"ready": ready, "processing": pending, "all_ready": not pending}

    def send_buyer_update(self, message: str) -> dict[str, Any]:
        clean_message = message.strip()
        if clean_message and clean_message not in self.buyer_updates:
            self.buyer_updates.append(clean_message)
        return {"sent": True, "message": clean_message}

    def handoff_order(self) -> dict[str, Any]:
        assets = self.inspect_seller_assets()
        if not assets["all_ready"]:
            raise HandoffRuleError("Seller assets must all be ready before handoff.")
        if not self.buyer_updates:
            raise HandoffRuleError("Send the buyer an update before handoff.")
        self.handed_off = True
        return {"handed_off": True, "order_id": self.order.order_id}

    def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if name == "inspect_seller_assets":
            return self.inspect_seller_assets()
        if name == "send_buyer_update":
            return self.send_buyer_update(message=str(arguments["message"]))
        if name == "handoff_order":
            return self.handoff_order()
        raise ValueError(f"Unknown local tool: {name}")

    def result(self) -> HandoffResult:
        assets = self.inspect_seller_assets()
        return HandoffResult(
            order_id=self.order.order_id,
            status="handed_off" if self.handed_off else "needs_seller_assets",
            buyer_updates=self.buyer_updates,
            asset_names=assets["ready"],
        )
