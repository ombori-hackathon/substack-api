import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import create_access_token, hash_password
from app.db import Base, get_db
from app.main import app
from app.models.user import User


@pytest.fixture
def db_session():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db_session):
    """Create a test client with database session override."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def auth_client(db_session):
    """Create a test client with an authenticated user."""
    # Create a test user
    test_user = User(
        email="test@example.com",
        hashed_password=hash_password("password123"),
    )
    db_session.add(test_user)
    db_session.commit()
    db_session.refresh(test_user)

    # Create access token (sub must be string)
    token = create_access_token(data={"sub": str(test_user.id)})

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        test_client.headers["Authorization"] = f"Bearer {token}"
        test_client.test_user = test_user  # Attach user for assertions
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def second_auth_client(db_session):
    """Create a test client with a second authenticated user (for isolation tests)."""
    # Create a second test user
    second_user = User(
        email="second@example.com",
        hashed_password=hash_password("password123"),
    )
    db_session.add(second_user)
    db_session.commit()
    db_session.refresh(second_user)

    # Create access token (sub must be string)
    token = create_access_token(data={"sub": str(second_user.id)})

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        test_client.headers["Authorization"] = f"Bearer {token}"
        test_client.test_user = second_user
        yield test_client
    app.dependency_overrides.clear()
