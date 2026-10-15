import json

from marketplace_handoff.models import MarketplaceOrder, SellerAsset
from marketplace_handoff.service import infrai_client
from marketplace_handoff.tool_loop import run_handoff


order = MarketplaceOrder(
    order_id="order-1042",
    buyer_name="Mina",
    product_title="Launch trailer edit",
    seller_assets=[
        SellerAsset(name="trailer-master.mp4", status="ready"),
        SellerAsset(name="captions.srt", status="ready"),
    ],
)

result = run_handoff(infrai_client(), order)
print(json.dumps(result.model_dump(), indent=2))
