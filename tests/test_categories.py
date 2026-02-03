"""Tests for Category Management API endpoints."""

import pytest


class TestCategoryList:
    """Tests for GET /categories endpoint."""

    def test_list_returns_system_categories(self, auth_client):
        """System categories should be returned for all users."""
        response = auth_client.get("/categories")
        assert response.status_code == 200

        data = response.json()
        assert "items" in data
        assert "total_count" in data
        assert "custom_count" in data
        assert "max_custom_allowed" in data

        # Should have 7 system categories
        system_categories = [c for c in data["items"] if c["is_system"]]
        assert len(system_categories) == 7

        # Check system category names
        system_names = {c["name"] for c in system_categories}
        expected_names = {"Entertainment", "Productivity", "Health", "Finance", "Education", "Shopping", "Other"}
        assert system_names == expected_names

    def test_list_returns_user_custom_categories(self, auth_client):
        """User's custom categories should be included in the list."""
        # Create a custom category
        create_response = auth_client.post(
            "/categories",
            json={"name": "My Custom", "icon": "star.fill", "color": "#FF0000"},
        )
        assert create_response.status_code == 201

        # List categories
        response = auth_client.get("/categories")
        assert response.status_code == 200

        data = response.json()
        custom_categories = [c for c in data["items"] if not c["is_system"]]
        assert len(custom_categories) == 1
        assert custom_categories[0]["name"] == "My Custom"
        assert data["custom_count"] == 1

    def test_list_excludes_other_users_categories(self, auth_client, second_auth_client, db_session):
        """Custom categories should only be visible to their owner."""
        # First user creates a category
        auth_client.post(
            "/categories",
            json={"name": "User1 Category", "icon": "star.fill", "color": "#FF0000"},
        )

        # Second user creates a category
        second_auth_client.post(
            "/categories",
            json={"name": "User2 Category", "icon": "heart.fill", "color": "#00FF00"},
        )

        # First user should only see their custom category
        response1 = auth_client.get("/categories")
        custom1 = [c for c in response1.json()["items"] if not c["is_system"]]
        assert len(custom1) == 1
        assert custom1[0]["name"] == "User1 Category"

        # Second user should only see their custom category
        response2 = second_auth_client.get("/categories")
        custom2 = [c for c in response2.json()["items"] if not c["is_system"]]
        assert len(custom2) == 1
        assert custom2[0]["name"] == "User2 Category"

    def test_list_includes_subscription_count(self, auth_client, db_session):
        """Categories should include the count of subscriptions assigned to them."""
        # Get the Entertainment category ID
        response = auth_client.get("/categories")
        categories = response.json()["items"]
        entertainment = next(c for c in categories if c["name"] == "Entertainment")

        # Initially no subscriptions
        assert entertainment["subscription_count"] == 0

    def test_list_sorted_by_display_order(self, auth_client):
        """Categories should be sorted by display_order."""
        response = auth_client.get("/categories")
        data = response.json()

        # System categories should be ordered: Entertainment, Productivity, Health, Finance, Education, Shopping, Other
        system_categories = [c for c in data["items"] if c["is_system"]]
        expected_order = ["Entertainment", "Productivity", "Health", "Finance", "Education", "Shopping", "Other"]
        actual_order = [c["name"] for c in system_categories]
        assert actual_order == expected_order

    def test_list_requires_authentication(self, client):
        """Listing categories requires authentication."""
        response = client.get("/categories")
        assert response.status_code == 401


