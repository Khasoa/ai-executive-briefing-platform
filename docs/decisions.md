# Architectural Decisions

This document records the key architectural decisions made for Relay's backend and the reasoning behind each choice.

---

## ADR-001: FastAPI as the Web Framework

**Decision:** Use FastAPI for the backend API.

**Why:**
- Native async support for future I/O-bound integrations (Gmail, Calendar APIs)
- Automatic OpenAPI documentation at `/docs`
- Pydantic v2 integration for request/response validation
- Dependency injection system maps cleanly to our service layer
- Large ecosystem and strong Railway deployment support

**Alternatives considered:** Django REST Framework (heavier, more opinionated), Flask (no built-in validation or DI).

---

## ADR-002: Modular Monolith over Microservices

**Decision:** Single FastAPI application with internal module boundaries.

**Why:**
- v0.1 is a small team building an MVP — microservices add operational overhead without benefit
- Clear folder structure (`routes/`, `services/`, `integrations/`) provides separation of concerns
- Can extract services into independent deployments later if needed
- Simpler Railway deployment (one service, one database)

**Alternatives considered:** Microservices from day one (premature), serverless functions (cold start issues, harder local dev).

---

## ADR-003: Service Layer Pattern

**Decision:** Routes delegate to service classes. No business logic in route handlers.

**Why:**
- Services can be tested independently of HTTP layer
- Mock data and real integrations swap without changing routes
- Each domain (inbox, CRM, calendar) has a clear owner
- Matches how the frontend thinks about features (one service per page)

**Example:**
```python
# Route (thin)
@router.get("/inbox")
def get_inbox(db: Session = Depends(get_db)):
    return InboxService(db).get_inbox()

# Service (business logic)
class InboxService:
    def get_inbox(self):
        # v0.1: return mock data
        # v0.3: query Email table + Gmail sync
```

---

## ADR-004: Mock Data in v0.1

**Decision:** Services return mock data from a centralized `mock_data.py` module. Database models exist but are not yet populated by API calls.

**Why:**
- Frontend can connect to the backend immediately without waiting for integrations
- Mock data exactly matches the frontend's existing data shapes
- Database schema is ready for when integrations arrive
- Avoids building a complex seeding system before it's needed

**Trade-off:** API responses don't persist or reflect database state yet. Acceptable for v0.1.

---

## ADR-005: SQLAlchemy 2.0 with Typed Models

**Decision:** Use SQLAlchemy 2.0 declarative style with `Mapped` type annotations.

**Why:**
- Modern Python typing support (mypy-compatible)
- `mapped_column` is the current recommended pattern
- JSONB and ARRAY types for flexible fields (brief sections, tags, integration config)
- Alembic integration for migration management

**Alternatives considered:** Raw SQL (no ORM benefits), SQLModel (less mature ecosystem).

---

## ADR-006: PostgreSQL on Railway

**Decision:** PostgreSQL as the primary database, hosted on Railway.

**Why:**
- JSONB support for flexible schema fields (daily brief sections, integration config)
- ARRAY type for tags and attendees
- Railway provides managed PostgreSQL with automatic `DATABASE_URL`
- Production-grade reliability for a SaaS product
- Strong SQLAlchemy and Alembic support

**Alternatives considered:** SQLite (not suitable for production SaaS), MongoDB (relational data fits better in SQL).

---

## ADR-007: Integration Module Pattern

**Decision:** Each external service gets a dedicated module in `app/integrations/`. Services never call third-party APIs directly.

**Why:**
- Isolates API changes — if Gmail's API changes, only `gmail.py` needs updating
- Consistent internal interface regardless of provider
- Easy to mock integrations in tests
- Clear ownership for each integration

**Structure:**
```
integrations/gmail.py       → used by InboxService
integrations/google_calendar.py → used by CalendarService
integrations/gohighlevel.py → used by CRMService
integrations/openai.py        → used by AssistantService, OverviewService
```

---

## ADR-008: Pydantic Schemas Separate from ORM Models

**Decision:** API response shapes are defined in `app/schemas/`, separate from `app/models/`.

**Why:**
- API contract is independent of database schema
- Frontend field names (camelCase like `executiveSummary`) differ from database columns (snake_case)
- Response schemas can combine data from multiple models
- Prevents accidental exposure of internal database fields

---

## ADR-009: No Authentication in v0.1

**Decision:** Skip authentication for the initial release. User model includes `email` for future auth.

**Why:**
- Single-user demo doesn't require auth complexity
- User model is already designed for multi-tenant auth later
- Avoids blocking frontend integration on auth flows
- JWT auth planned for v1.0

**Risk:** API is open in v0.1. Mitigated by deploying only in development/staging.

---

## ADR-010: Centralized Settings via pydantic-settings

**Decision:** All configuration loaded from environment variables through a `Settings` class.

**Why:**
- Railway injects config via environment variables
- `.env` file for local development
- Type-safe settings with defaults
- Single source of truth for database URL, CORS origins, log level

---

## ADR-011: Alembic for Database Migrations

**Decision:** Use Alembic for all schema changes.

**Why:**
- Industry standard for SQLAlchemy projects
- Version-controlled migration history
- `upgrade`/`downgrade` support for rollbacks
- Railway deploy hooks can run `alembic upgrade head`

---

## ADR-012: Request Logging Middleware

**Decision:** Custom middleware logs method, path, status code, and duration for every request.

**Why:**
- Essential for debugging in development
- Foundation for production monitoring
- Lightweight — no external dependencies (Datadog, etc.) needed yet
- Structured log format for future log aggregation

---

## ADR-013: CORS Configured via Environment

**Decision:** CORS allowed origins are configurable via `CORS_ORIGINS` environment variable.

**Why:**
- Development: `http://localhost:5173` (Vite dev server)
- Production: actual frontend domain
- Comma-separated string parsed into list
- No code changes needed between environments

---

## ADR-014: Flat Route Structure

**Decision:** Top-level routes (`/overview`, `/calendar`, `/inbox`) without an `/api` prefix.

**Why:**
- Matches the user's specified endpoint structure
- Simpler for frontend consumption
- Can add `/api/v1` prefix later if versioning is needed
- Health check at `/health` is a common convention

---

## Summary

These decisions prioritize **simplicity, modularity, and progressive enhancement**. The backend starts as a mock-data API with a production-ready schema and service architecture, then gains real integrations one at a time without structural changes.
