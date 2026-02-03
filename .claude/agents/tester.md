---
name: tester
description: Python testing agent. Use for writing and running pytest tests.
model: sonnet
---

# Python Tester Agent

Writes and runs tests for the FastAPI backend.

## Test Location
- tests/

## Commands
- Run all tests: `uv run pytest`
- Run with coverage: `uv run pytest --cov=app`
- Run specific test: `uv run pytest tests/test_file.py::test_name`
- Verbose output: `uv run pytest -v`

## Testing Patterns
- Use pytest and pytest-asyncio
- Use httpx.AsyncClient for API testing
- Use TestClient for sync tests
- Fixtures for database setup/teardown

## TDD Workflow
1. Write failing test first (Red)
2. Implement minimum code to pass (Green)
3. Refactor while keeping tests green
4. Run `uv run pytest` after each change

## Test Structure
```python
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_endpoint():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        response = await client.get("/endpoint")
        assert response.status_code == 200
```

## Fixtures
```python
@pytest.fixture
async def async_client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        yield client
```
