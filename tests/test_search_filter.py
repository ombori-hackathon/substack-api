"""Tests for subscription search and filter functionality."""

from datetime import date, timedelta

import pytest


# =============================================================================
# Text Search Tests
# =============================================================================


class TestTextSearch:
    """Tests for text search on subscription name."""

    def test_search_exact_match(self, auth_client):
        """Should find subscription with exact name match."""
        # Create subscriptions
        auth_client.post(
            "/subscriptions",
            json={
                "name": "Netflix",
                "cost": 15.99,
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )
        auth_client.post(
            "/subscriptions",
            json={
                "name": "Spotify",
                "cost": 9.99,
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )

        response = auth_client.get("/subscriptions?search=Netflix")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["name"] == "Netflix"

    def test_search_partial_match(self, auth_client):
        """Should find subscription with partial name match."""
        auth_client.post(
            "/subscriptions",
            json={
                "name": "Netflix Premium",
                "cost": 19.99,
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )
        auth_client.post(
            "/subscriptions",
            json={
                "name": "Hulu",
                "cost": 7.99,
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )

        response = auth_client.get("/subscriptions?search=Net")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert "Net" in data["items"][0]["name"]

    def test_search_case_insensitive(self, auth_client):
        """Should find subscription regardless of case."""
        auth_client.post(
            "/subscriptions",
            json={
                "name": "Spotify",
                "cost": 9.99,
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )

        # Search with different case
        response = auth_client.get("/subscriptions?search=SPOTIFY")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["name"] == "Spotify"

        # Search with mixed case
        response = auth_client.get("/subscriptions?search=spOtIfY")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1

    def test_search_special_characters(self, auth_client):
        """Should safely handle special characters in search (SQL injection prevention)."""
        auth_client.post(
            "/subscriptions",
            json={
                "name": "O'Reilly Safari",
                "cost": 39.99,
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )

        # Search with apostrophe
        response = auth_client.get("/subscriptions?search=O'Reilly")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["name"] == "O'Reilly Safari"

        # SQL injection attempt should not cause errors
        response = auth_client.get("/subscriptions?search='; DROP TABLE subscriptions;--")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 0  # No results, but no error

    def test_search_no_results(self, auth_client):
        """Should return empty list when no subscriptions match."""
        auth_client.post(
            "/subscriptions",
            json={
                "name": "Netflix",
                "cost": 15.99,
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )

        response = auth_client.get("/subscriptions?search=Hulu")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 0
        assert data["total_count"] == 0

    def test_search_combined_with_other_filters(self, auth_client):
        """Should combine search with category and status filters."""
        # Create streaming subscriptions
        auth_client.post(
            "/subscriptions",
            json={
                "name": "Netflix",
                "cost": 15.99,
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
                "category": "streaming",
            },
        )
        # Create software subscription with "Net" in name
        auth_client.post(
            "/subscriptions",
            json={
                "name": ".NET Tools",
                "cost": 49.99,
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
                "category": "software",
            },
        )

        # Search "Net" with streaming category filter
        response = auth_client.get("/subscriptions?search=Net&category=streaming")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["name"] == "Netflix"

    def test_search_empty_string_rejected(self, auth_client):
        """Should reject empty search string with 422."""
        response = auth_client.get("/subscriptions?search=")
        assert response.status_code == 422

    def test_search_too_long_rejected(self, auth_client):
        """Should reject search string over 100 characters."""
        long_search = "x" * 101
        response = auth_client.get(f"/subscriptions?search={long_search}")
        assert response.status_code == 422


# =============================================================================
# Billing Cycle Filter Tests
# =============================================================================


class TestBillingCycleFilter:
    """Tests for billing cycle filter."""

    def test_filter_weekly(self, auth_client):
        """Should filter subscriptions by weekly billing cycle."""
        auth_client.post(
            "/subscriptions",
            json={
                "name": "Weekly Sub",
                "cost": 5.00,
                "billing_cycle": "weekly",
                "next_billing_date": str(date.today() + timedelta(days=7)),
            },
        )
        auth_client.post(
            "/subscriptions",
            json={
                "name": "Monthly Sub",
                "cost": 15.00,
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )

        response = auth_client.get("/subscriptions?billing_cycle=weekly")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["billing_cycle"] == "weekly"

    def test_filter_monthly(self, auth_client):
        """Should filter subscriptions by monthly billing cycle."""
        auth_client.post(
            "/subscriptions",
            json={
                "name": "Weekly Sub",
                "cost": 5.00,
                "billing_cycle": "weekly",
                "next_billing_date": str(date.today() + timedelta(days=7)),
            },
        )
        auth_client.post(
            "/subscriptions",
            json={
                "name": "Monthly Sub",
                "cost": 15.00,
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )

        response = auth_client.get("/subscriptions?billing_cycle=monthly")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["billing_cycle"] == "monthly"

    def test_filter_quarterly(self, auth_client):
        """Should filter subscriptions by quarterly billing cycle."""
        auth_client.post(
            "/subscriptions",
            json={
                "name": "Quarterly Sub",
                "cost": 30.00,
                "billing_cycle": "quarterly",
                "next_billing_date": str(date.today() + timedelta(days=90)),
            },
        )
        auth_client.post(
            "/subscriptions",
            json={
                "name": "Monthly Sub",
                "cost": 15.00,
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )

        response = auth_client.get("/subscriptions?billing_cycle=quarterly")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["billing_cycle"] == "quarterly"

    def test_filter_yearly(self, auth_client):
        """Should filter subscriptions by yearly billing cycle."""
        auth_client.post(
            "/subscriptions",
            json={
                "name": "Yearly Sub",
                "cost": 120.00,
                "billing_cycle": "yearly",
                "next_billing_date": str(date.today() + timedelta(days=365)),
            },
        )
        auth_client.post(
            "/subscriptions",
            json={
                "name": "Monthly Sub",
                "cost": 15.00,
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )

        response = auth_client.get("/subscriptions?billing_cycle=yearly")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["billing_cycle"] == "yearly"

    def test_filter_invalid_cycle_rejected(self, auth_client):
        """Should reject invalid billing cycle value with 422."""
        response = auth_client.get("/subscriptions?billing_cycle=biweekly")
        assert response.status_code == 422


# =============================================================================
# Cost Range Filter Tests
# =============================================================================


class TestCostRangeFilter:
    """Tests for cost range filter."""

    def test_filter_min_only(self, auth_client):
        """Should filter subscriptions with cost >= min."""
        auth_client.post(
            "/subscriptions",
            json={
                "name": "Cheap Sub",
                "cost": 5.00,
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )
        auth_client.post(
            "/subscriptions",
            json={
                "name": "Expensive Sub",
                "cost": 50.00,
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )

        response = auth_client.get("/subscriptions?cost_min=20")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["cost"] >= 20

    def test_filter_max_only(self, auth_client):
        """Should filter subscriptions with cost <= max."""
        auth_client.post(
            "/subscriptions",
            json={
                "name": "Cheap Sub",
                "cost": 5.00,
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )
        auth_client.post(
            "/subscriptions",
            json={
                "name": "Expensive Sub",
                "cost": 50.00,
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )

        response = auth_client.get("/subscriptions?cost_max=20")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["cost"] <= 20

    def test_filter_range(self, auth_client):
        """Should filter subscriptions within cost range."""
        auth_client.post(
            "/subscriptions",
            json={
                "name": "Cheap Sub",
                "cost": 5.00,
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )
        auth_client.post(
            "/subscriptions",
            json={
                "name": "Medium Sub",
                "cost": 15.00,
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )
        auth_client.post(
            "/subscriptions",
            json={
                "name": "Expensive Sub",
                "cost": 50.00,
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )

        response = auth_client.get("/subscriptions?cost_min=10&cost_max=20")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["name"] == "Medium Sub"

    def test_filter_range_inclusive(self, auth_client):
        """Should include subscriptions at exact min and max bounds."""
        auth_client.post(
            "/subscriptions",
            json={
                "name": "At Min",
                "cost": 10.00,
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )
        auth_client.post(
            "/subscriptions",
            json={
                "name": "At Max",
                "cost": 20.00,
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )

        response = auth_client.get("/subscriptions?cost_min=10&cost_max=20")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2

    def test_filter_negative_rejected(self, auth_client):
        """Should reject negative cost values with 422."""
        response = auth_client.get("/subscriptions?cost_min=-5")
        assert response.status_code == 422

        response = auth_client.get("/subscriptions?cost_max=-10")
        assert response.status_code == 422


# =============================================================================
# Combined Filters Tests
# =============================================================================


class TestCombinedFilters:
    """Tests for combining multiple filters."""

    def test_all_filters_combined(self, auth_client):
        """Should apply all filters together."""
        # Create various subscriptions
        auth_client.post(
            "/subscriptions",
            json={
                "name": "Netflix",
                "cost": 15.99,
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
                "category": "streaming",
            },
        )
        auth_client.post(
            "/subscriptions",
            json={
                "name": "Netflix Premium Yearly",
                "cost": 199.99,
                "billing_cycle": "yearly",
                "next_billing_date": str(date.today() + timedelta(days=365)),
                "category": "streaming",
            },
        )
        auth_client.post(
            "/subscriptions",
            json={
                "name": "Hulu",
                "cost": 12.99,
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
                "category": "streaming",
            },
        )
        auth_client.post(
            "/subscriptions",
            json={
                "name": "GitHub",
                "cost": 4.00,
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
                "category": "software",
            },
        )

        # Search "Net" + monthly billing + cost between 10-20 + streaming category
        response = auth_client.get(
            "/subscriptions?search=Net&billing_cycle=monthly&cost_min=10&cost_max=20&category=streaming"
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["name"] == "Netflix"

    def test_search_with_status_filter(self, auth_client):
        """Should combine search with status filter."""
        # Create and cancel a subscription
        create_response = auth_client.post(
            "/subscriptions",
            json={
                "name": "Netflix",
                "cost": 15.99,
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )
        subscription_id = create_response.json()["id"]
        auth_client.post(f"/subscriptions/{subscription_id}/cancel")

        # Create active subscription
        auth_client.post(
            "/subscriptions",
            json={
                "name": "Netflix Premium",
                "cost": 19.99,
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )

        # Search "Netflix" in cancelled
        response = auth_client.get("/subscriptions?search=Netflix&status=cancelled")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["status"] == "cancelled"

        # Search "Netflix" in active
        response = auth_client.get("/subscriptions?search=Netflix&status=active")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["status"] == "active"

    def test_search_with_sort(self, auth_client):
        """Should combine search with sorting."""
        auth_client.post(
            "/subscriptions",
            json={
                "name": "Apple TV+",
                "cost": 6.99,
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )
        auth_client.post(
            "/subscriptions",
            json={
                "name": "Apple Music",
                "cost": 10.99,
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )
        auth_client.post(
            "/subscriptions",
            json={
                "name": "Apple One",
                "cost": 19.95,
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )

        # Search "Apple" sorted by cost descending
        response = auth_client.get("/subscriptions?search=Apple&sort_by=cost&order=desc")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 3
        assert data["items"][0]["name"] == "Apple One"
        assert data["items"][1]["name"] == "Apple Music"
        assert data["items"][2]["name"] == "Apple TV+"

    def test_filters_with_pagination(self, auth_client):
        """Should apply filters correctly with pagination."""
        # Create 5 streaming subscriptions
        for i in range(5):
            auth_client.post(
                "/subscriptions",
                json={
                    "name": f"Streaming {i}",
                    "cost": 10.00 + i,
                    "billing_cycle": "monthly",
                    "next_billing_date": str(date.today() + timedelta(days=30 + i)),
                    "category": "streaming",
                },
            )
        # Create non-streaming subscriptions
        for i in range(3):
            auth_client.post(
                "/subscriptions",
                json={
                    "name": f"Software {i}",
                    "cost": 20.00 + i,
                    "billing_cycle": "monthly",
                    "next_billing_date": str(date.today() + timedelta(days=30)),
                    "category": "software",
                },
            )

        # Filter streaming with pagination
        response = auth_client.get("/subscriptions?category=streaming&limit=2&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total_count"] == 5  # Total matching filter

        response = auth_client.get("/subscriptions?category=streaming&limit=2&offset=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total_count"] == 5
