"""Tests for reminder endpoints and notification preferences."""

from datetime import date, datetime, timedelta, timezone

import pytest


# =============================================================================
# Upcoming Subscriptions Tests
# =============================================================================


class TestUpcomingSubscriptions:
    """Tests for GET /subscriptions/upcoming endpoint."""

    def test_upcoming_empty(self, auth_client):
        """Should return empty list when no upcoming subscriptions."""
        response = auth_client.get("/subscriptions/upcoming")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total_count"] == 0

    def test_upcoming_within_days(self, auth_client):
        """Should return subscriptions renewing within specified days."""
        # Create subscription renewing in 5 days
        auth_client.post(
            "/subscriptions",
            json={
                "name": "Netflix",
                "cost": 15.99,
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=5)),
            },
        )

        response = auth_client.get("/subscriptions/upcoming?days=7")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["name"] == "Netflix"
        assert data["items"][0]["days_until_renewal"] == 5

    def test_upcoming_excludes_cancelled(self, auth_client):
        """Should not include cancelled subscriptions."""
        # Create and cancel subscription
        create_response = auth_client.post(
            "/subscriptions",
            json={
                "name": "Netflix",
                "cost": 15.99,
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=5)),
            },
        )
        subscription_id = create_response.json()["id"]
        auth_client.post(f"/subscriptions/{subscription_id}/cancel")

        response = auth_client.get("/subscriptions/upcoming?days=7")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total_count"] == 0

    def test_upcoming_sorted_by_date(self, auth_client):
        """Should sort by next billing date ascending."""
        # Create subscriptions with different dates
        auth_client.post(
            "/subscriptions",
            json={
                "name": "Later",
                "cost": 10.00,
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=6)),
            },
        )
        auth_client.post(
            "/subscriptions",
            json={
                "name": "Sooner",
                "cost": 10.00,
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=3)),
            },
        )

        response = auth_client.get("/subscriptions/upcoming?days=7")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["items"][0]["name"] == "Sooner"
        assert data["items"][1]["name"] == "Later"

    def test_upcoming_excludes_outside_range(self, auth_client):
        """Should not include subscriptions outside the specified days range."""
        # Create subscription renewing in 10 days
        auth_client.post(
            "/subscriptions",
            json={
                "name": "Netflix",
                "cost": 15.99,
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=10)),
            },
        )

        response = auth_client.get("/subscriptions/upcoming?days=7")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []

    def test_upcoming_different_days_parameter(self, auth_client):
        """Should respect different days parameter."""
        # Create subscription renewing in 20 days
        auth_client.post(
            "/subscriptions",
            json={
                "name": "Netflix",
                "cost": 15.99,
                "billing_cycle": "monthly",
                "next_billing_date": str(date.today() + timedelta(days=20)),
            },
        )

        # Not in 7 days
        response = auth_client.get("/subscriptions/upcoming?days=7")
        assert len(response.json()["items"]) == 0

        # But in 30 days
        response = auth_client.get("/subscriptions/upcoming?days=30")
        assert len(response.json()["items"]) == 1

    def test_upcoming_requires_auth(self, client):
        """Should return 401 when not authenticated."""
        response = client.get("/subscriptions/upcoming")
        assert response.status_code == 401


# =============================================================================
# Notification Preferences Tests
# =============================================================================


