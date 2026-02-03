# Hackathon API - FastAPI Backend

Python FastAPI backend with PostgreSQL database.

## Commands
- Run dev server: `uv run fastapi dev`
- Run tests: `uv run pytest`
- Sync dependencies: `uv sync`
- Add dependency: `uv add <package>`

## Skills (Commands)
Available in `.claude/skills/`:
- `/feature` - Build new API features with TDD
- `/test` - Run pytest tests

## Agents
Available in `.claude/agents/`:
- `python-coder` - FastAPI development
- `tester` - Write and run pytest tests
- `reviewer` - Code review before commits
- `debugger` - Investigate API issues

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

## Database
- PostgreSQL via Docker Compose
- SQLAlchemy 2.0 ORM
- Connection: postgresql://postgres:postgres@localhost:5432/hackathon

## API Docs
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Adding Features
1. Create model in app/models/
2. Create schemas in app/schemas/
3. Create router in app/routers/
4. Register router in app/main.py
