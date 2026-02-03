"""Tests for subscription CRUD endpoints."""

from datetime import date, timedelta

import pytest


# =============================================================================
# Authentication Tests
# =============================================================================


class TestAuthRequired:
    """Tests for authentication requirements."""

    def test_create_no_token(self, client):
        """Should return 401 when no token is provided."""
        response = client.post(
            "/subscriptions",
            json={
                "name": "Netflix",
                "cost": 15.99,
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )
        assert response.status_code == 401

    def test_create_invalid_token(self, client):
        """Should return 401 when token is invalid."""
        response = client.post(
            "/subscriptions",
            json={
                "name": "Netflix",
                "cost": 15.99,
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert response.status_code == 401

    def test_list_no_token(self, client):
        """Should return 401 when no token is provided for list."""
        response = client.get("/subscriptions")
        assert response.status_code == 401

    def test_get_no_token(self, client):
        """Should return 401 when no token is provided for get."""
        response = client.get("/subscriptions/1")
        assert response.status_code == 401


# =============================================================================
# Create Subscription Tests
# =============================================================================


class TestCreateSubscription:
    """Tests for POST /subscriptions endpoint."""

    def test_create_minimal_fields(self, auth_client):
        """Should create subscription with minimal required fields."""
        response = auth_client.post(
            "/subscriptions",
            json={
                "name": "Netflix",
                "cost": 15.99,
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Netflix"
        assert data["cost"] == 15.99
        assert data["currency"] == "USD"  # default
        assert data["billing_cycle"] == "monthly"
        assert data["reminder_days_before"] == 3  # default
        assert data["category"] is None
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_create_all_fields(self, auth_client):
        """Should create subscription with all fields."""
        response = auth_client.post(
            "/subscriptions",
            json={
                "name": "Spotify",
                "cost": 9.99,
                "currency": "EUR",
                "billing_cycle": "yearly",
                "next_billing_date": str(date.today() + timedelta(days=365)),
                "category": "streaming",
                "reminder_days_before": 7,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Spotify"
        assert data["cost"] == 9.99
        assert data["currency"] == "EUR"
        assert data["billing_cycle"] == "yearly"
        assert data["category"] == "streaming"
        assert data["reminder_days_before"] == 7

    def test_create_duplicate_name_allowed(self, auth_client):
        """Should allow creating subscriptions with same name."""
        subscription_data = {
            "name": "Netflix",
            "cost": 15.99,
            "billing_cycle": "monthly",
            "next_billing_date": str(date.today() + timedelta(days=30)),
        }
        response1 = auth_client.post("/subscriptions", json=subscription_data)
        assert response1.status_code == 201

        response2 = auth_client.post("/subscriptions", json=subscription_data)
        assert response2.status_code == 201
        assert response1.json()["id"] != response2.json()["id"]


class TestCreateValidation:
    """Tests for subscription creation validation."""

    def test_create_missing_name(self, auth_client):
        """Should return 422 when name is missing."""
        response = auth_client.post(
            "/subscriptions",
            json={
                "cost": 15.99,
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )
        assert response.status_code == 422

    def test_create_empty_name(self, auth_client):
        """Should return 422 when name is empty."""
        response = auth_client.post(
            "/subscriptions",
            json={
                "name": "",
                "cost": 15.99,
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )
        assert response.status_code == 422

    def test_create_name_too_long(self, auth_client):
        """Should return 422 when name exceeds 100 characters."""
        response = auth_client.post(
            "/subscriptions",
            json={
                "name": "x" * 101,
                "cost": 15.99,
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )
        assert response.status_code == 422

    def test_create_negative_cost(self, auth_client):
        """Should return 422 when cost is negative."""
        response = auth_client.post(
            "/subscriptions",
            json={
                "name": "Netflix",
                "cost": -15.99,
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )
        assert response.status_code == 422

    def test_create_zero_cost(self, auth_client):
        """Should return 422 when cost is zero."""
        response = auth_client.post(
            "/subscriptions",
            json={
                "name": "Netflix",
                "cost": 0,
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )
        assert response.status_code == 422

    def test_create_past_billing_date(self, auth_client):
        """Should return 422 when next_billing_date is in the past."""
        response = auth_client.post(
            "/subscriptions",
            json={
                "name": "Netflix",
                "cost": 15.99,
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() - timedelta(days=1)),
            },
        )
        assert response.status_code == 422

    def test_create_invalid_currency(self, auth_client):
        """Should return 422 when currency is invalid."""
        response = auth_client.post(
            "/subscriptions",
            json={
                "name": "Netflix",
                "cost": 15.99,
                "currency": "INVALID",
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )
        assert response.status_code == 422

    def test_create_invalid_billing_cycle(self, auth_client):
        """Should return 422 when billing_cycle is invalid."""
        response = auth_client.post(
            "/subscriptions",
            json={
                "name": "Netflix",
                "cost": 15.99,
                "billing_cycle": "biweekly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )
        assert response.status_code == 422

    def test_create_invalid_category(self, auth_client):
        """Should return 422 when category is invalid."""
        response = auth_client.post(
            "/subscriptions",
            json={
                "name": "Netflix",
                "cost": 15.99,
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
                "category": "entertainment",
            },
        )
        assert response.status_code == 422

    def test_create_reminder_too_high(self, auth_client):
        """Should return 422 when reminder_days_before exceeds 30."""
        response = auth_client.post(
            "/subscriptions",
            json={
                "name": "Netflix",
                "cost": 15.99,
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
                "reminder_days_before": 31,
            },
        )
        assert response.status_code == 422

    def test_create_reminder_negative(self, auth_client):
        """Should return 422 when reminder_days_before is negative."""
        response = auth_client.post(
            "/subscriptions",
            json={
                "name": "Netflix",
                "cost": 15.99,
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
                "reminder_days_before": -1,
            },
        )
        assert response.status_code == 422


# =============================================================================
# List Subscriptions Tests
# =============================================================================


class TestListSubscriptions:
    """Tests for GET /subscriptions endpoint."""

    def test_list_empty(self, auth_client):
        """Should return empty list when user has no subscriptions."""
        response = auth_client.get("/subscriptions")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total_count"] == 0

    def test_list_multiple(self, auth_client):
        """Should return all user's subscriptions."""
        # Create two subscriptions
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

        response = auth_client.get("/subscriptions")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        names = [sub["name"] for sub in data["items"]]
        assert "Netflix" in names
        assert "Spotify" in names


class TestSubscriptionIsolation:
    """Tests for user subscription isolation."""

    def test_list_only_own_subscriptions(self, auth_client, db_session):
        """Should only return subscriptions owned by the current user."""
        from app.auth import create_access_token, hash_password
        from app.models.subscription import Subscription
        from app.models.user import User

        # Create another user with a subscription directly in DB
        other_user = User(
            email="other@example.com",
            hashed_password=hash_password("password123"),
        )
        db_session.add(other_user)
        db_session.commit()
        db_session.refresh(other_user)

        other_subscription = Subscription(
            user_id=other_user.id,
            name="Other's Netflix",
            cost=15.99,
            currency="USD",
            billing_cycle="monthly",
            next_billing_date=date.today() + timedelta(days=30),
        )
        db_session.add(other_subscription)
        db_session.commit()

        # Create a subscription for the authenticated user
        auth_client.post(
            "/subscriptions",
            json={
                "name": "My Netflix",
                "cost": 15.99,
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )

        # List should only show authenticated user's subscription
        response = auth_client.get("/subscriptions")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["name"] == "My Netflix"


# =============================================================================
# Get Single Subscription Tests
# =============================================================================


class TestGetSubscription:
    """Tests for GET /subscriptions/{id} endpoint."""

    def test_get_exists(self, auth_client):
        """Should return subscription when it exists."""
        # Create subscription
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

        response = auth_client.get(f"/subscriptions/{subscription_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Netflix"
        assert data["id"] == subscription_id

    def test_get_not_found(self, auth_client):
        """Should return 404 when subscription doesn't exist."""
        response = auth_client.get("/subscriptions/9999")
        assert response.status_code == 404

    def test_get_other_users_subscription(self, auth_client, db_session):
        """Should return 404 when trying to get another user's subscription."""
        from app.auth import hash_password
        from app.models.subscription import Subscription
        from app.models.user import User

        # Create another user with a subscription
        other_user = User(
            email="other2@example.com",
            hashed_password=hash_password("password123"),
        )
        db_session.add(other_user)
        db_session.commit()
        db_session.refresh(other_user)

        other_subscription = Subscription(
            user_id=other_user.id,
            name="Other's Spotify",
            cost=9.99,
            currency="USD",
            billing_cycle="monthly",
            next_billing_date=date.today() + timedelta(days=30),
        )
        db_session.add(other_subscription)
        db_session.commit()
        db_session.refresh(other_subscription)

        # Try to get other user's subscription
        response = auth_client.get(f"/subscriptions/{other_subscription.id}")
        assert response.status_code == 404


# =============================================================================
# Update Subscription Tests
# =============================================================================


class TestUpdateSubscription:
    """Tests for PUT /subscriptions/{id} endpoint."""

    def test_update_single_field(self, auth_client):
        """Should update single field."""
        # Create subscription
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

        # Update name
        response = auth_client.put(
            f"/subscriptions/{subscription_id}",
            json={"name": "Netflix Premium"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Netflix Premium"
        assert data["cost"] == 15.99  # Unchanged

    def test_update_multiple_fields(self, auth_client):
        """Should update multiple fields."""
        # Create subscription
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

        # Update multiple fields
        new_date = str(date.today() + timedelta(days=60))
        response = auth_client.put(
            f"/subscriptions/{subscription_id}",
            json={
                "name": "Netflix Premium",
                "cost": 19.99,
                "billing_cycle": "yearly",
                "next_billing_date": new_date,
                "category": "streaming",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Netflix Premium"
        assert data["cost"] == 19.99
        assert data["billing_cycle"] == "yearly"
        assert data["category"] == "streaming"

    def test_update_not_found(self, auth_client):
        """Should return 404 when subscription doesn't exist."""
        response = auth_client.put(
            "/subscriptions/9999",
            json={"name": "Updated"},
        )
        assert response.status_code == 404

    def test_update_other_users_subscription(self, auth_client, db_session):
        """Should return 404 when trying to update another user's subscription."""
        from app.auth import hash_password
        from app.models.subscription import Subscription
        from app.models.user import User

        # Create another user with a subscription
        other_user = User(
            email="other3@example.com",
            hashed_password=hash_password("password123"),
        )
        db_session.add(other_user)
        db_session.commit()
        db_session.refresh(other_user)

        other_subscription = Subscription(
            user_id=other_user.id,
            name="Other's Netflix",
            cost=15.99,
            currency="USD",
            billing_cycle="monthly",
            next_billing_date=date.today() + timedelta(days=30),
        )
        db_session.add(other_subscription)
        db_session.commit()
        db_session.refresh(other_subscription)

        # Try to update other user's subscription
        response = auth_client.put(
            f"/subscriptions/{other_subscription.id}",
            json={"name": "Hijacked"},
        )
        assert response.status_code == 404

    def test_update_validation_error(self, auth_client):
        """Should return 422 for invalid update data."""
        # Create subscription
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

        # Try to update with invalid cost
        response = auth_client.put(
            f"/subscriptions/{subscription_id}",
            json={"cost": -5.00},
        )
        assert response.status_code == 422


class TestUpdateConflictDetection:
    """Tests for optimistic locking with If-Unmodified-Since header."""

    def test_update_with_matching_updated_at(self, auth_client):
        """Should succeed when If-Unmodified-Since matches updated_at."""
        # Create subscription
        create_response = auth_client.post(
            "/subscriptions",
            json={
                "name": "Netflix",
                "cost": 15.99,
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )
        subscription = create_response.json()
        subscription_id = subscription["id"]
        updated_at = subscription["updated_at"]

        # Update with matching If-Unmodified-Since
        response = auth_client.put(
            f"/subscriptions/{subscription_id}",
            json={"name": "Netflix Premium"},
            headers={"If-Unmodified-Since": updated_at},
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Netflix Premium"

    def test_update_with_stale_updated_at(self, auth_client):
        """Should return 409 when If-Unmodified-Since is stale."""
        # Create subscription
        create_response = auth_client.post(
            "/subscriptions",
            json={
                "name": "Netflix",
                "cost": 15.99,
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )
        subscription = create_response.json()
        subscription_id = subscription["id"]
        original_updated_at = subscription["updated_at"]

        # First update (simulate another session)
        auth_client.put(
            f"/subscriptions/{subscription_id}",
            json={"name": "Netflix Updated"},
        )

        # Try to update with stale timestamp
        response = auth_client.put(
            f"/subscriptions/{subscription_id}",
            json={"name": "Netflix Premium"},
            headers={"If-Unmodified-Since": original_updated_at},
        )
        assert response.status_code == 409
        data = response.json()
        assert "modified by another session" in data["detail"].lower()
        assert "x-current-updated-at" in response.headers

    def test_update_without_if_unmodified_since(self, auth_client):
        """Should succeed when If-Unmodified-Since is not provided (backward compatible)."""
        # Create subscription
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

        # Update without If-Unmodified-Since header
        response = auth_client.put(
            f"/subscriptions/{subscription_id}",
            json={"name": "Netflix Premium"},
        )
        assert response.status_code == 200

    def test_update_deleted_subscription_message(self, auth_client):
        """Should return 404 with clear message when subscription was deleted."""
        # Create subscription
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

        # Delete subscription
        auth_client.delete(f"/subscriptions/{subscription_id}")

        # Try to update deleted subscription
        response = auth_client.put(
            f"/subscriptions/{subscription_id}",
            json={"name": "Netflix Premium"},
        )
        assert response.status_code == 404
        data = response.json()
        assert "deleted" in data["detail"].lower() or "not found" in data["detail"].lower()


# =============================================================================
# Delete Subscription Tests
# =============================================================================


class TestDeleteSubscription:
    """Tests for DELETE /subscriptions/{id} endpoint."""

    def test_delete_exists(self, auth_client):
        """Should soft delete subscription and return 204."""
        # Create subscription
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

        # Delete
        response = auth_client.delete(f"/subscriptions/{subscription_id}")
        assert response.status_code == 204

        # Verify it's not accessible via API
        get_response = auth_client.get(f"/subscriptions/{subscription_id}")
        assert get_response.status_code == 404

    def test_delete_not_found(self, auth_client):
        """Should return 404 when subscription doesn't exist."""
        response = auth_client.delete("/subscriptions/9999")
        assert response.status_code == 404

    def test_delete_other_users_subscription(self, auth_client, db_session):
        """Should return 404 when trying to delete another user's subscription."""
        from app.auth import hash_password
        from app.models.subscription import Subscription
        from app.models.user import User

        # Create another user with a subscription
        other_user = User(
            email="other4@example.com",
            hashed_password=hash_password("password123"),
        )
        db_session.add(other_user)
        db_session.commit()
        db_session.refresh(other_user)

        other_subscription = Subscription(
            user_id=other_user.id,
            name="Other's Netflix",
            cost=15.99,
            currency="USD",
            billing_cycle="monthly",
            next_billing_date=date.today() + timedelta(days=30),
        )
        db_session.add(other_subscription)
        db_session.commit()
        db_session.refresh(other_subscription)

        # Try to delete other user's subscription
        response = auth_client.delete(f"/subscriptions/{other_subscription.id}")
        assert response.status_code == 404

        # Verify it still exists
        db_session.refresh(other_subscription)
        assert other_subscription.id is not None


class TestSoftDelete:
    """Tests for soft delete behavior."""

    def test_delete_sets_deleted_at(self, auth_client, db_session):
        """Should set deleted_at timestamp instead of hard deleting."""
        from app.models.subscription import Subscription

        # Create subscription
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

        # Delete
        response = auth_client.delete(f"/subscriptions/{subscription_id}")
        assert response.status_code == 204

        # Verify the record still exists in DB with deleted_at set
        subscription = db_session.query(Subscription).filter(
            Subscription.id == subscription_id
        ).first()
        assert subscription is not None
        assert subscription.deleted_at is not None

    def test_list_excludes_soft_deleted(self, auth_client):
        """Should not include soft-deleted subscriptions in list."""
        # Create two subscriptions
        auth_client.post(
            "/subscriptions",
            json={
                "name": "Netflix",
                "cost": 15.99,
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )
        create_response = auth_client.post(
            "/subscriptions",
            json={
                "name": "Spotify",
                "cost": 9.99,
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )
        spotify_id = create_response.json()["id"]

        # Delete Spotify
        auth_client.delete(f"/subscriptions/{spotify_id}")

        # List should only show Netflix
        response = auth_client.get("/subscriptions")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["name"] == "Netflix"
        assert data["total_count"] == 1

    def test_get_returns_404_for_soft_deleted(self, auth_client):
        """Should return 404 when getting a soft-deleted subscription."""
        # Create subscription
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

        # Delete it
        auth_client.delete(f"/subscriptions/{subscription_id}")

        # Try to get it
        response = auth_client.get(f"/subscriptions/{subscription_id}")
        assert response.status_code == 404

    def test_update_returns_404_for_soft_deleted(self, auth_client):
        """Should return 404 when updating a soft-deleted subscription."""
        # Create subscription
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

        # Delete it
        auth_client.delete(f"/subscriptions/{subscription_id}")

        # Try to update it
        response = auth_client.put(
            f"/subscriptions/{subscription_id}",
            json={"name": "Netflix Premium"},
        )
        assert response.status_code == 404

    def test_delete_already_deleted_returns_404(self, auth_client):
        """Should return 404 when trying to delete an already deleted subscription."""
        # Create subscription
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

        # Delete it once
        response = auth_client.delete(f"/subscriptions/{subscription_id}")
        assert response.status_code == 204

        # Try to delete again
        response = auth_client.delete(f"/subscriptions/{subscription_id}")
        assert response.status_code == 404

    def test_totals_exclude_soft_deleted(self, auth_client):
        """Should not include soft-deleted subscriptions in totals calculation."""
        # Create two subscriptions
        auth_client.post(
            "/subscriptions",
            json={
                "name": "Netflix",
                "cost": 15.99,
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )
        create_response = auth_client.post(
            "/subscriptions",
            json={
                "name": "Spotify",
                "cost": 9.99,
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )
        spotify_id = create_response.json()["id"]

        # Delete Spotify
        auth_client.delete(f"/subscriptions/{spotify_id}")

        # Totals should only include Netflix
        response = auth_client.get("/subscriptions")
        assert response.status_code == 200
        data = response.json()
        assert len(data["totals_by_currency"]) == 1
        assert data["totals_by_currency"][0]["total"] == pytest.approx(15.99, rel=0.01)


class TestRestoreSubscription:
    """Tests for POST /subscriptions/{id}/restore endpoint."""

    def test_restore_soft_deleted_subscription(self, auth_client):
        """Should restore a soft-deleted subscription."""
        # Create subscription
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

        # Delete it
        auth_client.delete(f"/subscriptions/{subscription_id}")

        # Restore it
        response = auth_client.post(f"/subscriptions/{subscription_id}/restore")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == subscription_id
        assert data["name"] == "Netflix"

        # Verify it's accessible again
        get_response = auth_client.get(f"/subscriptions/{subscription_id}")
        assert get_response.status_code == 200

    def test_restore_not_found(self, auth_client):
        """Should return 404 when subscription doesn't exist."""
        response = auth_client.post("/subscriptions/9999/restore")
        assert response.status_code == 404

    def test_restore_not_deleted_returns_400(self, auth_client):
        """Should return 400 when trying to restore a non-deleted subscription."""
        # Create subscription
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

        # Try to restore without deleting
        response = auth_client.post(f"/subscriptions/{subscription_id}/restore")
        assert response.status_code == 400

    def test_restore_other_users_subscription_returns_404(self, auth_client, db_session):
        """Should return 404 when trying to restore another user's subscription."""
        from app.auth import hash_password
        from app.models.subscription import Subscription, utc_now
        from app.models.user import User

        # Create another user with a soft-deleted subscription
        other_user = User(
            email="other5@example.com",
            hashed_password=hash_password("password123"),
        )
        db_session.add(other_user)
        db_session.commit()
        db_session.refresh(other_user)

        other_subscription = Subscription(
            user_id=other_user.id,
            name="Other's Netflix",
            cost=15.99,
            currency="USD",
            billing_cycle="monthly",
            next_billing_date=date.today() + timedelta(days=30),
            deleted_at=utc_now(),
        )
        db_session.add(other_subscription)
        db_session.commit()
        db_session.refresh(other_subscription)

        # Try to restore other user's subscription
        response = auth_client.post(f"/subscriptions/{other_subscription.id}/restore")
        assert response.status_code == 404

    def test_restore_appears_in_list(self, auth_client):
        """Should show restored subscription in list after restore."""
        # Create subscription
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

        # Delete and restore
        auth_client.delete(f"/subscriptions/{subscription_id}")
        auth_client.post(f"/subscriptions/{subscription_id}/restore")

        # Verify it appears in list
        response = auth_client.get("/subscriptions")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == subscription_id


# =============================================================================
# Sorting Tests
# =============================================================================


class TestListSorting:
    """Tests for subscription list sorting."""

    def test_list_sorted_by_next_billing_date_asc_default(self, auth_client):
        """Should sort by next_billing_date ascending by default."""
        # Create subscriptions with different dates
        auth_client.post(
            "/subscriptions",
            json={
                "name": "Later",
                "cost": 10.00,
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=60)),
            },
        )
        auth_client.post(
            "/subscriptions",
            json={
                "name": "Sooner",
                "cost": 10.00,
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=10)),
            },
        )
        auth_client.post(
            "/subscriptions",
            json={
                "name": "Middle",
                "cost": 10.00,
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )

        response = auth_client.get("/subscriptions")
        assert response.status_code == 200
        data = response.json()
        items = data["items"]
        assert len(items) == 3
        assert items[0]["name"] == "Sooner"
        assert items[1]["name"] == "Middle"
        assert items[2]["name"] == "Later"

    def test_list_sorted_by_next_billing_date_desc(self, auth_client):
        """Should sort by next_billing_date descending."""
        auth_client.post(
            "/subscriptions",
            json={
                "name": "Later",
                "cost": 10.00,
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=60)),
            },
        )
        auth_client.post(
            "/subscriptions",
            json={
                "name": "Sooner",
                "cost": 10.00,
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=10)),
            },
        )

        response = auth_client.get("/subscriptions?sort_by=next_billing_date&order=desc")
        assert response.status_code == 200
        data = response.json()
        items = data["items"]
        assert items[0]["name"] == "Later"
        assert items[1]["name"] == "Sooner"

    def test_list_sorted_by_name(self, auth_client):
        """Should sort by name alphabetically."""
        auth_client.post(
            "/subscriptions",
            json={
                "name": "Zebra",
                "cost": 10.00,
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )
        auth_client.post(
            "/subscriptions",
            json={
                "name": "Apple",
                "cost": 10.00,
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )

        response = auth_client.get("/subscriptions?sort_by=name&order=asc")
        assert response.status_code == 200
        data = response.json()
        items = data["items"]
        assert items[0]["name"] == "Apple"
        assert items[1]["name"] == "Zebra"

    def test_list_sorted_by_cost(self, auth_client):
        """Should sort by cost."""
        auth_client.post(
            "/subscriptions",
            json={
                "name": "Expensive",
                "cost": 99.99,
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )
        auth_client.post(
            "/subscriptions",
            json={
                "name": "Cheap",
                "cost": 4.99,
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )

        response = auth_client.get("/subscriptions?sort_by=cost&order=desc")
        assert response.status_code == 200
        data = response.json()
        items = data["items"]
        assert items[0]["name"] == "Expensive"
        assert items[1]["name"] == "Cheap"

    def test_list_invalid_sort_field(self, auth_client):
        """Should return 422 for invalid sort field."""
        response = auth_client.get("/subscriptions?sort_by=invalid_field")
        assert response.status_code == 422


# =============================================================================
# Filtering Tests
# =============================================================================


class TestListFiltering:
    """Tests for subscription list filtering."""

    def test_list_filter_by_category(self, auth_client):
        """Should filter by category."""
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
                "name": "GitHub",
                "cost": 4.00,
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
                "category": "software",
            },
        )
        auth_client.post(
            "/subscriptions",
            json={
                "name": "Spotify",
                "cost": 9.99,
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
                "category": "streaming",
            },
        )

        response = auth_client.get("/subscriptions?category=streaming")
        assert response.status_code == 200
        data = response.json()
        items = data["items"]
        assert len(items) == 2
        assert all(item["category"] == "streaming" for item in items)

    def test_list_filter_returns_empty(self, auth_client):
        """Should return empty list when filter matches nothing."""
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

        response = auth_client.get("/subscriptions?category=gaming")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total_count"] == 0


# =============================================================================
# Pagination Tests
# =============================================================================


class TestListPagination:
    """Tests for subscription list pagination."""

    def test_list_default_limit_50(self, auth_client):
        """Should use default limit of 50."""
        # Create 3 subscriptions
        for i in range(3):
            auth_client.post(
                "/subscriptions",
                json={
                    "name": f"Sub {i}",
                    "cost": 10.00,
                    "billing_cycle": "monthly",
                    "next_billing_date": str(date.today() + timedelta(days=30)),
                },
            )

        response = auth_client.get("/subscriptions")
        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 50
        assert data["offset"] == 0

    def test_list_custom_limit(self, auth_client):
        """Should respect custom limit."""
        for i in range(5):
            auth_client.post(
                "/subscriptions",
                json={
                    "name": f"Sub {i}",
                    "cost": 10.00,
                    "billing_cycle": "monthly",
                    "next_billing_date": str(date.today() + timedelta(days=30)),
                },
            )

        response = auth_client.get("/subscriptions?limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["limit"] == 2
        assert data["total_count"] == 5

    def test_list_max_limit_100(self, auth_client):
        """Should reject limit over 100."""
        response = auth_client.get("/subscriptions?limit=200")
        assert response.status_code == 422

    def test_list_offset(self, auth_client):
        """Should skip items based on offset."""
        # Create 5 subscriptions with sequential dates for predictable order
        for i in range(5):
            auth_client.post(
                "/subscriptions",
                json={
                    "name": f"Sub {i}",
                    "cost": 10.00,
                    "billing_cycle": "monthly",
                    "next_billing_date": str(date.today() + timedelta(days=10 + i)),
                },
            )

        response = auth_client.get("/subscriptions?limit=2&offset=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["offset"] == 2
        assert data["items"][0]["name"] == "Sub 2"
        assert data["items"][1]["name"] == "Sub 3"

    def test_list_total_count_with_pagination(self, auth_client):
        """Should return correct total_count regardless of pagination."""
        for i in range(10):
            auth_client.post(
                "/subscriptions",
                json={
                    "name": f"Sub {i}",
                    "cost": 10.00,
                    "billing_cycle": "monthly",
                    "next_billing_date": str(date.today() + timedelta(days=30)),
                },
            )

        response = auth_client.get("/subscriptions?limit=3&offset=5")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 3
        assert data["total_count"] == 10


# =============================================================================
# Totals Tests
# =============================================================================


class TestListTotals:
    """Tests for subscription totals by currency."""

    def test_totals_single_currency(self, auth_client):
        """Should calculate totals for single currency."""
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
                "currency": "USD",
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )

        response = auth_client.get("/subscriptions")
        assert response.status_code == 200
        data = response.json()
        totals = data["totals_by_currency"]
        assert len(totals) == 1
        assert totals[0]["currency"] == "USD"
        assert totals[0]["total"] == pytest.approx(25.98, rel=0.01)
        assert totals[0]["monthly_equivalent"] == pytest.approx(25.98, rel=0.01)

    def test_totals_mixed_currencies(self, auth_client):
        """Should calculate separate totals for each currency."""
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
        auth_client.post(
            "/subscriptions",
            json={
                "name": "Hulu",
                "cost": 7.99,
                "currency": "USD",
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )

        response = auth_client.get("/subscriptions")
        assert response.status_code == 200
        data = response.json()
        totals = data["totals_by_currency"]
        assert len(totals) == 2

        # Find each currency total
        usd_total = next((t for t in totals if t["currency"] == "USD"), None)
        eur_total = next((t for t in totals if t["currency"] == "EUR"), None)

        assert usd_total is not None
        assert usd_total["total"] == pytest.approx(23.98, rel=0.01)

        assert eur_total is not None
        assert eur_total["total"] == pytest.approx(9.99, rel=0.01)

    def test_totals_monthly_equivalent_weekly(self, auth_client):
        """Should convert weekly to monthly equivalent (x4.33)."""
        auth_client.post(
            "/subscriptions",
            json={
                "name": "Weekly Sub",
                "cost": 10.00,
                "currency": "USD",
                "billing_cycle": "weekly",
                "next_billing_date": str(date.today() + timedelta(days=7)),
            },
        )

        response = auth_client.get("/subscriptions")
        assert response.status_code == 200
        data = response.json()
        totals = data["totals_by_currency"]
        assert len(totals) == 1
        # Weekly: 10.00 * 52/12 = 43.33 monthly equivalent
        assert totals[0]["total"] == pytest.approx(10.00, rel=0.01)
        assert totals[0]["monthly_equivalent"] == pytest.approx(43.33, rel=0.01)

    def test_totals_monthly_equivalent_yearly(self, auth_client):
        """Should convert yearly to monthly equivalent (/12)."""
        auth_client.post(
            "/subscriptions",
            json={
                "name": "Yearly Sub",
                "cost": 120.00,
                "currency": "USD",
                "billing_cycle": "yearly",
                "next_billing_date": str(date.today() + timedelta(days=365)),
            },
        )

        response = auth_client.get("/subscriptions")
        assert response.status_code == 200
        data = response.json()
        totals = data["totals_by_currency"]
        assert len(totals) == 1
        # Yearly: 120.00 / 12 = 10.00 monthly equivalent
        assert totals[0]["total"] == pytest.approx(120.00, rel=0.01)
        assert totals[0]["monthly_equivalent"] == pytest.approx(10.00, rel=0.01)

    def test_totals_monthly_equivalent_quarterly(self, auth_client):
        """Should convert quarterly to monthly equivalent (/3)."""
        auth_client.post(
            "/subscriptions",
            json={
                "name": "Quarterly Sub",
                "cost": 30.00,
                "currency": "USD",
                "billing_cycle": "quarterly",
                "next_billing_date": str(date.today() + timedelta(days=90)),
            },
        )

        response = auth_client.get("/subscriptions")
        assert response.status_code == 200
        data = response.json()
        totals = data["totals_by_currency"]
        assert len(totals) == 1
        # Quarterly: 30.00 / 3 = 10.00 monthly equivalent
        assert totals[0]["total"] == pytest.approx(30.00, rel=0.01)
        assert totals[0]["monthly_equivalent"] == pytest.approx(10.00, rel=0.01)


# =============================================================================
# Response Format Tests
# =============================================================================


class TestListResponseFormat:
    """Tests for the new list response format."""

    def test_list_returns_paginated_response(self, auth_client):
        """Should return new paginated response format."""
        auth_client.post(
            "/subscriptions",
            json={
                "name": "Test",
                "cost": 10.00,
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )

        response = auth_client.get("/subscriptions")
        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "items" in data
        assert "total_count" in data
        assert "offset" in data
        assert "limit" in data
        assert "totals_by_currency" in data

        assert isinstance(data["items"], list)
        assert isinstance(data["totals_by_currency"], list)

    def test_list_empty_returns_paginated_response(self, auth_client):
        """Should return paginated response even when empty."""
        response = auth_client.get("/subscriptions")
        assert response.status_code == 200
        data = response.json()

        assert data["items"] == []
        assert data["total_count"] == 0
        assert data["totals_by_currency"] == []


# =============================================================================
# Cancel Subscription Tests
# =============================================================================


class TestCancelSubscription:
    """Tests for POST /subscriptions/{id}/cancel endpoint."""

    def test_cancel_subscription_success(self, auth_client):
        """Should cancel subscription and return 200."""
        # Create subscription
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

        # Cancel subscription
        response = auth_client.post(f"/subscriptions/{subscription_id}/cancel")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"
        assert data["cancelled_at"] is not None

    def test_cancel_sets_status_and_timestamps(self, auth_client, db_session):
        """Should set status to cancelled and record cancelled_at timestamp."""
        from app.models.subscription import Subscription

        # Create subscription
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

        # Cancel subscription
        response = auth_client.post(f"/subscriptions/{subscription_id}/cancel")
        assert response.status_code == 200

        # Verify database state
        subscription = db_session.query(Subscription).filter(
            Subscription.id == subscription_id
        ).first()
        assert subscription.status == "cancelled"
        assert subscription.cancelled_at is not None

    def test_cancel_with_reason(self, auth_client):
        """Should store cancellation reason."""
        # Create subscription
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

        # Cancel with reason
        response = auth_client.post(
            f"/subscriptions/{subscription_id}/cancel",
            json={"reason": "Too expensive"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["cancellation_reason"] == "Too expensive"

    def test_cancel_with_effective_date(self, auth_client):
        """Should store cancellation effective date."""
        # Create subscription
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
        effective_date = str(date.today() + timedelta(days=15))

        # Cancel with effective date
        response = auth_client.post(
            f"/subscriptions/{subscription_id}/cancel",
            json={"effective_date": effective_date},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["cancellation_effective_date"] == effective_date

    def test_cancel_already_cancelled_returns_400(self, auth_client):
        """Should return 400 when subscription is already cancelled."""
        # Create subscription
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

        # Cancel once
        auth_client.post(f"/subscriptions/{subscription_id}/cancel")

        # Try to cancel again
        response = auth_client.post(f"/subscriptions/{subscription_id}/cancel")
        assert response.status_code == 400
        assert "already cancelled" in response.json()["detail"].lower()

    def test_cancel_not_found_returns_404(self, auth_client):
        """Should return 404 when subscription doesn't exist."""
        response = auth_client.post("/subscriptions/9999/cancel")
        assert response.status_code == 404

    def test_cancel_other_users_subscription_returns_404(self, auth_client, db_session):
        """Should return 404 when trying to cancel another user's subscription."""
        from app.auth import hash_password
        from app.models.subscription import Subscription
        from app.models.user import User

        # Create another user with a subscription
        other_user = User(
            email="cancel_other@example.com",
            hashed_password=hash_password("password123"),
        )
        db_session.add(other_user)
        db_session.commit()
        db_session.refresh(other_user)

        other_subscription = Subscription(
            user_id=other_user.id,
            name="Other's Netflix",
            cost=15.99,
            currency="USD",
            billing_cycle="monthly",
            next_billing_date=date.today() + timedelta(days=30),
        )
        db_session.add(other_subscription)
        db_session.commit()
        db_session.refresh(other_subscription)

        # Try to cancel other user's subscription
        response = auth_client.post(f"/subscriptions/{other_subscription.id}/cancel")
        assert response.status_code == 404

    def test_cancelled_excluded_from_active_list(self, auth_client):
        """Should not show cancelled subscriptions in default list (active only)."""
        # Create two subscriptions
        create_response = auth_client.post(
            "/subscriptions",
            json={
                "name": "Netflix",
                "cost": 15.99,
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )
        netflix_id = create_response.json()["id"]

        auth_client.post(
            "/subscriptions",
            json={
                "name": "Spotify",
                "cost": 9.99,
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )

        # Cancel Netflix
        auth_client.post(f"/subscriptions/{netflix_id}/cancel")

        # List should only show Spotify (default is active)
        response = auth_client.get("/subscriptions")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["name"] == "Spotify"

    def test_cancelled_included_when_status_filter_cancelled(self, auth_client):
        """Should show cancelled subscriptions when status=cancelled."""
        # Create subscription and cancel it
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

        # List with status=cancelled
        response = auth_client.get("/subscriptions?status=cancelled")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["status"] == "cancelled"

    def test_list_with_status_all(self, auth_client):
        """Should show all subscriptions when status=all."""
        # Create two subscriptions
        create_response = auth_client.post(
            "/subscriptions",
            json={
                "name": "Netflix",
                "cost": 15.99,
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )
        netflix_id = create_response.json()["id"]

        auth_client.post(
            "/subscriptions",
            json={
                "name": "Spotify",
                "cost": 9.99,
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )

        # Cancel Netflix
        auth_client.post(f"/subscriptions/{netflix_id}/cancel")

        # List with status=all should show both
        response = auth_client.get("/subscriptions?status=all")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2

    def test_cancel_returns_estimated_savings(self, auth_client):
        """Should return estimated savings in cancellation response."""
        # Create subscription
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

        # Cancel subscription
        response = auth_client.post(f"/subscriptions/{subscription_id}/cancel")
        assert response.status_code == 200
        data = response.json()
        assert "estimated_savings" in data
        assert data["estimated_savings"]["currency"] == "USD"
        assert data["estimated_savings"]["monthly_amount"] == pytest.approx(15.99, rel=0.01)

    def test_cancel_deleted_subscription_returns_404(self, auth_client):
        """Should return 404 when trying to cancel a deleted subscription."""
        # Create subscription
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

        # Delete it
        auth_client.delete(f"/subscriptions/{subscription_id}")

        # Try to cancel
        response = auth_client.post(f"/subscriptions/{subscription_id}/cancel")
        assert response.status_code == 404


# =============================================================================
# Reactivate Subscription Tests
# =============================================================================


class TestReactivateSubscription:
    """Tests for POST /subscriptions/{id}/reactivate endpoint."""

    def test_reactivate_cancelled_subscription(self, auth_client):
        """Should reactivate a cancelled subscription."""
        # Create and cancel subscription
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

        # Reactivate
        response = auth_client.post(f"/subscriptions/{subscription_id}/reactivate")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "active"

    def test_reactivate_clears_cancellation_fields(self, auth_client, db_session):
        """Should clear cancelled_at, cancellation_reason, and effective_date."""
        from app.models.subscription import Subscription

        # Create and cancel subscription
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
        auth_client.post(
            f"/subscriptions/{subscription_id}/cancel",
            json={"reason": "Too expensive"},
        )

        # Reactivate
        response = auth_client.post(f"/subscriptions/{subscription_id}/reactivate")
        assert response.status_code == 200

        # Verify database state
        subscription = db_session.query(Subscription).filter(
            Subscription.id == subscription_id
        ).first()
        assert subscription.status == "active"
        assert subscription.cancelled_at is None
        assert subscription.cancellation_reason is None
        assert subscription.cancellation_effective_date is None

    def test_reactivate_with_new_billing_date(self, auth_client):
        """Should set new billing date when provided."""
        # Create and cancel subscription
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

        # Reactivate with new billing date
        new_date = str(date.today() + timedelta(days=60))
        response = auth_client.post(
            f"/subscriptions/{subscription_id}/reactivate",
            json={"next_billing_date": new_date},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["next_billing_date"] == new_date

    def test_reactivate_active_returns_400(self, auth_client):
        """Should return 400 when subscription is already active."""
        # Create subscription (already active)
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

        # Try to reactivate
        response = auth_client.post(f"/subscriptions/{subscription_id}/reactivate")
        assert response.status_code == 400
        assert "not cancelled" in response.json()["detail"].lower()

    def test_reactivate_not_found_returns_404(self, auth_client):
        """Should return 404 when subscription doesn't exist."""
        response = auth_client.post("/subscriptions/9999/reactivate")
        assert response.status_code == 404

    def test_reactivate_other_users_subscription_returns_404(self, auth_client, db_session):
        """Should return 404 when trying to reactivate another user's subscription."""
        from app.auth import hash_password
        from app.models.subscription import Subscription, utc_now
        from app.models.user import User

        # Create another user with a cancelled subscription
        other_user = User(
            email="reactivate_other@example.com",
            hashed_password=hash_password("password123"),
        )
        db_session.add(other_user)
        db_session.commit()
        db_session.refresh(other_user)

        other_subscription = Subscription(
            user_id=other_user.id,
            name="Other's Netflix",
            cost=15.99,
            currency="USD",
            billing_cycle="monthly",
            next_billing_date=date.today() + timedelta(days=30),
            status="cancelled",
            cancelled_at=utc_now(),
        )
        db_session.add(other_subscription)
        db_session.commit()
        db_session.refresh(other_subscription)

        # Try to reactivate other user's subscription
        response = auth_client.post(f"/subscriptions/{other_subscription.id}/reactivate")
        assert response.status_code == 404

    def test_reactivate_appears_in_active_list(self, auth_client):
        """Should show reactivated subscription in active list."""
        # Create and cancel subscription
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

        # Verify not in active list
        response = auth_client.get("/subscriptions")
        assert len(response.json()["items"]) == 0

        # Reactivate
        auth_client.post(f"/subscriptions/{subscription_id}/reactivate")

        # Verify in active list
        response = auth_client.get("/subscriptions")
        assert len(response.json()["items"]) == 1
        assert response.json()["items"][0]["id"] == subscription_id


# =============================================================================
# Savings Summary Tests
# =============================================================================


class TestSavingsSummary:
    """Tests for GET /subscriptions/savings endpoint."""

    def test_get_savings_empty(self, auth_client):
        """Should return empty savings when no cancelled subscriptions."""
        response = auth_client.get("/subscriptions/savings")
        assert response.status_code == 200
        data = response.json()
        assert data["savings_by_currency"] == []
        assert data["cancelled_count"] == 0

    def test_get_savings_single_cancelled(self, auth_client):
        """Should calculate savings for a single cancelled subscription."""
        # Create and cancel subscription
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

        response = auth_client.get("/subscriptions/savings")
        assert response.status_code == 200
        data = response.json()
        assert data["cancelled_count"] == 1
        assert len(data["savings_by_currency"]) == 1
        assert data["savings_by_currency"][0]["currency"] == "USD"
        assert data["savings_by_currency"][0]["monthly_amount"] == pytest.approx(15.99, rel=0.01)

    def test_get_savings_multiple_currencies(self, auth_client):
        """Should group savings by currency."""
        # Create and cancel USD subscription
        create_response = auth_client.post(
            "/subscriptions",
            json={
                "name": "Netflix",
                "cost": 15.99,
                "currency": "USD",
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )
        auth_client.post(f"/subscriptions/{create_response.json()['id']}/cancel")

        # Create and cancel EUR subscription
        create_response = auth_client.post(
            "/subscriptions",
            json={
                "name": "Spotify",
                "cost": 9.99,
                "currency": "EUR",
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )
        auth_client.post(f"/subscriptions/{create_response.json()['id']}/cancel")

        response = auth_client.get("/subscriptions/savings")
        assert response.status_code == 200
        data = response.json()
        assert data["cancelled_count"] == 2
        assert len(data["savings_by_currency"]) == 2

        currencies = [s["currency"] for s in data["savings_by_currency"]]
        assert "USD" in currencies
        assert "EUR" in currencies

    def test_savings_excludes_free_trials(self, auth_client, db_session):
        """Should not include free trial subscriptions in savings."""
        from app.models.subscription import Subscription, utc_now

        # Create a normal cancelled subscription
        create_response = auth_client.post(
            "/subscriptions",
            json={
                "name": "Netflix",
                "cost": 15.99,
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )
        auth_client.post(f"/subscriptions/{create_response.json()['id']}/cancel")

        # Create a free trial cancelled subscription directly in DB
        # (since there's no API to set was_free_trial)
        free_trial_sub = Subscription(
            user_id=1,  # auth_client user
            name="Free Trial",
            cost=9.99,
            currency="USD",
            billing_cycle="monthly",
            next_billing_date=date.today() + timedelta(days=30),
            status="cancelled",
            cancelled_at=utc_now(),
            was_free_trial=True,
        )
        db_session.add(free_trial_sub)
        db_session.commit()

        response = auth_client.get("/subscriptions/savings")
        assert response.status_code == 200
        data = response.json()
        # Should only count Netflix (non-free-trial)
        assert data["cancelled_count"] == 1
        assert data["savings_by_currency"][0]["monthly_amount"] == pytest.approx(15.99, rel=0.01)

    def test_savings_excludes_other_users(self, auth_client, db_session):
        """Should only show savings for current user's subscriptions."""
        from app.auth import hash_password
        from app.models.subscription import Subscription, utc_now
        from app.models.user import User

        # Create and cancel current user's subscription
        create_response = auth_client.post(
            "/subscriptions",
            json={
                "name": "Netflix",
                "cost": 15.99,
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=30)),
            },
        )
        auth_client.post(f"/subscriptions/{create_response.json()['id']}/cancel")

        # Create another user with a cancelled subscription
        other_user = User(
            email="savings_other@example.com",
            hashed_password=hash_password("password123"),
        )
        db_session.add(other_user)
        db_session.commit()
        db_session.refresh(other_user)

        other_subscription = Subscription(
            user_id=other_user.id,
            name="Other's Netflix",
            cost=99.99,
            currency="USD",
            billing_cycle="monthly",
            next_billing_date=date.today() + timedelta(days=30),
            status="cancelled",
            cancelled_at=utc_now(),
        )
        db_session.add(other_subscription)
        db_session.commit()

        response = auth_client.get("/subscriptions/savings")
        assert response.status_code == 200
        data = response.json()
        # Should only count current user's subscription
        assert data["cancelled_count"] == 1
        assert data["savings_by_currency"][0]["monthly_amount"] == pytest.approx(15.99, rel=0.01)

    def test_savings_billing_cycle_conversion(self, auth_client):
        """Should convert different billing cycles to monthly equivalent."""
        # Create and cancel yearly subscription
        create_response = auth_client.post(
            "/subscriptions",
            json={
                "name": "Annual Sub",
                "cost": 120.00,
                "billing_cycle": "yearly",
                "next_billing_date": str(date.today() + timedelta(days=365)),
            },
        )
        auth_client.post(f"/subscriptions/{create_response.json()['id']}/cancel")

        response = auth_client.get("/subscriptions/savings")
        assert response.status_code == 200
        data = response.json()
        # 120/12 = 10.00 monthly
        assert data["savings_by_currency"][0]["monthly_amount"] == pytest.approx(10.00, rel=0.01)
