from typing import Literal

from pydantic import BaseModel, Field


class SellerAsset(BaseModel):
    name: str
    status: Literal["ready", "processing"]


class MarketplaceOrder(BaseModel):
    order_id: str = Field(min_length=1)
    buyer_name: str = Field(min_length=1)
    product_title: str = Field(min_length=1)
    seller_assets: list[SellerAsset] = Field(min_length=1)


class HandoffRequest(BaseModel):
    order: MarketplaceOrder


class HandoffResult(BaseModel):
    order_id: str
    status: Literal["handed_off", "needs_seller_assets"]
    buyer_updates: list[str]
    asset_names: list[str]
