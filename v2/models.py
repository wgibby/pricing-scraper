"""
Pydantic data models for the v2 pricing extraction pipeline.

Defines the structured output schema that Claude returns via tool_use.
Also generates the JSON schema used as the `tools` parameter in API calls.
"""

from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class BillingPeriod(str, Enum):
    MONTHLY = "monthly"
    ANNUAL = "annual"
    WEEKLY = "weekly"
    QUARTERLY = "quarterly"


class TargetAudience(str, Enum):
    INDIVIDUAL = "individual"
    FAMILY = "family"
    STUDENT = "student"
    TEAM = "team"
    ENTERPRISE = "enterprise"


class Confidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class PricingPlan(BaseModel):
    plan_name: str = Field(
        description="Name of the plan as displayed on the page"
    )
    monthly_price: Optional[float] = Field(
        None,
        description="Monthly price. null if free tier or contact-sales only",
    )
    annual_price: Optional[float] = Field(
        None,
        description="Full annual price (e.g., 119.88 for a year). null if not offered",
    )
    annual_monthly_equivalent: Optional[float] = Field(
        None,
        description="Per-month price when billed annually (e.g., 9.99/mo billed annually). null if not shown",
    )
    billing_periods_available: list[BillingPeriod] = Field(
        description="Which billing periods are offered for this plan"
    )
    is_free_tier: bool = Field(
        description="True if this is a free/freemium plan"
    )
    is_contact_sales: bool = Field(
        description="True if pricing requires contacting sales"
    )
    target_audience: TargetAudience = Field(
        description="Who this plan is for"
    )
    key_features: list[str] = Field(
        description="Notable features listed for this plan (up to 10)"
    )
    notes: Optional[str] = Field(
        None,
        description="Any relevant notes (e.g., 'Up to 6 family members', 'First 3 months free')",
    )


class PricingExtraction(BaseModel):
    currency_code: str = Field(
        description="ISO 4217 currency code: USD, EUR, GBP, JPY, BRL, INR, etc."
    )
    currency_symbol: str = Field(
        description="Currency symbol as shown on page: $, €, £, ¥, R$, ₹, etc."
    )
    plans: list[PricingPlan] = Field(
        description="All pricing plans found on the page"
    )
    extraction_confidence: Confidence = Field(
        description="high=all data clear, medium=some ambiguity, low=significant uncertainty"
    )
    extraction_notes: Optional[str] = Field(
        None,
        description="Notes about extraction quality or issues encountered",
    )


# Claude tool schema — generated from the Pydantic model.
# Used as the `tools` parameter in Anthropic API calls with tool_choice
# forcing the model to return structured data matching this schema.
PRICING_EXTRACTION_TOOL = {
    "name": "extract_pricing_data",
    "description": (
        "Extract structured pricing data from a subscription/SaaS pricing page. "
        "Extract ALL plans shown on the page including free tiers and enterprise/contact-sales tiers."
    ),
    "input_schema": PricingExtraction.model_json_schema(),
}


if __name__ == "__main__":
    import json

    print("=== PricingExtraction JSON Schema ===")
    print(json.dumps(PricingExtraction.model_json_schema(), indent=2))
    print()
    print("=== Claude Tool Definition ===")
    print(json.dumps(PRICING_EXTRACTION_TOOL, indent=2))
