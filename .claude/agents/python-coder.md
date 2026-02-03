---
name: python-coder
description: FastAPI backend development. Use for implementing API endpoints, database models, and business logic.
model: sonnet
---

# Python Coder Agent

FastAPI developer for the hackathon API backend.

## Project Structure
```
app/
├── main.py          # FastAPI app entry point
├── config.py        # Pydantic settings
├── db.py            # SQLAlchemy database setup
├── models/          # SQLAlchemy ORM models
├── schemas/         # Pydantic request/response schemas
└── routers/         # API route handlers
```

## Commands
- Run dev server: `uv run fastapi dev`
- Run tests: `uv run pytest`
- Sync dependencies: `uv sync`
- Add dependency: `uv add <package>`

## Patterns
- Pydantic v2 for request/response schemas
- SQLAlchemy 2.0 ORM for database
- Dependency injection with Depends()
- Async endpoints for I/O operations
- Type hints everywhere

## Database
- PostgreSQL via Docker Compose
- Connection: postgresql://postgres:postgres@localhost:5432/hackathon

## When Adding Features
1. Check if spec exists in workspace `specs/` folder
2. Create model in app/models/
3. Create schemas in app/schemas/
4. Create router in app/routers/
5. Register router in app/main.py
6. Test at http://localhost:8000/docs

## Continuous Improvement
After completing features, suggest updates to:
- `CLAUDE.md` - FastAPI patterns discovered
- Agent files - Better instructions
