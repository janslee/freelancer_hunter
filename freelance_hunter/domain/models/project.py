from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class MoneyRange(BaseModel):
    currency: str = "USD"
    min_amount: float | None = None
    max_amount: float | None = None
    amount_type: str = "fixed"


class ClientProfile(BaseModel):
    client_id: str | None = None
    name: str | None = None
    country: str | None = None
    rating: float | None = None
    payment_verified: bool | None = None
    total_spent: float | None = None
    review_count: int | None = None


class Project(BaseModel):
    platform: str
    external_id: str
    url: str
    title: str
    description: str
    skills: list[str] = Field(default_factory=list)
    budget: MoneyRange
    bids_count: int | None = None
    posted_at: datetime | None = None
    deadline_at: datetime | None = None
    client: ClientProfile = Field(default_factory=ClientProfile)
    raw_payload: dict[str, Any] = Field(default_factory=dict)
