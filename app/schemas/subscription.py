from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class BillingCycle(str, Enum):
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    CANCELLED = "cancelled"


class SortField(str, Enum):
    NEXT_BILLING_DATE = "next_billing_date"
    NAME = "name"
    COST = "cost"
    CREATED_AT = "created_at"


class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"


class Currency(str, Enum):
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    CAD = "CAD"
    AUD = "AUD"
    JPY = "JPY"
    CHF = "CHF"
    SEK = "SEK"
    NOK = "NOK"
    DKK = "DKK"


class Category(str, Enum):
    STREAMING = "streaming"
    SOFTWARE = "software"
    UTILITIES = "utilities"
    GAMING = "gaming"
    OTHER = "other"


class SubscriptionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    cost: float = Field(..., gt=0)
    currency: Currency = Currency.USD
    billing_cycle: BillingCycle
    next_billing_date: date
    category: Optional[Category] = None  # Deprecated: use category_id
    category_id: Optional[int] = None
    reminder_days_before: int = Field(default=3, ge=0, le=30)

    @field_validator("next_billing_date")
    @classmethod
    def validate_billing_date(cls, v: date) -> date:
        if v < date.today():
            raise ValueError("Next billing date cannot be in the past")
        return v


class SubscriptionUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    cost: Optional[float] = Field(None, gt=0)
    currency: Optional[Currency] = None
    billing_cycle: Optional[BillingCycle] = None
    next_billing_date: Optional[date] = None
    category: Optional[Category] = None  # Deprecated: use category_id
    category_id: Optional[int] = None
    reminder_days_before: Optional[int] = Field(None, ge=0, le=30)

    @field_validator("next_billing_date")
    @classmethod
    def validate_billing_date(cls, v: date | None) -> date | None:
        if v is not None and v < date.today():
            raise ValueError("Next billing date cannot be in the past")
        return v


class SubscriptionResponse(BaseModel):
    id: int
    user_id: int
    name: str
    cost: float
    currency: str
    billing_cycle: str
    next_billing_date: date
    category: Optional[str]  # Deprecated: use category_id
    category_id: Optional[int] = None
    reminder_days_before: int
    created_at: datetime
    updated_at: datetime
    status: str = "active"
    cancelled_at: Optional[datetime] = None
    cancellation_reason: Optional[str] = None
    cancellation_effective_date: Optional[date] = None
    was_free_trial: bool = False
    last_used_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CurrencyTotal(BaseModel):
    currency: str
    total: float
    monthly_equivalent: float


class SubscriptionListResponse(BaseModel):
    items: list[SubscriptionResponse]
    total_count: int
    offset: int
    limit: int
    totals_by_currency: list[CurrencyTotal]


# Cancellation schemas
class CancellationRequest(BaseModel):
    reason: Optional[str] = Field(None, max_length=500)
    effective_date: Optional[date] = None


class ReactivateRequest(BaseModel):
    next_billing_date: Optional[date] = None

    @field_validator("next_billing_date")
    @classmethod
    def validate_billing_date(cls, v: date | None) -> date | None:
        if v is not None and v < date.today():
            raise ValueError("Next billing date cannot be in the past")
        return v


class EstimatedSavings(BaseModel):
    currency: str
    monthly_amount: float
    total_saved: float
    months_since_cancellation: int


class CancellationResponse(SubscriptionResponse):
    estimated_savings: Optional[EstimatedSavings] = None


class CurrencySavings(BaseModel):
    currency: str
    monthly_amount: float
    total_saved: float
    months_since_cancellation: float


class SavingsSummaryResponse(BaseModel):
    savings_by_currency: list[CurrencySavings]
    cancelled_count: int


# Upcoming subscriptions schemas
class UpcomingSubscription(BaseModel):
    id: int
    name: str
    cost: float
    currency: str
    next_billing_date: date
    days_until_renewal: int
    reminder_sent: bool

    class Config:
        from_attributes = True


class UpcomingSubscriptionListResponse(BaseModel):
    items: list[UpcomingSubscription]
    total_count: int


# Monthly Cost Calculator schemas
class CategoryCost(BaseModel):
    """Cost breakdown for a single category."""

    category: str  # "streaming", "software", etc. or "uncategorized"
    monthly_cost: float
    subscription_count: int
    free_trial_count: int


class CurrencyMonthlyCost(BaseModel):
    """Monthly cost summary for a single currency."""

    currency: str
    total_monthly_cost: float
    projected_yearly_cost: float  # monthly * 12
    subscription_count: int
    free_trial_count: int
    categories: list[CategoryCost]


class MonthComparison(BaseModel):
    """Month-over-month comparison for a currency."""

    currency: str
    current_month_cost: float
    previous_month_cost: float
    difference: float
    percentage_change: Optional[float]  # None if previous month was 0


class FreeTrialSubscription(BaseModel):
    """Free trial subscription details."""

    id: int
    name: str
    cost: float  # The would-be cost after trial
    currency: str
    category: Optional[str]
    billing_cycle: str


class MonthlyCostResponse(BaseModel):
    """Complete monthly cost analytics response."""

    month: str  # "2026-02"
    calculation_date: datetime
    costs_by_currency: list[CurrencyMonthlyCost]
    comparison: list[MonthComparison]
    free_trials: list[FreeTrialSubscription]
    free_trial_total_count: int
    total_subscription_count: int
    active_count: int


# Spending Analytics schemas
class MonthlySpendingPoint(BaseModel):
    """A single data point in the spending trend."""

    month: str  # "YYYY-MM"
    total_monthly_cost: float
    subscription_count: int


class SpendingTrendResponse(BaseModel):
    """6-month spending trend for a single currency."""

    currency: str
    data_points: list[MonthlySpendingPoint]
    average_monthly_cost: float
    trend_direction: str  # "increasing", "decreasing", "stable"
    trend_percentage: Optional[float]  # None if not enough data


class ForgottenSubscription(BaseModel):
    """A subscription that hasn't been used recently."""

    id: int
    name: str
    monthly_cost: float
    currency: str
    last_used_at: Optional[datetime]
    days_since_used: Optional[int]  # None if never used


class ForgottenSubscriptionsResponse(BaseModel):
    """Response for forgotten subscriptions endpoint."""

    subscriptions: list[ForgottenSubscription]
    total_count: int
    total_monthly_waste: dict[str, float]  # currency -> amount


class RankedSubscription(BaseModel):
    """A subscription ranked by cost."""

    id: int
    name: str
    monthly_cost: float
    currency: str
    percentage_of_total: float


class TopSubscriptionsResponse(BaseModel):
    """Top expensive subscriptions for a single currency."""

    currency: str
    subscriptions: list[RankedSubscription]
    total_monthly_cost: float


class SavingsSuggestion(BaseModel):
    """A suggestion for potential savings."""

    subscription_id: int
    subscription_name: str
    monthly_cost: float
    currency: str
    suggestion_type: str  # "unused", "duplicate_category", "high_cost"
    reason: str
    potential_monthly_savings: float
    confidence: str  # "high", "medium", "low"


class SavingsSuggestionsResponse(BaseModel):
    """Response for savings suggestions endpoint."""

    suggestions: list[SavingsSuggestion]
    total_potential_savings: dict[str, float]  # currency -> amount


class SpendingAnalyticsResponse(BaseModel):
    """Combined analytics response."""

    trends_by_currency: list[SpendingTrendResponse]
    top_subscriptions_by_currency: list[TopSubscriptionsResponse]
    forgotten_subscriptions: ForgottenSubscriptionsResponse
    savings_suggestions: SavingsSuggestionsResponse
    generated_at: datetime