class TestCategoryCreate:
    """Tests for POST /categories endpoint."""

    def test_create_custom_category(self, auth_client):
        """Should create a custom category with valid data."""
        response = auth_client.post(
            "/categories",
            json={"name": "Gaming", "icon": "gamecontroller.fill", "color": "#9C27B0"},
        )
        assert response.status_code == 201

        data = response.json()
        assert data["name"] == "Gaming"
        assert data["icon"] == "gamecontroller.fill"
        assert data["color"] == "#9C27B0"
        assert data["is_system"] is False
        assert "id" in data

    def test_reject_invalid_sf_symbol(self, auth_client):
        """Should reject invalid SF Symbol icons."""
        response = auth_client.post(
            "/categories",
            json={"name": "Test", "icon": "invalid.icon.name", "color": "#FF0000"},
        )
        assert response.status_code == 422
        assert "Invalid SF Symbol" in response.json()["detail"][0]["msg"]

    def test_reject_invalid_hex_color(self, auth_client):
        """Should reject invalid hex color codes."""
        # Missing #
        response = auth_client.post(
            "/categories",
            json={"name": "Test", "icon": "star.fill", "color": "FF0000"},
        )
        assert response.status_code == 422
        assert "Invalid hex color" in response.json()["detail"][0]["msg"]

        # Too short
        response = auth_client.post(
            "/categories",
            json={"name": "Test", "icon": "star.fill", "color": "#F00"},
        )
        assert response.status_code == 422

        # Invalid characters
        response = auth_client.post(
            "/categories",
            json={"name": "Test", "icon": "star.fill", "color": "#GGGGGG"},
        )
        assert response.status_code == 422

    def test_reject_duplicate_name_case_insensitive(self, auth_client):
        """Should reject duplicate category names (case-insensitive)."""
        # Create first category
        auth_client.post(
            "/categories",
            json={"name": "My Category", "icon": "star.fill", "color": "#FF0000"},
        )

        # Try to create with same name
        response = auth_client.post(
            "/categories",
            json={"name": "My Category", "icon": "heart.fill", "color": "#00FF00"},
        )
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"].lower()

        # Try to create with different case
        response = auth_client.post(
            "/categories",
            json={"name": "my category", "icon": "heart.fill", "color": "#00FF00"},
        )
        assert response.status_code == 409

    def test_reject_when_max_20_reached(self, auth_client):
        """Should reject creation when user has 20 custom categories."""
        # Create 20 categories
        for i in range(20):
            response = auth_client.post(
                "/categories",
                json={"name": f"Category {i}", "icon": "star.fill", "color": "#FF0000"},
            )
            assert response.status_code == 201, f"Failed to create category {i}"

        # Try to create 21st
        response = auth_client.post(
            "/categories",
            json={"name": "Category 21", "icon": "star.fill", "color": "#FF0000"},
        )
        assert response.status_code == 400
        assert "maximum" in response.json()["detail"].lower()

    def test_create_requires_authentication(self, client):
        """Creating categories requires authentication."""
        response = client.post(
            "/categories",
            json={"name": "Test", "icon": "star.fill", "color": "#FF0000"},
        )
        assert response.status_code == 401

    def test_reject_empty_name(self, auth_client):
        """Should reject empty category names."""
        response = auth_client.post(
            "/categories",
            json={"name": "", "icon": "star.fill", "color": "#FF0000"},
        )
        assert response.status_code == 422

    def test_reject_name_too_long(self, auth_client):
        """Should reject category names longer than 50 characters."""
        response = auth_client.post(
            "/categories",
            json={"name": "A" * 51, "icon": "star.fill", "color": "#FF0000"},
        )
        assert response.status_code == 422

    def test_cannot_create_with_system_category_name(self, auth_client):
        """Should reject creating custom category with same name as system category."""
        response = auth_client.post(
            "/categories",
            json={"name": "Entertainment", "icon": "star.fill", "color": "#FF0000"},
        )
        assert response.status_code == 409


class TestCategoryGet:
    """Tests for GET /categories/{id} endpoint."""

    def test_get_system_category(self, auth_client):
        """Should get a system category by ID."""
        # First list to get an ID
        list_response = auth_client.get("/categories")
        entertainment = next(c for c in list_response.json()["items"] if c["name"] == "Entertainment")

        response = auth_client.get(f"/categories/{entertainment['id']}")
        assert response.status_code == 200
        assert response.json()["name"] == "Entertainment"
        assert response.json()["is_system"] is True

    def test_get_custom_category(self, auth_client):
        """Should get a custom category by ID."""
        # Create a category
        create_response = auth_client.post(
            "/categories",
            json={"name": "My Category", "icon": "star.fill", "color": "#FF0000"},
        )
        category_id = create_response.json()["id"]

        response = auth_client.get(f"/categories/{category_id}")
        assert response.status_code == 200
        assert response.json()["name"] == "My Category"

    def test_get_nonexistent_category(self, auth_client):
        """Should return 404 for nonexistent category."""
        response = auth_client.get("/categories/99999")
        assert response.status_code == 404

    def test_cannot_get_other_users_category(self, auth_client, second_auth_client):
        """Should not be able to get another user's custom category."""
        # First user creates a category
        create_response = auth_client.post(
            "/categories",
            json={"name": "Private", "icon": "star.fill", "color": "#FF0000"},
        )
        category_id = create_response.json()["id"]

        # Second user tries to get it
        response = second_auth_client.get(f"/categories/{category_id}")
        assert response.status_code == 404