class TestNotificationPreferences:
    """Tests for user notification preferences endpoints."""

    def test_get_user_profile_with_preferences(self, auth_client):
        """Should return user profile with notification preferences."""
        response = auth_client.get("/users/me")
        assert response.status_code == 200
        data = response.json()
        assert "email_notifications_enabled" in data
        assert "push_notifications_enabled" in data
        assert "timezone" in data
        # Check defaults
        assert data["email_notifications_enabled"] is True
        assert data["push_notifications_enabled"] is True
        assert data["timezone"] == "UTC"

    def test_update_notification_preferences(self, auth_client):
        """Should update notification preferences."""
        response = auth_client.patch(
            "/users/me/notifications",
            json={
                "email_notifications_enabled": False,
                "push_notifications_enabled": False,
                "timezone": "America/New_York",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email_notifications_enabled"] is False
        assert data["push_notifications_enabled"] is False
        assert data["timezone"] == "America/New_York"

    def test_update_invalid_timezone_returns_422(self, auth_client):
        """Should return 422 for invalid timezone."""
        response = auth_client.patch(
            "/users/me/notifications",
            json={"timezone": "Invalid/Timezone"},
        )
        assert response.status_code == 422

    def test_partial_update_preserves_other_fields(self, auth_client):
        """Should preserve unset fields during partial update."""
        # First update to set custom values
        auth_client.patch(
            "/users/me/notifications",
            json={
                "email_notifications_enabled": False,
                "timezone": "Europe/London",
            },
        )

        # Partial update only push notifications
        response = auth_client.patch(
            "/users/me/notifications",
            json={"push_notifications_enabled": False},
        )
        assert response.status_code == 200
        data = response.json()
        # Should preserve previous values
        assert data["email_notifications_enabled"] is False
        assert data["timezone"] == "Europe/London"
        assert data["push_notifications_enabled"] is False

    def test_get_user_profile_requires_auth(self, client):
        """Should return 401 when not authenticated."""
        response = client.get("/users/me")
        assert response.status_code == 401

    def test_update_preferences_requires_auth(self, client):
        """Should return 401 when not authenticated."""
        response = client.patch(
            "/users/me/notifications",
            json={"email_notifications_enabled": False},
        )
        assert response.status_code == 401


# =============================================================================
# Reminder History Tests
# =============================================================================


class TestReminderHistory:
    """Tests for GET /reminders endpoint."""

    def test_reminder_history_empty(self, auth_client):
        """Should return empty list when no reminders."""
        response = auth_client.get("/reminders")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total_count"] == 0

    def test_reminder_history_paginated(self, auth_client, db_session):
        """Should support pagination for reminder history."""
        from app.models.reminder_log import ReminderLog

        # Create some reminder logs directly in DB
        user_id = auth_client.test_user.id
        for i in range(5):
            log = ReminderLog(
                user_id=user_id,
                subscription_id=1,
                reminder_type="email",
                scheduled_for=datetime.now(timezone.utc),
                status="sent",
            )
            db_session.add(log)
        db_session.commit()

        # Get first page
        response = auth_client.get("/reminders?limit=2&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total_count"] == 5

        # Get second page
        response = auth_client.get("/reminders?limit=2&offset=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total_count"] == 5

    def test_reminder_history_requires_auth(self, client):
        """Should return 401 when not authenticated."""
        response = client.get("/reminders")
        assert response.status_code == 401

    def test_reminder_history_only_shows_own(self, auth_client, db_session):
        """Should only show reminders for current user."""
        from app.auth import hash_password
        from app.models.reminder_log import ReminderLog
        from app.models.user import User

        # Create another user with a reminder
        other_user = User(
            email="other_reminder@example.com",
            hashed_password=hash_password("password123"),
        )
        db_session.add(other_user)
        db_session.commit()
        db_session.refresh(other_user)

        # Create reminder for other user
        other_log = ReminderLog(
            user_id=other_user.id,
            subscription_id=1,
            reminder_type="email",
            scheduled_for=datetime.now(timezone.utc),
            status="sent",
        )
        db_session.add(other_log)

        # Create reminder for current user
        my_log = ReminderLog(
            user_id=auth_client.test_user.id,
            subscription_id=1,
            reminder_type="email",
            scheduled_for=datetime.now(timezone.utc),
            status="sent",
        )
        db_session.add(my_log)
        db_session.commit()

        response = auth_client.get("/reminders")
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1
        assert data["items"][0]["user_id"] == auth_client.test_user.id
