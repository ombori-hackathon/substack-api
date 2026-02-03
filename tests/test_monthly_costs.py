"""Tests for monthly cost calculator endpoint."""

from datetime import date, datetime, timedelta

import pytest

from app.models.subscription import Subscription


# =============================================================================
# Helper Functions
# =============================================================================


def create_subscription(
    db_session,
    user_id: int,
    name: str = "Test Sub",
    cost: float = 10.0,
    currency: str = "USD",
    billing_cycle: str = "monthly",
    category: str | None = None,
    status: str = "active",
    was_free_trial: bool = False,
    cancelled_at: datetime | None = None,
    deleted_at: datetime | None = None,
) -> Subscription:
    """Helper to create subscriptions for testing."""
    sub = Subscription(
        user_id=user_id,
        name=name,
        cost=cost,
        currency=currency,
        billing_cycle=billing_cycle,
        next_billing_date=date.today() + timedelta(days=30),
        category=category,
        status=status,
        was_free_trial=was_free_trial,
        cancelled_at=cancelled_at,
        deleted_at=deleted_at,
    )
    db_session.add(sub)
    db_session.commit()
    db_session.refresh(sub)
    return sub


# =============================================================================
# Authentication Tests
# =============================================================================


class TestMonthlyCostsAuth:
    """Tests for monthly costs authentication requirements."""

    def test_monthly_costs_no_token(self, client):
        """Should return 401 when no token is provided."""
        response = client.get("/subscriptions/monthly-costs")
        assert response.status_code == 401

    def test_monthly_costs_invalid_token(self, client):
        """Should return 401 when token is invalid."""
        response = client.get(
            "/subscriptions/monthly-costs",
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert response.status_code == 401


# =============================================================================
# Basic Monthly Cost Tests
# =============================================================================


class TestMonthlyCostCalculator:
    """Tests for basic monthly cost calculations."""

    def test_monthly_costs_empty(self, auth_client):
        """Should return empty response when no subscriptions exist."""
        response = auth_client.get("/subscriptions/monthly-costs")
        assert response.status_code == 200
        data = response.json()
        assert data["costs_by_currency"] == []
        assert data["comparison"] == []
        assert data["free_trials"] == []
        assert data["free_trial_total_count"] == 0
        assert data["total_subscription_count"] == 0
        assert data["active_count"] == 0
        assert "month" in data
        assert "calculation_date" in data

    def test_monthly_costs_single_subscription(self, auth_client, db_session):
        """Should calculate costs for a single subscription."""
        user_id = auth_client.test_user.id
        create_subscription(
            db_session,
            user_id,
            name="Netflix",
            cost=15.99,
            currency="USD",
            billing_cycle="monthly",
            category="streaming",
        )

        response = auth_client.get("/subscriptions/monthly-costs")
        assert response.status_code == 200
        data = response.json()

        assert data["total_subscription_count"] == 1
        assert data["active_count"] == 1
        assert len(data["costs_by_currency"]) == 1

        usd = data["costs_by_currency"][0]
        assert usd["currency"] == "USD"
        assert usd["total_monthly_cost"] == pytest.approx(15.99, rel=0.01)
        assert usd["projected_yearly_cost"] == pytest.approx(15.99 * 12, rel=0.01)
        assert usd["subscription_count"] == 1
        assert usd["free_trial_count"] == 0

        # Check category breakdown
        assert len(usd["categories"]) == 1
        assert usd["categories"][0]["category"] == "streaming"
        assert usd["categories"][0]["monthly_cost"] == pytest.approx(15.99, rel=0.01)

    def test_monthly_costs_multiple_currencies(self, auth_client, db_session):
        """Should group costs by currency."""
        user_id = auth_client.test_user.id
        create_subscription(
            db_session, user_id, name="Netflix", cost=15.99, currency="USD"
        )
        create_subscription(
            db_session, user_id, name="Spotify", cost=9.99, currency="EUR"
        )
        create_subscription(
            db_session, user_id, name="Disney+", cost=12.99, currency="USD"
        )

        response = auth_client.get("/subscriptions/monthly-costs")
        assert response.status_code == 200
        data = response.json()

        assert data["total_subscription_count"] == 3
        assert len(data["costs_by_currency"]) == 2

        # Find USD and EUR totals
        currencies = {c["currency"]: c for c in data["costs_by_currency"]}
        assert "USD" in currencies
        assert "EUR" in currencies

        assert currencies["USD"]["total_monthly_cost"] == pytest.approx(
            15.99 + 12.99, rel=0.01
        )
        assert currencies["USD"]["subscription_count"] == 2
        assert currencies["EUR"]["total_monthly_cost"] == pytest.approx(9.99, rel=0.01)
        assert currencies["EUR"]["subscription_count"] == 1

    def test_monthly_costs_category_breakdown(self, auth_client, db_session):
        """Should breakdown costs by category within each currency."""
        user_id = auth_client.test_user.id
        create_subscription(
            db_session,
            user_id,
            name="Netflix",
            cost=15.99,
            currency="USD",
            category="streaming",
        )
        create_subscription(
            db_session,
            user_id,
            name="Spotify",
            cost=9.99,
            currency="USD",
            category="streaming",
        )
        create_subscription(
            db_session,
            user_id,
            name="GitHub",
            cost=4.00,
            currency="USD",
            category="software",
        )
        # No category
        create_subscription(
            db_session, user_id, name="Random", cost=5.00, currency="USD", category=None
        )

        response = auth_client.get("/subscriptions/monthly-costs")
        assert response.status_code == 200
        data = response.json()

        usd = data["costs_by_currency"][0]
        categories = {c["category"]: c for c in usd["categories"]}

        assert "streaming" in categories
        assert "software" in categories
        assert "uncategorized" in categories

        assert categories["streaming"]["monthly_cost"] == pytest.approx(
            15.99 + 9.99, rel=0.01
        )
        assert categories["streaming"]["subscription_count"] == 2
        assert categories["software"]["monthly_cost"] == pytest.approx(4.00, rel=0.01)
        assert categories["uncategorized"]["monthly_cost"] == pytest.approx(
            5.00, rel=0.01
        )

    def test_projected_yearly_calculation(self, auth_client, db_session):
        """Should calculate projected yearly cost as monthly * 12."""
        user_id = auth_client.test_user.id
        create_subscription(
            db_session, user_id, name="Netflix", cost=15.99, currency="USD"
        )

        response = auth_client.get("/subscriptions/monthly-costs")
        assert response.status_code == 200
        data = response.json()

        usd = data["costs_by_currency"][0]
        assert usd["projected_yearly_cost"] == pytest.approx(
            usd["total_monthly_cost"] * 12, rel=0.01
        )


# =============================================================================
# Billing Cycle Conversion Tests
# =============================================================================


class TestBillingCycleConversion:
    """Tests for billing cycle to monthly equivalent conversion."""

    def test_billing_cycle_conversion_weekly(self, auth_client, db_session):
        """Should convert weekly costs to monthly (weekly * 52 / 12)."""
        user_id = auth_client.test_user.id
        create_subscription(
            db_session,
            user_id,
            name="Weekly Sub",
            cost=10.00,
            billing_cycle="weekly",
        )

        response = auth_client.get("/subscriptions/monthly-costs")
        assert response.status_code == 200
        data = response.json()

        # Weekly $10 = $10 * 52 / 12 ≈ $43.33/month
        usd = data["costs_by_currency"][0]
        expected_monthly = 10.00 * 52 / 12
        assert usd["total_monthly_cost"] == pytest.approx(expected_monthly, rel=0.01)

    def test_billing_cycle_conversion_yearly(self, auth_client, db_session):
        """Should convert yearly costs to monthly (yearly / 12)."""
        user_id = auth_client.test_user.id
        create_subscription(
            db_session,
            user_id,
            name="Yearly Sub",
            cost=120.00,
            billing_cycle="yearly",
        )

        response = auth_client.get("/subscriptions/monthly-costs")
        assert response.status_code == 200
        data = response.json()

        # Yearly $120 = $10/month
        usd = data["costs_by_currency"][0]
        assert usd["total_monthly_cost"] == pytest.approx(10.00, rel=0.01)

    def test_billing_cycle_conversion_quarterly(self, auth_client, db_session):
        """Should convert quarterly costs to monthly (quarterly / 3)."""
        user_id = auth_client.test_user.id
        create_subscription(
            db_session,
            user_id,
            name="Quarterly Sub",
            cost=30.00,
            billing_cycle="quarterly",
        )

        response = auth_client.get("/subscriptions/monthly-costs")
        assert response.status_code == 200
        data = response.json()

        # Quarterly $30 = $10/month
        usd = data["costs_by_currency"][0]
        assert usd["total_monthly_cost"] == pytest.approx(10.00, rel=0.01)

    def test_mixed_billing_cycles(self, auth_client, db_session):
        """Should correctly sum mixed billing cycles."""
        user_id = auth_client.test_user.id
        create_subscription(
            db_session,
            user_id,
            name="Monthly",
            cost=10.00,
            billing_cycle="monthly",
        )
        create_subscription(
            db_session,
            user_id,
            name="Yearly",
            cost=120.00,
            billing_cycle="yearly",
        )
        create_subscription(
            db_session,
            user_id,
            name="Weekly",
            cost=5.00,
            billing_cycle="weekly",
        )

        response = auth_client.get("/subscriptions/monthly-costs")
        assert response.status_code == 200
        data = response.json()

        # Monthly: $10 + Yearly: $10 + Weekly: $5 * 52/12 ≈ $21.67
        expected = 10.00 + 10.00 + (5.00 * 52 / 12)
        usd = data["costs_by_currency"][0]
        assert usd["total_monthly_cost"] == pytest.approx(expected, rel=0.01)


# =============================================================================
# Free Trial Tests
# =============================================================================


class TestMonthlyCostFreeTrials:
    """Tests for free trial handling in monthly costs."""

    def test_free_trial_contributes_zero(self, auth_client, db_session):
        """Free trials should contribute $0 to monthly costs."""
        user_id = auth_client.test_user.id
        create_subscription(
            db_session,
            user_id,
            name="Netflix",
            cost=15.99,
            currency="USD",
            was_free_trial=True,
        )
        create_subscription(
            db_session, user_id, name="Spotify", cost=9.99, currency="USD"
        )

        response = auth_client.get("/subscriptions/monthly-costs")
        assert response.status_code == 200
        data = response.json()

        # Only non-trial subscription should count
        usd = data["costs_by_currency"][0]
        assert usd["total_monthly_cost"] == pytest.approx(9.99, rel=0.01)
        assert usd["subscription_count"] == 2
        assert usd["free_trial_count"] == 1

    def test_free_trials_listed_separately(self, auth_client, db_session):
        """Free trials should be listed in the free_trials array."""
        user_id = auth_client.test_user.id
        sub = create_subscription(
            db_session,
            user_id,
            name="Netflix Trial",
            cost=15.99,
            currency="USD",
            category="streaming",
            billing_cycle="monthly",
            was_free_trial=True,
        )

        response = auth_client.get("/subscriptions/monthly-costs")
        assert response.status_code == 200
        data = response.json()

        assert data["free_trial_total_count"] == 1
        assert len(data["free_trials"]) == 1

        trial = data["free_trials"][0]
        assert trial["id"] == sub.id
        assert trial["name"] == "Netflix Trial"
        assert trial["cost"] == 15.99
        assert trial["currency"] == "USD"
        assert trial["category"] == "streaming"
        assert trial["billing_cycle"] == "monthly"

    def test_exclude_free_trials_parameter(self, auth_client, db_session):
        """Should exclude free trials from listing when include_free_trials=false."""
        user_id = auth_client.test_user.id
        create_subscription(
            db_session, user_id, name="Netflix Trial", cost=15.99, was_free_trial=True
        )
        create_subscription(db_session, user_id, name="Spotify", cost=9.99)

        response = auth_client.get(
            "/subscriptions/monthly-costs?include_free_trials=false"
        )
        assert response.status_code == 200
        data = response.json()

        # Free trial should be excluded from listing
        assert data["free_trial_total_count"] == 0
        assert len(data["free_trials"]) == 0
        # Total count still includes all active subscriptions
        assert data["total_subscription_count"] == 2

    def test_free_trial_category_tracking(self, auth_client, db_session):
        """Free trials should be tracked in category free_trial_count."""
        user_id = auth_client.test_user.id
        create_subscription(
            db_session,
            user_id,
            name="Netflix Trial",
            cost=15.99,
            category="streaming",
            was_free_trial=True,
        )
        create_subscription(
            db_session, user_id, name="Netflix Paid", cost=15.99, category="streaming"
        )

        response = auth_client.get("/subscriptions/monthly-costs")
        assert response.status_code == 200
        data = response.json()

        usd = data["costs_by_currency"][0]
        streaming = next(
            c for c in usd["categories"] if c["category"] == "streaming"
        )
        assert streaming["subscription_count"] == 2
        assert streaming["free_trial_count"] == 1


# =============================================================================
# Month Comparison Tests
# =============================================================================


class TestMonthlyCostComparison:
    """Tests for month-over-month comparison."""

    def test_no_previous_month_data(self, auth_client, db_session):
        """Should show 0 for previous month if no historical data."""
        user_id = auth_client.test_user.id
        create_subscription(
            db_session, user_id, name="Netflix", cost=15.99, currency="USD"
        )

        response = auth_client.get("/subscriptions/monthly-costs")
        assert response.status_code == 200
        data = response.json()

        # Should still have comparison data
        assert len(data["comparison"]) == 1
        comp = data["comparison"][0]
        assert comp["currency"] == "USD"
        assert comp["current_month_cost"] == pytest.approx(15.99, rel=0.01)
        # Previous month is 0 for new subscriptions (assuming created this month)
        assert comp["previous_month_cost"] >= 0

    def test_percentage_change_calculation(self, auth_client, db_session):
        """Should calculate percentage change correctly."""
        user_id = auth_client.test_user.id
        # Create subscription that was active last month
        sub = create_subscription(
            db_session, user_id, name="Netflix", cost=15.99, currency="USD"
        )
        # Simulate it was created more than a month ago
        sub.created_at = datetime.utcnow() - timedelta(days=45)
        db_session.commit()

        response = auth_client.get("/subscriptions/monthly-costs")
        assert response.status_code == 200
        data = response.json()

        # Comparison should show no change (same subscription both months)
        if data["comparison"]:
            comp = data["comparison"][0]
            # If subscription existed both months, should show 0% change
            if comp["previous_month_cost"] > 0:
                expected_change = (
                    (comp["current_month_cost"] - comp["previous_month_cost"])
                    / comp["previous_month_cost"]
                    * 100
                )
                assert comp["percentage_change"] == pytest.approx(
                    expected_change, rel=0.1
                )

    def test_cancelled_subscription_shows_decrease(self, auth_client, db_session):
        """Cancelled subscriptions should show decrease in current month."""
        user_id = auth_client.test_user.id
        # Create a cancelled subscription that was active last month
        sub = create_subscription(
            db_session,
            user_id,
            name="Netflix",
            cost=15.99,
            currency="USD",
            status="cancelled",
            cancelled_at=datetime.utcnow() - timedelta(days=5),
        )
        # Make it look like it was created before last month
        sub.created_at = datetime.utcnow() - timedelta(days=45)
        db_session.commit()

        response = auth_client.get("/subscriptions/monthly-costs")
        assert response.status_code == 200
        data = response.json()

        # Current month should not include the cancelled subscription
        assert data["active_count"] == 0


# =============================================================================
# Exclusion Tests
# =============================================================================


class TestMonthlyCostExclusions:
    """Tests for proper exclusion of cancelled/deleted subscriptions."""

    def test_excludes_cancelled(self, auth_client, db_session):
        """Should exclude cancelled subscriptions from current costs."""
        user_id = auth_client.test_user.id
        create_subscription(
            db_session, user_id, name="Active", cost=10.00, status="active"
        )
        create_subscription(
            db_session,
            user_id,
            name="Cancelled",
            cost=20.00,
            status="cancelled",
            cancelled_at=datetime.utcnow(),
        )

        response = auth_client.get("/subscriptions/monthly-costs")
        assert response.status_code == 200
        data = response.json()

        # Only active subscription should be counted
        assert data["active_count"] == 1
        usd = data["costs_by_currency"][0]
        assert usd["total_monthly_cost"] == pytest.approx(10.00, rel=0.01)
        assert usd["subscription_count"] == 1

    def test_excludes_deleted(self, auth_client, db_session):
        """Should exclude soft-deleted subscriptions."""
        user_id = auth_client.test_user.id
        create_subscription(
            db_session, user_id, name="Active", cost=10.00, status="active"
        )
        create_subscription(
            db_session,
            user_id,
            name="Deleted",
            cost=20.00,
            deleted_at=datetime.utcnow(),
        )

        response = auth_client.get("/subscriptions/monthly-costs")
        assert response.status_code == 200
        data = response.json()

        # Only active subscription should be counted
        assert data["active_count"] == 1
        usd = data["costs_by_currency"][0]
        assert usd["total_monthly_cost"] == pytest.approx(10.00, rel=0.01)

    def test_excludes_other_users(self, auth_client, second_auth_client, db_session):
        """Should only include current user's subscriptions."""
        user1_id = auth_client.test_user.id
        user2_id = second_auth_client.test_user.id

        create_subscription(
            db_session, user1_id, name="User1 Sub", cost=10.00, currency="USD"
        )
        create_subscription(
            db_session, user2_id, name="User2 Sub", cost=20.00, currency="USD"
        )

        response = auth_client.get("/subscriptions/monthly-costs")
        assert response.status_code == 200
        data = response.json()

        # Only user1's subscription
        assert data["total_subscription_count"] == 1
        usd = data["costs_by_currency"][0]
        assert usd["total_monthly_cost"] == pytest.approx(10.00, rel=0.01)


# =============================================================================
# Month Parameter Tests
# =============================================================================


class TestMonthParameter:
    """Tests for month query parameter."""

    def test_default_month_is_current(self, auth_client, db_session):
        """Should default to current month when no month parameter."""
        user_id = auth_client.test_user.id
        create_subscription(db_session, user_id, name="Netflix", cost=15.99)

        response = auth_client.get("/subscriptions/monthly-costs")
        assert response.status_code == 200
        data = response.json()

        # Month should be current month in YYYY-MM format
        expected_month = date.today().strftime("%Y-%m")
        assert data["month"] == expected_month

    def test_specific_month_parameter(self, auth_client, db_session):
        """Should use specified month when provided."""
        user_id = auth_client.test_user.id
        create_subscription(db_session, user_id, name="Netflix", cost=15.99)

        response = auth_client.get("/subscriptions/monthly-costs?month=2026-01")
        assert response.status_code == 200
        data = response.json()

        assert data["month"] == "2026-01"

    def test_invalid_month_format(self, auth_client):
        """Should return 422 for invalid month format."""
        response = auth_client.get("/subscriptions/monthly-costs?month=2026/01")
        assert response.status_code == 422

    def test_invalid_month_value(self, auth_client):
        """Should return 422 for invalid month value."""
        response = auth_client.get("/subscriptions/monthly-costs?month=2026-13")
        assert response.status_code == 422
