---
name: feature
description: Build a new API feature with TDD. Creates spec, writes tests first, then implements.
user-invocable: true
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
---

# /feature - API Feature Workflow

Build FastAPI features using test-driven development.

## Usage

```
/feature <brief description of what you want to build>
```

## Workflow

### Step 1: Understand the Feature

Ask the user:
1. **What should this endpoint do?** (one sentence)
2. **HTTP method and path?** (GET /items, POST /users, etc.)
3. **Request body structure?** (if POST/PUT/PATCH)
4. **Response structure?**
5. **Any database changes needed?**

### Step 2: Check for Existing Spec

Look for related spec in `../../specs/` (workspace specs folder).
If none exists, create one.

### Step 3: Enter Plan Mode

Use EnterPlanMode to design the implementation:

```markdown
# Feature: [Name]

## Summary
[One sentence description]

## API Endpoint
- Method: [GET/POST/PUT/DELETE]
- Path: [/path]
- Request Schema: { field: type }
- Response Schema: { field: type }

## Database Changes (if needed)
- New model: [ModelName]
- Fields: [list]

## Implementation Plan
1. [ ] Write failing tests
2. [ ] Create database model (if needed)
3. [ ] Create Pydantic schemas
4. [ ] Create router
5. [ ] Register router in main.py
6. [ ] Run tests
```

### Step 4: TDD Red Phase

1. Create test file: `tests/test_<feature>.py`
2. Write tests for new endpoint
3. Run `uv run pytest` - confirm FAILS (Red)

### Step 5: TDD Green Phase

1. Create model in `app/models/` (if needed)
2. Create schemas in `app/schemas/`
3. Create router in `app/routers/`
4. Register router in `app/main.py`
5. Run `uv run pytest` - should PASS (Green)

### Step 6: Verify

```bash
uv run pytest
uv run fastapi dev  # Test at /docs
```

### Step 7: Commit

```bash
git checkout -b feature/<name>
git add .
git commit -m "feat: <description>"
git push -u origin feature/<name>
gh pr create --title "feat: <description>" --body "Implements <feature>"
```
