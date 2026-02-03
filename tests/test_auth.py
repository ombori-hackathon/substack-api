"""Tests for user registration endpoint."""
import pytest


class TestRegisterSuccess:
    """Test successful registration scenarios."""

    def test_register_success(self, client):
        """Valid registration returns 201 with user and token."""
        response = client.post(
            "/auth/register",
            json={
                "email": "test@example.com",
                "password": "SecurePass123!"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert "user" in data
        assert data["user"]["email"] == "test@example.com"
        assert "id" in data["user"]
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        # Password should not be returned
        assert "password" not in data["user"]
        assert "hashed_password" not in data["user"]


class TestRegisterDuplicate:
    """Test duplicate email handling."""

    def test_register_duplicate_email(self, client):
        """Registering with existing email returns 409."""
        # First registration
        client.post(
            "/auth/register",
            json={
                "email": "duplicate@example.com",
                "password": "SecurePass123!"
            }
        )

        # Second registration with same email
        response = client.post(
            "/auth/register",
            json={
                "email": "duplicate@example.com",
                "password": "DifferentPass456!"
            }
        )

        assert response.status_code == 409
        assert "email already registered" in response.json()["detail"].lower()


class TestRegisterValidation:
    """Test input validation for registration."""

    def test_register_invalid_email(self, client):
        """Invalid email format returns 422."""
        response = client.post(
            "/auth/register",
            json={
                "email": "not-an-email",
                "password": "SecurePass123!"
            }
        )

        assert response.status_code == 422

    def test_register_password_too_short(self, client):
        """Password shorter than 8 characters returns 422."""
        response = client.post(
            "/auth/register",
            json={
                "email": "test@example.com",
                "password": "Short1!"
            }
        )

        assert response.status_code == 422
        assert "8 characters" in response.json()["detail"][0]["msg"].lower()

    def test_register_password_no_number(self, client):
        """Password without a number returns 422."""
        response = client.post(
            "/auth/register",
            json={
                "email": "test@example.com",
                "password": "NoNumberHere!"
            }
        )

        assert response.status_code == 422
        assert "number" in response.json()["detail"][0]["msg"].lower()

    def test_register_password_no_special_char(self, client):
        """Password without a special character returns 422."""
        response = client.post(
            "/auth/register",
            json={
                "email": "test@example.com",
                "password": "NoSpecial123"
            }
        )

        assert response.status_code == 422
        assert "special" in response.json()["detail"][0]["msg"].lower()

    def test_register_empty_fields(self, client):
        """Empty email or password returns 422."""
        response = client.post(
            "/auth/register",
            json={
                "email": "",
                "password": ""
            }
        )

        assert response.status_code == 422


# === LOGIN TESTS ===


class TestLoginSuccess:
    """Test successful login scenarios."""

    def test_login_success(self, client):
        """Valid credentials return 200 with user and token."""
        # First register a user
        client.post(
            "/auth/register",
            json={
                "email": "login@example.com",
                "password": "SecurePass123!"
            }
        )

        # Then login
        response = client.post(
            "/auth/login",
            json={
                "email": "login@example.com",
                "password": "SecurePass123!"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "user" in data
        assert data["user"]["email"] == "login@example.com"
        assert "id" in data["user"]
        assert "access_token" in data
        assert data["token_type"] == "bearer"


class TestLoginFailure:
    """Test login failure scenarios."""

    def test_login_wrong_password(self, client):
        """Wrong password returns 401."""
        # First register a user
        client.post(
            "/auth/register",
            json={
                "email": "wrongpass@example.com",
                "password": "SecurePass123!"
            }
        )

        # Try to login with wrong password
        response = client.post(
            "/auth/login",
            json={
                "email": "wrongpass@example.com",
                "password": "WrongPassword123!"
            }
        )

        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()

    def test_login_nonexistent_user(self, client):
        """Nonexistent user returns 401 (same as wrong password for security)."""
        response = client.post(
            "/auth/login",
            json={
                "email": "nobody@example.com",
                "password": "SecurePass123!"
            }
        )

        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()


class TestLoginValidation:
    """Test login input validation."""

    def test_login_empty_fields(self, client):
        """Empty email or password returns 422."""
        response = client.post(
            "/auth/login",
            json={
                "email": "",
                "password": ""
            }
        )

        assert response.status_code == 422