class TestCategoryUpdate:
    """Tests for PUT /categories/{id} endpoint."""

    def test_update_custom_category(self, auth_client):
        """Should update a custom category."""
        # Create a category
        create_response = auth_client.post(
            "/categories",
            json={"name": "Original", "icon": "star.fill", "color": "#FF0000"},
        )
        category_id = create_response.json()["id"]

        # Update it
        response = auth_client.put(
            f"/categories/{category_id}",
            json={"name": "Updated", "icon": "heart.fill", "color": "#00FF00"},
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Updated"
        assert response.json()["icon"] == "heart.fill"
        assert response.json()["color"] == "#00FF00"

    def test_partial_update(self, auth_client):
        """Should allow partial updates."""
        # Create a category
        create_response = auth_client.post(
            "/categories",
            json={"name": "Original", "icon": "star.fill", "color": "#FF0000"},
        )
        category_id = create_response.json()["id"]

        # Update only name
        response = auth_client.put(
            f"/categories/{category_id}",
            json={"name": "New Name"},
        )
        assert response.status_code == 200
        assert response.json()["name"] == "New Name"
        assert response.json()["icon"] == "star.fill"  # Unchanged
        assert response.json()["color"] == "#FF0000"  # Unchanged

    def test_update_system_category_icon_color(self, auth_client):
        """Should allow updating icon and color of system categories."""
        # Get a system category
        list_response = auth_client.get("/categories")
        entertainment = next(c for c in list_response.json()["items"] if c["name"] == "Entertainment")

        # Update icon and color
        response = auth_client.put(
            f"/categories/{entertainment['id']}",
            json={"icon": "gamecontroller.fill", "color": "#FF00FF"},
        )
        assert response.status_code == 200
        assert response.json()["icon"] == "gamecontroller.fill"
        assert response.json()["color"] == "#FF00FF"

    def test_cannot_rename_system_category(self, auth_client):
        """Should not allow renaming system categories."""
        # Get a system category
        list_response = auth_client.get("/categories")
        entertainment = next(c for c in list_response.json()["items"] if c["name"] == "Entertainment")

        # Try to rename
        response = auth_client.put(
            f"/categories/{entertainment['id']}",
            json={"name": "My Entertainment"},
        )
        assert response.status_code == 400
        assert "system category" in response.json()["detail"].lower()

    def test_cannot_update_other_users_category(self, auth_client, second_auth_client):
        """Should not be able to update another user's category."""
        # First user creates a category
        create_response = auth_client.post(
            "/categories",
            json={"name": "Private", "icon": "star.fill", "color": "#FF0000"},
        )
        category_id = create_response.json()["id"]

        # Second user tries to update it
        response = second_auth_client.put(
            f"/categories/{category_id}",
            json={"name": "Hacked"},
        )
        assert response.status_code == 404

    def test_update_rejects_invalid_icon(self, auth_client):
        """Should reject invalid SF Symbol on update."""
        create_response = auth_client.post(
            "/categories",
            json={"name": "Test", "icon": "star.fill", "color": "#FF0000"},
        )
        category_id = create_response.json()["id"]

        response = auth_client.put(
            f"/categories/{category_id}",
            json={"icon": "invalid.icon"},
        )
        assert response.status_code == 422

    def test_update_rejects_duplicate_name(self, auth_client):
        """Should reject renaming to an existing name."""
        # Create two categories
        auth_client.post(
            "/categories",
            json={"name": "Category A", "icon": "star.fill", "color": "#FF0000"},
        )
        create_response = auth_client.post(
            "/categories",
            json={"name": "Category B", "icon": "heart.fill", "color": "#00FF00"},
        )
        category_b_id = create_response.json()["id"]

        # Try to rename B to A
        response = auth_client.put(
            f"/categories/{category_b_id}",
            json={"name": "Category A"},
        )
        assert response.status_code == 409


class TestCategoryDelete:
    """Tests for DELETE /categories/{id} endpoint."""

    def test_delete_custom_category(self, auth_client):
        """Should delete a custom category."""
        # Create a category
        create_response = auth_client.post(
            "/categories",
            json={"name": "To Delete", "icon": "star.fill", "color": "#FF0000"},
        )
        category_id = create_response.json()["id"]

        # Delete it
        response = auth_client.delete(f"/categories/{category_id}")
        assert response.status_code == 204

        # Verify it's gone
        get_response = auth_client.get(f"/categories/{category_id}")
        assert get_response.status_code == 404

    def test_cannot_delete_system_category(self, auth_client):
        """Should not allow deleting system categories."""
        # Get a system category
        list_response = auth_client.get("/categories")
        entertainment = next(c for c in list_response.json()["items"] if c["name"] == "Entertainment")

        response = auth_client.delete(f"/categories/{entertainment['id']}")
        assert response.status_code == 400
        assert "system category" in response.json()["detail"].lower()

    def test_cannot_delete_other_users_category(self, auth_client, second_auth_client):
        """Should not be able to delete another user's category."""
        # First user creates a category
        create_response = auth_client.post(
            "/categories",
            json={"name": "Private", "icon": "star.fill", "color": "#FF0000"},
        )
        category_id = create_response.json()["id"]

        # Second user tries to delete it
        response = second_auth_client.delete(f"/categories/{category_id}")
        assert response.status_code == 404

        # Verify it still exists for first user
        get_response = auth_client.get(f"/categories/{category_id}")
        assert get_response.status_code == 200

    def test_delete_nonexistent_category(self, auth_client):
        """Should return 404 for nonexistent category."""
        response = auth_client.delete("/categories/99999")
        assert response.status_code == 404

    def test_delete_requires_authentication(self, client):
        """Deleting categories requires authentication."""
        response = client.delete("/categories/1")
        assert response.status_code == 401


class TestAvailableIcons:
    """Tests for GET /categories/icons endpoint."""

    def test_list_available_icons(self, auth_client):
        """Should return list of available SF Symbols."""
        response = auth_client.get("/categories/icons")
        assert response.status_code == 200

        data = response.json()
        assert "icons" in data
        assert len(data["icons"]) > 0
        assert "star.fill" in data["icons"]
        assert "heart.fill" in data["icons"]
