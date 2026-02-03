---
name: test
description: Run Python tests and report results.
user-invocable: true
allowed-tools: Bash, Read, Grep, Glob
---

# /test - Run Python Tests

Run tests for the FastAPI backend.

## Usage

```
/test              # Run all tests
/test <name>       # Run tests matching name
/test --cov        # Run with coverage
```

## Workflow

### Run Tests

```bash
# All tests
uv run pytest

# Specific test file
uv run pytest tests/test_file.py

# Specific test function
uv run pytest tests/test_file.py::test_function

# With coverage
uv run pytest --cov=app --cov-report=term-missing

# Verbose output
uv run pytest -v
```

### Interpret Results

- **All tests passed**: Report success with count
- **Tests failed**:
  1. Show which tests failed
  2. Show assertion errors
  3. Suggest fixes if obvious

### Common Issues

- **Database error**: Ensure PostgreSQL is running (`docker compose up -d`)
- **Import error**: Check module paths and __init__.py files
- **Async test fails**: Ensure @pytest.mark.asyncio decorator is present
- **422 errors in tests**: Request body doesn't match schema
