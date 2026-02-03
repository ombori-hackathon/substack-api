from collections import defaultdict
from datetime import date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import asc, desc
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import get_current_user
from app.models.subscription import Subscription, utc_now
from app.models.user import User
from app.models.reminder_log import ReminderLog
from app.schemas.subscription import (
    BillingCycle,
    CancellationRequest,
    CancellationResponse,
    Category,
    CategoryCost,
    CurrencyMonthlyCost,
    CurrencySavings,
    CurrencyTotal,
    EstimatedSavings,
    ForgottenSubscription,
    ForgottenSubscriptionsResponse,
    FreeTrialSubscription,
    MonthComparison,
    MonthlyCostResponse,
    MonthlySpendingPoint,
    RankedSubscription,
    ReactivateRequest,
    SavingsSuggestion,
    SavingsSuggestionsResponse,
    SavingsSummaryResponse,
    SortField,
    SortOrder,
    SpendingAnalyticsResponse,
    SpendingTrendResponse,
    SubscriptionCreate,
    SubscriptionListResponse,
    SubscriptionResponse,
    SubscriptionStatus,
    SubscriptionUpdate,
    TopSubscriptionsResponse,
    UpcomingSubscription,
    UpcomingSubscriptionListResponse,
)

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


@router.post("", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_subscription(
    subscription_data: SubscriptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new subscription for the authenticated user."""
    subscription = Subscription(
        user_id=current_user.id,
        name=subscription_data.name,
        cost=subscription_data.cost,
        currency=subscription_data.currency.value,
        billing_cycle=subscription_data.billing_cycle.value,
        next_billing_date=subscription_data.next_billing_date,
        category=subscription_data.category.value if subscription_data.category else None,
        category_id=subscription_data.category_id,
        reminder_days_before=subscription_data.reminder_days_before,
    )
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    return subscription


def _calculate_monthly_equivalent(cost: float, billing_cycle: str) -> float:
    """Convert cost to monthly equivalent based on billing cycle."""
    if billing_cycle == "weekly":
        return cost * 52 / 12  # ~4.33
    elif billing_cycle == "monthly":
        return cost
    elif billing_cycle == "quarterly":
        return cost / 3
    elif billing_cycle == "yearly":
        return cost / 12
    return cost


def _calculate_totals_by_currency(subscriptions: list[Subscription]) -> list[CurrencyTotal]:
    """Calculate totals and monthly equivalents grouped by currency."""
    totals: dict[str, dict[str, float]] = defaultdict(lambda: {"total": 0.0, "monthly_equivalent": 0.0})

    for sub in subscriptions:
        totals[sub.currency]["total"] += sub.cost
        totals[sub.currency]["monthly_equivalent"] += _calculate_monthly_equivalent(
            sub.cost, sub.billing_cycle
        )

    return [
        CurrencyTotal(
            currency=currency,
            total=round(data["total"], 2),
            monthly_equivalent=round(data["monthly_equivalent"], 2),
        )
        for currency, data in sorted(totals.items())
    ]


def _calculate_months_since(cancelled_at: datetime) -> int:
    """Calculate the number of complete months since cancellation."""
    if cancelled_at is None:
        return 0
    now = datetime.now(cancelled_at.tzinfo) if cancelled_at.tzinfo else datetime.now()
    diff = now - cancelled_at
    return max(0, int(diff.days / 30))


def _calculate_estimated_savings(subscription: Subscription) -> EstimatedSavings:
    """Calculate estimated savings for a cancelled subscription."""
    monthly_amount = _calculate_monthly_equivalent(subscription.cost, subscription.billing_cycle)
    months_since = _calculate_months_since(subscription.cancelled_at)
    total_saved = monthly_amount * months_since

    return EstimatedSavings(
        currency=subscription.currency,
        monthly_amount=round(monthly_amount, 2),
        total_saved=round(total_saved, 2),
        months_since_cancellation=months_since,
    )


@router.get("", response_model=SubscriptionListResponse)
async def list_subscriptions(
    sort_by: SortField = Query(default=SortField.NEXT_BILLING_DATE, description="Sort field"),
    order: SortOrder = Query(default=SortOrder.ASC, description="Sort order"),
    category: Optional[Category] = Query(default=None, description="Filter by category (deprecated)"),
    category_id: Optional[int] = Query(default=None, description="Filter by category ID"),
    subscription_status: Optional[str] = Query(
        default="active",
        alias="status",
        description="Filter by status: active, cancelled, or all",
    ),
    search: Optional[str] = Query(
        default=None,
        min_length=1,
        max_length=100,
        description="Case-insensitive partial match on subscription name",
    ),
    billing_cycle: Optional[BillingCycle] = Query(
        default=None,
        description="Filter by billing cycle: weekly, monthly, quarterly, yearly",
    ),
    cost_min: Optional[float] = Query(
        default=None,
        ge=0,
        description="Minimum cost (inclusive)",
    ),
    cost_max: Optional[float] = Query(
        default=None,
        ge=0,
        description="Maximum cost (inclusive)",
    ),
    limit: int = Query(default=50, ge=1, le=100, description="Page size (max 100)"),
    offset: int = Query(default=0, ge=0, description="Pagination offset"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all subscriptions for the authenticated user with sorting, filtering, and pagination."""
    # Base query - exclude soft-deleted subscriptions
    query = db.query(Subscription).filter(
        Subscription.user_id == current_user.id,
        Subscription.deleted_at.is_(None),
    )

    # Apply status filter
    if subscription_status and subscription_status != "all":
        query = query.filter(Subscription.status == subscription_status)

    # Apply search filter (case-insensitive partial match on name)
    if search:
        query = query.filter(Subscription.name.ilike(f"%{search}%"))

    # Apply billing cycle filter
    if billing_cycle:
        query = query.filter(Subscription.billing_cycle == billing_cycle.value)

    # Apply cost range filters
    if cost_min is not None:
        query = query.filter(Subscription.cost >= cost_min)
    if cost_max is not None:
        query = query.filter(Subscription.cost <= cost_max)

    # Apply category filter (prefer category_id over deprecated category string)
    if category_id is not None:
        query = query.filter(Subscription.category_id == category_id)
    elif category:
        query = query.filter(Subscription.category == category.value)

    # Get total count before pagination
    total_count = query.count()

    # Get all subscriptions for totals calculation (before pagination)
    all_subscriptions = query.all()

    # Apply sorting
    sort_column = getattr(Subscription, sort_by.value)
    if order == SortOrder.DESC:
        query = query.order_by(desc(sort_column))
    else:
        query = query.order_by(asc(sort_column))

    # Apply pagination
    subscriptions = query.offset(offset).limit(limit).all()

    # Calculate totals by currency
    totals_by_currency = _calculate_totals_by_currency(all_subscriptions)

    return SubscriptionListResponse(
        items=[SubscriptionResponse.model_validate(s) for s in subscriptions],
        total_count=total_count,
        offset=offset,
        limit=limit,
        totals_by_currency=totals_by_currency,
    )


@router.get("/upcoming", response_model=UpcomingSubscriptionListResponse)
async def get_upcoming_subscriptions(
    days: int = Query(default=7, ge=1, le=90, description="Days to look ahead"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get subscriptions renewing within the specified number of days."""
    today = date.today()
    end_date = today + __import__("datetime").timedelta(days=days)

    # Query active subscriptions with upcoming renewal
    subscriptions = (
        db.query(Subscription)
        .filter(
            Subscription.user_id == current_user.id,
            Subscription.status == "active",
            Subscription.deleted_at.is_(None),
            Subscription.next_billing_date >= today,
            Subscription.next_billing_date <= end_date,
        )
        .order_by(asc(Subscription.next_billing_date))
        .all()
    )

    # Check for existing reminders for each subscription
    upcoming_items = []
    for sub in subscriptions:
        days_until = (sub.next_billing_date - today).days

        # Check if reminder was already sent for this billing date
        existing_reminder = (
            db.query(ReminderLog)
            .filter(
                ReminderLog.subscription_id == sub.id,
                ReminderLog.scheduled_for == __import__("datetime").datetime.combine(
                    sub.next_billing_date, __import__("datetime").time.min
                ),
                ReminderLog.status == "sent",
            )
            .first()
        )

        upcoming_items.append(
            UpcomingSubscription(
                id=sub.id,
                name=sub.name,
                cost=sub.cost,
                currency=sub.currency,
                next_billing_date=sub.next_billing_date,
                days_until_renewal=days_until,
                reminder_sent=existing_reminder is not None,
            )
        )

    return UpcomingSubscriptionListResponse(
        items=upcoming_items,
        total_count=len(upcoming_items),
    )


@router.get("/savings", response_model=SavingsSummaryResponse)
async def get_savings_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get total savings from all cancelled subscriptions."""
    # Get all cancelled subscriptions (excluding free trials and deleted)
    cancelled_subscriptions = (
        db.query(Subscription)
        .filter(
            Subscription.user_id == current_user.id,
            Subscription.status == "cancelled",
            Subscription.was_free_trial == False,  # noqa: E712
            Subscription.deleted_at.is_(None),
        )
        .all()
    )

    # Group by currency and calculate savings
    savings_by_currency: dict[str, dict[str, float]] = defaultdict(
        lambda: {"monthly_amount": 0.0, "total_saved": 0.0, "months": 0.0, "count": 0}
    )

    for sub in cancelled_subscriptions:
        monthly = _calculate_monthly_equivalent(sub.cost, sub.billing_cycle)
        months = _calculate_months_since(sub.cancelled_at)
        total = monthly * months

        savings_by_currency[sub.currency]["monthly_amount"] += monthly
        savings_by_currency[sub.currency]["total_saved"] += total
        savings_by_currency[sub.currency]["months"] += months
        savings_by_currency[sub.currency]["count"] += 1

    savings_list = [
        CurrencySavings(
            currency=currency,
            monthly_amount=round(data["monthly_amount"], 2),
            total_saved=round(data["total_saved"], 2),
            months_since_cancellation=data["months"] / data["count"] if data["count"] > 0 else 0,
        )
        for currency, data in sorted(savings_by_currency.items())
    ]

    return SavingsSummaryResponse(
        savings_by_currency=savings_list,
        cancelled_count=len(cancelled_subscriptions),
    )


def _validate_month_format(month_str: str) -> tuple[int, int]:
    """Validate and parse YYYY-MM format string. Returns (year, month)."""
    import re

    if not re.match(r"^\d{4}-\d{2}$", month_str):
        raise HTTPException(
            status_code=422,
            detail="Invalid month format. Use YYYY-MM format.",
        )
    year, month = int(month_str[:4]), int(month_str[5:7])
    if month < 1 or month > 12:
        raise HTTPException(
            status_code=422,
            detail="Invalid month value. Month must be between 01 and 12.",
        )
    return year, month


def _get_month_range(year: int, month: int) -> tuple[date, date]:
    """Get the start and end dates for a given month."""
    from calendar import monthrange

    start_date = date(year, month, 1)
    _, last_day = monthrange(year, month)
    end_date = date(year, month, last_day)
    return start_date, end_date


def _was_active_in_month(
    subscription: Subscription, month_start: date, month_end: date
) -> bool:
    """Check if subscription was active during the given month."""
    # Must have been created before end of month
    created_date = subscription.created_at.date() if subscription.created_at else date.min
    if created_date > month_end:
        return False

    # Must not be soft-deleted
    if subscription.deleted_at is not None:
        deleted_date = subscription.deleted_at.date()
        if deleted_date < month_start:
            return False

    # If cancelled, check cancellation date
    if subscription.status == "cancelled" and subscription.cancelled_at:
        cancelled_date = subscription.cancelled_at.date()
        # Was active if cancelled during or after the month
        if cancelled_date < month_start:
            return False

    return True


def _calculate_monthly_costs_for_subscriptions(
    subscriptions: list[Subscription], include_free_trials: bool
) -> tuple[dict, list[FreeTrialSubscription], int]:
    """Calculate costs grouped by currency with category breakdown.

    Returns: (currency_data dict, free_trials list, free_trial_count)
    """
    currency_data: dict[str, dict] = defaultdict(
        lambda: {
            "total_monthly_cost": 0.0,
            "subscription_count": 0,
            "free_trial_count": 0,
            "categories": defaultdict(
                lambda: {"monthly_cost": 0.0, "subscription_count": 0, "free_trial_count": 0}
            ),
        }
    )

    free_trials: list[FreeTrialSubscription] = []
    free_trial_count = 0

    for sub in subscriptions:
        currency = sub.currency
        category = sub.category or "uncategorized"
        monthly_cost = _calculate_monthly_equivalent(sub.cost, sub.billing_cycle)

        currency_data[currency]["subscription_count"] += 1
        currency_data[currency]["categories"][category]["subscription_count"] += 1

        if sub.was_free_trial:
            free_trial_count += 1
            currency_data[currency]["free_trial_count"] += 1
            currency_data[currency]["categories"][category]["free_trial_count"] += 1

            if include_free_trials:
                free_trials.append(
                    FreeTrialSubscription(
                        id=sub.id,
                        name=sub.name,
                        cost=sub.cost,
                        currency=sub.currency,
                        category=sub.category,
                        billing_cycle=sub.billing_cycle,
                    )
                )
        else:
            # Only non-trial subscriptions contribute to cost
            currency_data[currency]["total_monthly_cost"] += monthly_cost
            currency_data[currency]["categories"][category]["monthly_cost"] += monthly_cost

    return currency_data, free_trials, free_trial_count


@router.get("/monthly-costs", response_model=MonthlyCostResponse)
async def get_monthly_costs(
    month: Optional[str] = Query(
        default=None,
        description="Month in YYYY-MM format. Defaults to current month.",
    ),
    include_free_trials: bool = Query(
        default=True,
        description="Whether to include free trials in the response.",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get monthly cost analytics with category breakdown and month-over-month comparison."""
    # Parse and validate month parameter
    if month is None:
        today = date.today()
        target_year, target_month = today.year, today.month
        month_str = today.strftime("%Y-%m")
    else:
        target_year, target_month = _validate_month_format(month)
        month_str = month

    # Get month ranges for current and previous month
    current_start, current_end = _get_month_range(target_year, target_month)

    # Calculate previous month
    if target_month == 1:
        prev_year, prev_month = target_year - 1, 12
    else:
        prev_year, prev_month = target_year, target_month - 1
    prev_start, prev_end = _get_month_range(prev_year, prev_month)

    # Query all non-deleted subscriptions for the user
    all_subscriptions = (
        db.query(Subscription)
        .filter(
            Subscription.user_id == current_user.id,
        )
        .all()
    )

    # Filter subscriptions active in current month (excluding cancelled and deleted)
    current_month_subs = [
        sub
        for sub in all_subscriptions
        if _was_active_in_month(sub, current_start, current_end)
        and sub.status == "active"
        and sub.deleted_at is None
    ]

    # Filter subscriptions that were active in previous month (including those cancelled since)
    prev_month_subs = [
        sub
        for sub in all_subscriptions
        if _was_active_in_month(sub, prev_start, prev_end) and sub.deleted_at is None
    ]

    # Calculate costs for current month
    currency_data, free_trials, free_trial_count = _calculate_monthly_costs_for_subscriptions(
        current_month_subs, include_free_trials
    )

    # Build costs_by_currency response
    costs_by_currency = []
    for currency, data in sorted(currency_data.items()):
        categories = [
            CategoryCost(
                category=cat,
                monthly_cost=round(cat_data["monthly_cost"], 2),
                subscription_count=cat_data["subscription_count"],
                free_trial_count=cat_data["free_trial_count"],
            )
            for cat, cat_data in sorted(data["categories"].items())
        ]

        costs_by_currency.append(
            CurrencyMonthlyCost(
                currency=currency,
                total_monthly_cost=round(data["total_monthly_cost"], 2),
                projected_yearly_cost=round(data["total_monthly_cost"] * 12, 2),
                subscription_count=data["subscription_count"],
                free_trial_count=data["free_trial_count"],
                categories=categories,
            )
        )

    # Calculate previous month costs for comparison
    prev_currency_data, _, _ = _calculate_monthly_costs_for_subscriptions(prev_month_subs, False)

    # Build comparison data
    all_currencies = set(currency_data.keys()) | set(prev_currency_data.keys())
    comparison = []
    for currency in sorted(all_currencies):
        current_cost = currency_data.get(currency, {}).get("total_monthly_cost", 0.0)
        prev_cost = prev_currency_data.get(currency, {}).get("total_monthly_cost", 0.0)
        difference = current_cost - prev_cost

        if prev_cost > 0:
            percentage_change = (difference / prev_cost) * 100
        else:
            percentage_change = None  # Can't calculate percentage from 0

        comparison.append(
            MonthComparison(
                currency=currency,
                current_month_cost=round(current_cost, 2),
                previous_month_cost=round(prev_cost, 2),
                difference=round(difference, 2),
                percentage_change=round(percentage_change, 2) if percentage_change is not None else None,
            )
        )

    # Calculate totals
    total_subscription_count = len(current_month_subs)
    active_count = sum(1 for sub in current_month_subs if not sub.was_free_trial)

    return MonthlyCostResponse(
        month=month_str,
        calculation_date=datetime.now(timezone.utc),
        costs_by_currency=costs_by_currency,
        comparison=comparison,
        free_trials=free_trials if include_free_trials else [],
        free_trial_total_count=free_trial_count if include_free_trials else 0,
        total_subscription_count=total_subscription_count,
        active_count=active_count,
    )


FORGOTTEN_THRESHOLD_DAYS = 30


def _get_spending_trends(
    subscriptions: list[Subscription], months: int = 6
) -> list[SpendingTrendResponse]:
    """Calculate spending trends for the last N months grouped by currency."""
    from calendar import monthrange

    today = date.today()
    trends_by_currency: dict[str, list[MonthlySpendingPoint]] = defaultdict(list)

    # Generate last N months
    for i in range(months - 1, -1, -1):
        # Calculate month offset
        target_month = today.month - i
        target_year = today.year
        while target_month <= 0:
            target_month += 12
            target_year -= 1

        month_str = f"{target_year:04d}-{target_month:02d}"
        _, last_day = monthrange(target_year, target_month)
        month_start = date(target_year, target_month, 1)
        month_end = date(target_year, target_month, last_day)

        # Group by currency for this month
        currency_costs: dict[str, dict] = defaultdict(
            lambda: {"total": 0.0, "count": 0}
        )

        for sub in subscriptions:
            if _was_active_in_month(sub, month_start, month_end):
                monthly_cost = _calculate_monthly_equivalent(sub.cost, sub.billing_cycle)
                currency_costs[sub.currency]["total"] += monthly_cost
                currency_costs[sub.currency]["count"] += 1

        # Add data points for each currency
        for currency, data in currency_costs.items():
            trends_by_currency[currency].append(
                MonthlySpendingPoint(
                    month=month_str,
                    total_monthly_cost=round(data["total"], 2),
                    subscription_count=data["count"],
                )
            )

    # Build response for each currency
    result = []
    for currency, data_points in sorted(trends_by_currency.items()):
        # Fill in missing months with zeros
        all_months = []
        for i in range(months - 1, -1, -1):
            target_month = today.month - i
            target_year = today.year
            while target_month <= 0:
                target_month += 12
                target_year -= 1
            all_months.append(f"{target_year:04d}-{target_month:02d}")

        # Create complete data points with zeros for missing months
        month_to_data = {dp.month: dp for dp in data_points}
        complete_data_points = []
        for month_str in all_months:
            if month_str in month_to_data:
                complete_data_points.append(month_to_data[month_str])
            else:
                complete_data_points.append(
                    MonthlySpendingPoint(
                        month=month_str,
                        total_monthly_cost=0.0,
                        subscription_count=0,
                    )
                )

        # Calculate average and trend
        costs = [dp.total_monthly_cost for dp in complete_data_points]
        avg_cost = sum(costs) / len(costs) if costs else 0

        # Determine trend direction based on first and last non-zero values
        non_zero_costs = [(i, c) for i, c in enumerate(costs) if c > 0]
        if len(non_zero_costs) >= 2:
            first_idx, first_cost = non_zero_costs[0]
            last_idx, last_cost = non_zero_costs[-1]
            if last_cost > first_cost * 1.05:  # 5% threshold
                trend_direction = "increasing"
                trend_percentage = ((last_cost - first_cost) / first_cost) * 100
            elif last_cost < first_cost * 0.95:
                trend_direction = "decreasing"
                trend_percentage = ((first_cost - last_cost) / first_cost) * -100
            else:
                trend_direction = "stable"
                trend_percentage = 0.0
        else:
            trend_direction = "stable"
            trend_percentage = None

        result.append(
            SpendingTrendResponse(
                currency=currency,
                data_points=complete_data_points,
                average_monthly_cost=round(avg_cost, 2),
                trend_direction=trend_direction,
                trend_percentage=round(trend_percentage, 2) if trend_percentage is not None else None,
            )
        )

    return result


def _get_top_subscriptions(
    subscriptions: list[Subscription], limit: int = 5
) -> list[TopSubscriptionsResponse]:
    """Get top N expensive subscriptions grouped by currency."""
    # Group active subscriptions by currency
    by_currency: dict[str, list[Subscription]] = defaultdict(list)
    for sub in subscriptions:
        if sub.status == "active" and sub.deleted_at is None:
            by_currency[sub.currency].append(sub)

    result = []
    for currency, subs in sorted(by_currency.items()):
        # Calculate monthly costs
        subs_with_cost = [
            (sub, _calculate_monthly_equivalent(sub.cost, sub.billing_cycle))
            for sub in subs
        ]
        # Sort by cost descending
        subs_with_cost.sort(key=lambda x: x[1], reverse=True)

        total_cost = sum(cost for _, cost in subs_with_cost)

        # Take top N
        top_subs = subs_with_cost[:limit]

        ranked = [
            RankedSubscription(
                id=sub.id,
                name=sub.name,
                monthly_cost=round(monthly_cost, 2),
                currency=sub.currency,
                percentage_of_total=round((monthly_cost / total_cost) * 100, 2) if total_cost > 0 else 0,
            )
            for sub, monthly_cost in top_subs
        ]

        result.append(
            TopSubscriptionsResponse(
                currency=currency,
                subscriptions=ranked,
                total_monthly_cost=round(total_cost, 2),
            )
        )

    return result


def _get_forgotten_subscriptions(
    subscriptions: list[Subscription], threshold_days: int = FORGOTTEN_THRESHOLD_DAYS
) -> ForgottenSubscriptionsResponse:
    """Get subscriptions not used in threshold_days or never used."""
    now = datetime.now(timezone.utc)
    forgotten = []
    waste_by_currency: dict[str, float] = defaultdict(float)

    for sub in subscriptions:
        if sub.status != "active" or sub.deleted_at is not None:
            continue

        is_forgotten = False
        days_since_used = None

        if sub.last_used_at is None:
            # Never used
            is_forgotten = True
        else:
            # Calculate days since last use
            last_used = sub.last_used_at
            if last_used.tzinfo is None:
                last_used = last_used.replace(tzinfo=timezone.utc)
            days_since_used = (now - last_used).days
            if days_since_used >= threshold_days:
                is_forgotten = True

        if is_forgotten:
            monthly_cost = _calculate_monthly_equivalent(sub.cost, sub.billing_cycle)
            forgotten.append(
                ForgottenSubscription(
                    id=sub.id,
                    name=sub.name,
                    monthly_cost=round(monthly_cost, 2),
                    currency=sub.currency,
                    last_used_at=sub.last_used_at,
                    days_since_used=days_since_used,
                )
            )
            waste_by_currency[sub.currency] += monthly_cost

    return ForgottenSubscriptionsResponse(
        subscriptions=forgotten,
        total_count=len(forgotten),
        total_monthly_waste={k: round(v, 2) for k, v in waste_by_currency.items()},
    )


def _get_savings_suggestions(
    subscriptions: list[Subscription],
) -> SavingsSuggestionsResponse:
    """Generate savings suggestions based on subscription analysis."""
    suggestions = []
    savings_by_currency: dict[str, float] = defaultdict(float)

    # Filter active subscriptions
    active_subs = [s for s in subscriptions if s.status == "active" and s.deleted_at is None]

    # Calculate totals by currency
    totals_by_currency: dict[str, float] = defaultdict(float)
    for sub in active_subs:
        monthly_cost = _calculate_monthly_equivalent(sub.cost, sub.billing_cycle)
        totals_by_currency[sub.currency] += monthly_cost

    # Track categories for duplicate detection
    categories_by_currency: dict[str, dict[str, list[Subscription]]] = defaultdict(
        lambda: defaultdict(list)
    )

    now = datetime.now(timezone.utc)

    for sub in active_subs:
        monthly_cost = _calculate_monthly_equivalent(sub.cost, sub.billing_cycle)

        # 1. Unused subscriptions (high confidence)
        is_unused = False
        if sub.last_used_at is None:
            is_unused = True
        else:
            last_used = sub.last_used_at
            if last_used.tzinfo is None:
                last_used = last_used.replace(tzinfo=timezone.utc)
            days_since = (now - last_used).days
            if days_since >= FORGOTTEN_THRESHOLD_DAYS:
                is_unused = True

        if is_unused:
            suggestions.append(
                SavingsSuggestion(
                    subscription_id=sub.id,
                    subscription_name=sub.name,
                    monthly_cost=round(monthly_cost, 2),
                    currency=sub.currency,
                    suggestion_type="unused",
                    reason=f"This subscription hasn't been used in over {FORGOTTEN_THRESHOLD_DAYS} days or was never marked as used.",
                    potential_monthly_savings=round(monthly_cost, 2),
                    confidence="high",
                )
            )
            savings_by_currency[sub.currency] += monthly_cost

        # Track category for duplicate detection
        if sub.category:
            categories_by_currency[sub.currency][sub.category].append(sub)

        # 3. High cost single subscription (>25% of total)
        currency_total = totals_by_currency[sub.currency]
        if currency_total > 0 and (monthly_cost / currency_total) > 0.25:
            # Don't add if already suggested as unused
            if not is_unused:
                suggestions.append(
                    SavingsSuggestion(
                        subscription_id=sub.id,
                        subscription_name=sub.name,
                        monthly_cost=round(monthly_cost, 2),
                        currency=sub.currency,
                        suggestion_type="high_cost",
                        reason=f"This subscription represents {round((monthly_cost / currency_total) * 100, 1)}% of your total {sub.currency} spending.",
                        potential_monthly_savings=round(monthly_cost, 2),
                        confidence="medium",
                    )
                )

    # 2. Duplicate categories (medium confidence)
    processed_categories = set()
    for currency, cats in categories_by_currency.items():
        for category, subs in cats.items():
            if len(subs) >= 2 and category not in processed_categories:
                processed_categories.add(category)
                # Suggest the cheapest one for potential cancellation
                subs_with_cost = [
                    (s, _calculate_monthly_equivalent(s.cost, s.billing_cycle))
                    for s in subs
                ]
                subs_with_cost.sort(key=lambda x: x[1])
                cheapest_sub, cheapest_cost = subs_with_cost[0]

                suggestions.append(
                    SavingsSuggestion(
                        subscription_id=cheapest_sub.id,
                        subscription_name=cheapest_sub.name,
                        monthly_cost=round(cheapest_cost, 2),
                        currency=cheapest_sub.currency,
                        suggestion_type="duplicate_category",
                        reason=f"You have {len(subs)} subscriptions in the '{category}' category. Consider consolidating.",
                        potential_monthly_savings=round(cheapest_cost, 2),
                        confidence="medium",
                    )
                )
                savings_by_currency[cheapest_sub.currency] += cheapest_cost

    return SavingsSuggestionsResponse(
        suggestions=suggestions,
        total_potential_savings={k: round(v, 2) for k, v in savings_by_currency.items()},
    )


@router.get("/analytics/trends", response_model=list[SpendingTrendResponse])
async def get_spending_trends(
    months: int = Query(default=6, ge=1, le=12, description="Number of months to analyze"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get 6-month spending trends by currency."""
    subscriptions = (
        db.query(Subscription)
        .filter(Subscription.user_id == current_user.id)
        .all()
    )

    return _get_spending_trends(subscriptions, months)


@router.get("/analytics/top", response_model=list[TopSubscriptionsResponse])
async def get_top_subscriptions(
    limit: int = Query(default=5, ge=1, le=20, description="Number of top subscriptions per currency"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get top N expensive subscriptions grouped by currency."""
    subscriptions = (
        db.query(Subscription)
        .filter(
            Subscription.user_id == current_user.id,
            Subscription.status == "active",
            Subscription.deleted_at.is_(None),
        )
        .all()
    )

    return _get_top_subscriptions(subscriptions, limit)


@router.get("/analytics/forgotten", response_model=ForgottenSubscriptionsResponse)
async def get_forgotten_subscriptions(
    threshold_days: int = Query(
        default=FORGOTTEN_THRESHOLD_DAYS,
        ge=1,
        le=365,
        description="Days since last use to consider forgotten",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get subscriptions not used in threshold_days or never used."""
    subscriptions = (
        db.query(Subscription)
        .filter(
            Subscription.user_id == current_user.id,
            Subscription.status == "active",
            Subscription.deleted_at.is_(None),
        )
        .all()
    )

    return _get_forgotten_subscriptions(subscriptions, threshold_days)


@router.get("/analytics/savings-suggestions", response_model=SavingsSuggestionsResponse)
async def get_savings_suggestions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get heuristic-based savings suggestions."""
    subscriptions = (
        db.query(Subscription)
        .filter(
            Subscription.user_id == current_user.id,
            Subscription.deleted_at.is_(None),
        )
        .all()
    )

    return _get_savings_suggestions(subscriptions)


@router.get("/analytics", response_model=SpendingAnalyticsResponse)
async def get_combined_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get combined spending analytics including trends, top subscriptions, forgotten subscriptions, and savings suggestions."""
    subscriptions = (
        db.query(Subscription)
        .filter(Subscription.user_id == current_user.id)
        .all()
    )

    # Active subscriptions for most endpoints
    active_subs = [s for s in subscriptions if s.status == "active" and s.deleted_at is None]

    return SpendingAnalyticsResponse(
        trends_by_currency=_get_spending_trends(subscriptions),
        top_subscriptions_by_currency=_get_top_subscriptions(active_subs),
        forgotten_subscriptions=_get_forgotten_subscriptions(active_subs),
        savings_suggestions=_get_savings_suggestions(subscriptions),
        generated_at=datetime.now(timezone.utc),
    )


@router.post("/{subscription_id}/mark-used", response_model=SubscriptionResponse)
async def mark_subscription_used(
    subscription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark a subscription as used (updates last_used_at to current time)."""
    subscription = (
        db.query(Subscription)
        .filter(
            Subscription.id == subscription_id,
            Subscription.user_id == current_user.id,
            Subscription.deleted_at.is_(None),
        )
        .first()
    )
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found",
        )

    subscription.last_used_at = utc_now()
    db.commit()
    db.refresh(subscription)
    return subscription


@router.get("/{subscription_id}", response_model=SubscriptionResponse)
async def get_subscription(
    subscription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single subscription by ID."""
    subscription = (
        db.query(Subscription)
        .filter(
            Subscription.id == subscription_id,
            Subscription.user_id == current_user.id,
            Subscription.deleted_at.is_(None),
        )
        .first()
    )
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found",
        )
    return subscription


@router.put("/{subscription_id}", response_model=SubscriptionResponse)
async def update_subscription(
    subscription_id: int,
    subscription_data: SubscriptionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    if_unmodified_since: Optional[str] = Header(None, alias="If-Unmodified-Since"),
):
    """Update a subscription.

    Supports optimistic locking via If-Unmodified-Since header.
    Pass the subscription's updated_at timestamp to detect concurrent edits.
    Returns 409 Conflict if the subscription was modified since the provided timestamp.
    """
    subscription = (
        db.query(Subscription)
        .filter(
            Subscription.id == subscription_id,
            Subscription.user_id == current_user.id,
            Subscription.deleted_at.is_(None),
        )
        .first()
    )
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found or was deleted",
        )

    # Check for concurrent modification if If-Unmodified-Since header is provided
    if if_unmodified_since:
        try:
            # Parse the timestamp - handle both with and without timezone
            client_timestamp = if_unmodified_since.replace("Z", "+00:00")
            if "+" not in client_timestamp and "-" not in client_timestamp[10:]:
                # No timezone info, assume UTC
                client_dt = datetime.fromisoformat(client_timestamp)
            else:
                client_dt = datetime.fromisoformat(client_timestamp)

            # Compare timestamps (truncate to seconds for comparison)
            server_dt = subscription.updated_at
            if server_dt is not None:
                # Normalize both to naive UTC for comparison
                if client_dt.tzinfo is not None:
                    client_dt = client_dt.replace(tzinfo=None)
                if server_dt.tzinfo is not None:
                    server_dt = server_dt.replace(tzinfo=None)

                # Check if server timestamp is newer than client's version
                if server_dt > client_dt:
                    current_updated_at = subscription.updated_at.isoformat()
                    if subscription.updated_at.tzinfo is None:
                        current_updated_at += "Z"
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Subscription was modified by another session",
                        headers={"X-Current-Updated-At": current_updated_at},
                    )
        except ValueError:
            # Invalid timestamp format, ignore and proceed
            pass

    update_data = subscription_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(value, "value"):  # Handle enums
            value = value.value
        setattr(subscription, field, value)

    db.commit()
    db.refresh(subscription)
    return subscription


@router.delete("/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subscription(
    subscription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Soft delete a subscription by setting deleted_at timestamp."""
    subscription = (
        db.query(Subscription)
        .filter(
            Subscription.id == subscription_id,
            Subscription.user_id == current_user.id,
            Subscription.deleted_at.is_(None),
        )
        .first()
    )
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found",
        )

    subscription.deleted_at = utc_now()
    db.commit()
    return None


@router.post("/{subscription_id}/restore", response_model=SubscriptionResponse)
async def restore_subscription(
    subscription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Restore a soft-deleted subscription."""
    subscription = (
        db.query(Subscription)
        .filter(
            Subscription.id == subscription_id,
            Subscription.user_id == current_user.id,
        )
        .first()
    )
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found",
        )

    if subscription.deleted_at is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Subscription is not deleted",
        )

    subscription.deleted_at = None
    db.commit()
    db.refresh(subscription)
    return subscription


@router.post("/{subscription_id}/cancel", response_model=CancellationResponse)
async def cancel_subscription(
    subscription_id: int,
    cancellation_request: Optional[CancellationRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cancel a subscription (mark as cancelled with the provider)."""
    subscription = (
        db.query(Subscription)
        .filter(
            Subscription.id == subscription_id,
            Subscription.user_id == current_user.id,
            Subscription.deleted_at.is_(None),
        )
        .first()
    )
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found",
        )

    if subscription.status == "cancelled":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Subscription is already cancelled",
        )

    # Update subscription status
    subscription.status = "cancelled"
    subscription.cancelled_at = utc_now()

    if cancellation_request:
        if cancellation_request.reason:
            subscription.cancellation_reason = cancellation_request.reason
        if cancellation_request.effective_date:
            subscription.cancellation_effective_date = cancellation_request.effective_date
        else:
            # Default effective date is next_billing_date
            subscription.cancellation_effective_date = subscription.next_billing_date
    else:
        subscription.cancellation_effective_date = subscription.next_billing_date

    db.commit()
    db.refresh(subscription)

    # Calculate estimated savings
    estimated_savings = _calculate_estimated_savings(subscription)

    # Build response
    response_data = SubscriptionResponse.model_validate(subscription).model_dump()
    response_data["estimated_savings"] = estimated_savings

    return CancellationResponse(**response_data)


@router.post("/{subscription_id}/reactivate", response_model=SubscriptionResponse)
async def reactivate_subscription(
    subscription_id: int,
    reactivate_request: Optional[ReactivateRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Reactivate a cancelled subscription."""
    subscription = (
        db.query(Subscription)
        .filter(
            Subscription.id == subscription_id,
            Subscription.user_id == current_user.id,
            Subscription.deleted_at.is_(None),
        )
        .first()
    )
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found",
        )

    if subscription.status != "cancelled":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Subscription is not cancelled",
        )

    # Clear cancellation fields
    subscription.status = "active"
    subscription.cancelled_at = None
    subscription.cancellation_reason = None
    subscription.cancellation_effective_date = None

    # Update billing date if provided
    if reactivate_request and reactivate_request.next_billing_date:
        subscription.next_billing_date = reactivate_request.next_billing_date

    db.commit()
    db.refresh(subscription)
    return subscription
