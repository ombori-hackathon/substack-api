"""Tests for spending analytics endpoints."""

from datetime import date, datetime, timedelta, timezone

import pytest


class TestMarkUsed:
    """Tests for POST /subscriptions/{id}/mark-used endpoint."""

    def test_mark_used_updates_timestamp(self, auth_client):
        """Marking subscription as used should update last_used_at."""
        # Create subscription
        response = auth_client.post(
            "/subscriptions",
            json={
                "name": "Netflix",
                "cost": 15.99,
                "currency": "USD",
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )
        assert response.status_code == 201
        sub_id = response.json()["id"]
        assert response.json()["last_used_at"] is None

        # Mark as used
        response = auth_client.post(f"/subscriptions/{sub_id}/mark-used")
        assert response.status_code == 200
        data = response.json()
        assert data["last_used_at"] is not None
        # Verify timestamp is recent (within last minute)
        last_used_str = data["last_used_at"]
        if "Z" in last_used_str:
            last_used_str = last_used_str.replace("Z", "+00:00")
        elif "+" not in last_used_str and last_used_str[-6:-5] != "-":
            # No timezone info, assume UTC
            last_used_str = last_used_str + "+00:00"
        last_used = datetime.fromisoformat(last_used_str)
        if last_used.tzinfo is None:
            last_used = last_used.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        assert (now - last_used).total_seconds() < 60

    def test_mark_used_not_found(self, auth_client):
        """Marking non-existent subscription should return 404."""
        response = auth_client.post("/subscriptions/99999/mark-used")
        assert response.status_code == 404

    def test_mark_used_other_user(self, auth_client, second_auth_client):
        """Cannot mark another user's subscription as used."""
        # Create subscription as first user
        response = auth_client.post(
            "/subscriptions",
            json={
                "name": "Netflix",
                "cost": 15.99,
                "currency": "USD",
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )
        sub_id = response.json()["id"]

        # Try to mark as used as second user
        response = second_auth_client.post(f"/subscriptions/{sub_id}/mark-used")
        assert response.status_code == 404

    def test_mark_used_requires_auth(self, client):
        """Mark-used endpoint requires authentication."""
        response = client.post("/subscriptions/1/mark-used")
        assert response.status_code == 401


class TestSpendingTrends:
    """Tests for GET /subscriptions/analytics/trends endpoint."""

    def test_trends_empty_user(self, auth_client):
        """User with no subscriptions should get empty trends."""
        response = auth_client.get("/subscriptions/analytics/trends")
        assert response.status_code == 200
        data = response.json()
        assert data == []

    def test_trends_single_subscription(self, auth_client):
        """Single subscription should produce valid trend data."""
        # Create subscription
        auth_client.post(
            "/subscriptions",
            json={
                "name": "Netflix",
                "cost": 15.99,
                "currency": "USD",
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )

        response = auth_client.get("/subscriptions/analytics/trends")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1  # One currency
        assert data[0]["currency"] == "USD"
        assert len(data[0]["data_points"]) == 6  # 6 months
        # Current month should have cost
        assert data[0]["data_points"][-1]["total_monthly_cost"] == 15.99
        assert data[0]["data_points"][-1]["subscription_count"] == 1

    def test_trends_multiple_currencies(self, auth_client):
        """Should return separate trends for each currency."""
        # Create USD subscription
        auth_client.post(
            "/subscriptions",
            json={
                "name": "Netflix",
                "cost": 15.99,
                "currency": "USD",
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )
        # Create EUR subscription
        auth_client.post(
            "/subscriptions",
            json={
                "name": "Spotify",
                "cost": 9.99,
                "currency": "EUR",
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )

        response = auth_client.get("/subscriptions/analytics/trends")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        currencies = {d["currency"] for d in data}
        assert currencies == {"USD", "EUR"}

    def test_trends_direction_stable(self, auth_client):
        """Single subscription should have stable trend."""
        auth_client.post(
            "/subscriptions",
            json={
                "name": "Netflix",
                "cost": 15.99,
                "currency": "USD",
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )

        response = auth_client.get("/subscriptions/analytics/trends")
        data = response.json()
        # With a single subscription, trend should be stable
        assert data[0]["trend_direction"] == "stable"

    def test_trends_excludes_cancelled(self, auth_client, db_session):
        """Subscriptions cancelled before the month started should not appear."""
        from app.models.subscription import Subscription

        # Create subscription
        resp = auth_client.post(
            "/subscriptions",
            json={
                "name": "Netflix",
                "cost": 15.99,
                "currency": "USD",
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )
        sub_id = resp.json()["id"]

        # Cancel it (still active in current month since cancelled during the month)
        auth_client.post(f"/subscriptions/{sub_id}/cancel")

        # Force the cancellation date to be before the current month started
        sub = db_session.query(Subscription).filter(Subscription.id == sub_id).first()
        first_of_month = date.today().replace(day=1)
        sub.cancelled_at = datetime(
            first_of_month.year, first_of_month.month, 1, tzinfo=timezone.utc
        ) - timedelta(days=10)
        db_session.commit()

        response = auth_client.get("/subscriptions/analytics/trends")
        assert response.status_code == 200
        data = response.json()
        # Should be empty or have 0 cost in current month
        if data:
            current_month = data[0]["data_points"][-1]
            assert current_month["total_monthly_cost"] == 0
            assert current_month["subscription_count"] == 0

    def test_trends_requires_auth(self, client):
        """Trends endpoint requires authentication."""
        response = client.get("/subscriptions/analytics/trends")
        assert response.status_code == 401


class TestTopSubscriptions:
    """Tests for GET /subscriptions/analytics/top endpoint."""

    def test_top_empty_user(self, auth_client):
        """User with no subscriptions should get empty response."""
        response = auth_client.get("/subscriptions/analytics/top")
        assert response.status_code == 200
        data = response.json()
        assert data == []

    def test_top_respects_limit(self, auth_client):
        """Should respect the limit parameter."""
        # Create 5 subscriptions
        for i in range(5):
            auth_client.post(
                "/subscriptions",
                json={
                    "name": f"Sub {i}",
                    "cost": 10.0 + i,
                    "currency": "USD",
                    "billing_cycle": "monthly",
                    "next_billing_date": str(date.today() + timedelta(days=30)),
                },
            )

        response = auth_client.get("/subscriptions/analytics/top?limit=3")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1  # One currency
        assert len(data[0]["subscriptions"]) == 3

    def test_top_groups_by_currency(self, auth_client):
        """Should group results by currency."""
        auth_client.post(
            "/subscriptions",
            json={
                "name": "Netflix",
                "cost": 15.99,
                "currency": "USD",
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )
        auth_client.post(
            "/subscriptions",
            json={
                "name": "Spotify",
                "cost": 9.99,
                "currency": "EUR",
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )

        response = auth_client.get("/subscriptions/analytics/top")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    def test_top_calculates_percentage(self, auth_client):
        """Should calculate percentage of total correctly."""
        auth_client.post(
            "/subscriptions",
            json={
                "name": "Big Sub",
                "cost": 75.0,
                "currency": "USD",
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )
        auth_client.post(
            "/subscriptions",
            json={
                "name": "Small Sub",
                "cost": 25.0,
                "currency": "USD",
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )

        response = auth_client.get("/subscriptions/analytics/top")
        data = response.json()
        subs = data[0]["subscriptions"]
        assert subs[0]["percentage_of_total"] == 75.0
        assert subs[1]["percentage_of_total"] == 25.0

    def test_top_sorts_descending(self, auth_client):
        """Should sort subscriptions by cost descending."""
        auth_client.post(
            "/subscriptions",
            json={
                "name": "Cheap",
                "cost": 5.0,
                "currency": "USD",
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )
        auth_client.post(
            "/subscriptions",
            json={
                "name": "Expensive",
                "cost": 50.0,
                "currency": "USD",
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )

        response = auth_client.get("/subscriptions/analytics/top")
        data = response.json()
        subs = data[0]["subscriptions"]
        assert subs[0]["name"] == "Expensive"
        assert subs[1]["name"] == "Cheap"

    def test_top_requires_auth(self, client):
        """Top subscriptions endpoint requires authentication."""
        response = client.get("/subscriptions/analytics/top")
        assert response.status_code == 401


class TestForgottenSubscriptions:
    """Tests for GET /subscriptions/analytics/forgotten endpoint."""

    def test_forgotten_detects_null_last_used(self, auth_client):
        """Subscriptions with null last_used_at should be detected."""
        auth_client.post(
            "/subscriptions",
            json={
                "name": "Never Used",
                "cost": 9.99,
                "currency": "USD",
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )

        response = auth_client.get("/subscriptions/analytics/forgotten")
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1
        assert data["subscriptions"][0]["name"] == "Never Used"
        assert data["subscriptions"][0]["last_used_at"] is None
        assert data["subscriptions"][0]["days_since_used"] is None

    def test_forgotten_detects_old_last_used(self, auth_client, db_session):
        """Subscriptions not used in 30+ days should be detected."""
        from app.models.subscription import Subscription

        # Create subscription
        resp = auth_client.post(
            "/subscriptions",
            json={
                "name": "Old Sub",
                "cost": 9.99,
                "currency": "USD",
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )
        sub_id = resp.json()["id"]

        # Directly set last_used_at to 35 days ago
        sub = db_session.query(Subscription).filter(Subscription.id == sub_id).first()
        sub.last_used_at = datetime.now(timezone.utc) - timedelta(days=35)
        db_session.commit()

        response = auth_client.get("/subscriptions/analytics/forgotten")
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1
        assert data["subscriptions"][0]["days_since_used"] >= 35

    def test_forgotten_excludes_recently_used(self, auth_client):
        """Recently used subscriptions should not be listed."""
        # Create and immediately mark as used
        resp = auth_client.post(
            "/subscriptions",
            json={
                "name": "Active Sub",
                "cost": 9.99,
                "currency": "USD",
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )
        sub_id = resp.json()["id"]
        auth_client.post(f"/subscriptions/{sub_id}/mark-used")

        response = auth_client.get("/subscriptions/analytics/forgotten")
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 0

    def test_forgotten_calculates_waste(self, auth_client):
        """Should calculate total monthly waste by currency."""
        auth_client.post(
            "/subscriptions",
            json={
                "name": "Unused 1",
                "cost": 10.0,
                "currency": "USD",
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )
        auth_client.post(
            "/subscriptions",
            json={
                "name": "Unused 2",
                "cost": 15.0,
                "currency": "USD",
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )

        response = auth_client.get("/subscriptions/analytics/forgotten")
        data = response.json()
        assert data["total_monthly_waste"]["USD"] == 25.0

    def test_forgotten_requires_auth(self, client):
        """Forgotten subscriptions endpoint requires authentication."""
        response = client.get("/subscriptions/analytics/forgotten")
        assert response.status_code == 401


class TestSavingsSuggestions:
    """Tests for GET /subscriptions/analytics/savings-suggestions endpoint."""

    def test_suggestions_unused(self, auth_client):
        """Unused subscriptions should generate high confidence suggestions."""
        auth_client.post(
            "/subscriptions",
            json={
                "name": "Never Used",
                "cost": 19.99,
                "currency": "USD",
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )

        response = auth_client.get("/subscriptions/analytics/savings-suggestions")
        assert response.status_code == 200
        data = response.json()
        assert len(data["suggestions"]) >= 1
        unused_suggestion = next(
            (s for s in data["suggestions"] if s["suggestion_type"] == "unused"), None
        )
        assert unused_suggestion is not None
        assert unused_suggestion["confidence"] == "high"
        assert unused_suggestion["potential_monthly_savings"] == 19.99

    def test_suggestions_duplicate_category(self, auth_client):
        """Multiple subscriptions in same category should generate suggestion."""
        auth_client.post(
            "/subscriptions",
            json={
                "name": "Netflix",
                "cost": 15.99,
                "currency": "USD",
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
                "category": "streaming",
            },
        )
        auth_client.post(
            "/subscriptions",
            json={
                "name": "Disney+",
                "cost": 12.99,
                "currency": "USD",
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
                "category": "streaming",
            },
        )

        # Mark both as used to avoid "unused" suggestions
        auth_client.post("/subscriptions/1/mark-used")
        auth_client.post("/subscriptions/2/mark-used")

        response = auth_client.get("/subscriptions/analytics/savings-suggestions")
        data = response.json()
        duplicate_suggestion = next(
            (s for s in data["suggestions"] if s["suggestion_type"] == "duplicate_category"),
            None,
        )
        assert duplicate_suggestion is not None
        assert duplicate_suggestion["confidence"] == "medium"

    def test_suggestions_high_cost(self, auth_client):
        """Single subscription >25% of total should generate suggestion."""
        # Create one expensive and several cheap subscriptions
        auth_client.post(
            "/subscriptions",
            json={
                "name": "Expensive",
                "cost": 100.0,
                "currency": "USD",
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )
        auth_client.post(
            "/subscriptions",
            json={
                "name": "Cheap 1",
                "cost": 5.0,
                "currency": "USD",
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )
        auth_client.post(
            "/subscriptions",
            json={
                "name": "Cheap 2",
                "cost": 5.0,
                "currency": "USD",
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )

        # Mark all as used
        auth_client.post("/subscriptions/1/mark-used")
        auth_client.post("/subscriptions/2/mark-used")
        auth_client.post("/subscriptions/3/mark-used")

        response = auth_client.get("/subscriptions/analytics/savings-suggestions")
        data = response.json()
        high_cost_suggestion = next(
            (s for s in data["suggestions"] if s["suggestion_type"] == "high_cost"), None
        )
        assert high_cost_suggestion is not None
        assert high_cost_suggestion["subscription_name"] == "Expensive"
        assert high_cost_suggestion["confidence"] == "medium"

    def test_suggestions_requires_auth(self, client):
        """Savings suggestions endpoint requires authentication."""
        response = client.get("/subscriptions/analytics/savings-suggestions")
        assert response.status_code == 401


class TestCombinedAnalytics:
    """Tests for GET /subscriptions/analytics endpoint."""

    def test_combined_returns_all_data(self, auth_client):
        """Combined endpoint should return all analytics data."""
        # Create some subscriptions
        auth_client.post(
            "/subscriptions",
            json={
                "name": "Netflix",
                "cost": 15.99,
                "currency": "USD",
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
                "category": "streaming",
            },
        )

        response = auth_client.get("/subscriptions/analytics")
        assert response.status_code == 200
        data = response.json()
        assert "trends_by_currency" in data
        assert "top_subscriptions_by_currency" in data
        assert "forgotten_subscriptions" in data
        assert "savings_suggestions" in data
        assert "generated_at" in data

    def test_combined_empty_user(self, auth_client):
        """Empty user should get valid empty response."""
        response = auth_client.get("/subscriptions/analytics")
        assert response.status_code == 200
        data = response.json()
        assert data["trends_by_currency"] == []
        assert data["top_subscriptions_by_currency"] == []
        assert data["forgotten_subscriptions"]["total_count"] == 0
        assert len(data["savings_suggestions"]["suggestions"]) == 0

    def test_combined_requires_auth(self, client):
        """Combined analytics endpoint requires authentication."""
        response = client.get("/subscriptions/analytics")
        assert response.status_code == 401


class TestBillingCycleConversion:
    """Tests for billing cycle to monthly conversion in analytics."""

    def test_yearly_subscription_in_trends(self, auth_client):
        """Yearly subscriptions should be converted to monthly cost."""
        auth_client.post(
            "/subscriptions",
            json={
                "name": "Annual Sub",
                "cost": 120.0,  # $10/month
                "currency": "USD",
                "billing_cycle": "yearly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )

        response = auth_client.get("/subscriptions/analytics/trends")
        data = response.json()
        # Monthly cost should be 120/12 = 10
        assert data[0]["data_points"][-1]["total_monthly_cost"] == 10.0

    def test_quarterly_subscription_in_top(self, auth_client):
        """Quarterly subscriptions should be converted to monthly cost."""
        auth_client.post(
            "/subscriptions",
            json={
                "name": "Quarterly Sub",
                "cost": 30.0,  # $10/month
                "currency": "USD",
                "billing_cycle": "quarterly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )

        response = auth_client.get("/subscriptions/analytics/top")
        data = response.json()
        # Monthly cost should be 30/3 = 10
        assert data[0]["subscriptions"][0]["monthly_cost"] == 10.0

    def test_weekly_subscription_in_forgotten(self, auth_client):
        """Weekly subscriptions should be converted to monthly cost."""
        auth_client.post(
            "/subscriptions",
            json={
                "name": "Weekly Sub",
                "cost": 5.0,  # ~$21.67/month (5 * 52 / 12)
                "currency": "USD",
                "billing_cycle": "weekly",
                "next_billing_date": str(date.today() + timedelta(days=7)),
            },
        )

        response = auth_client.get("/subscriptions/analytics/forgotten")
        data = response.json()
        # Monthly cost should be approximately 5 * 52 / 12 = 21.67
        monthly_cost = data["subscriptions"][0]["monthly_cost"]
        assert 21.6 < monthly_cost < 21.7
