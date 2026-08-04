# Architectural Decisions

Key decisions behind Briefly and the reasoning for each.

---

## ADR-001: The Morning Brief is the product

**Decision:** One page is the output; every other page supports it.

**Why:**
- An executive tool that does eight things well is still eight things to check every morning
- A single artefact can be read in five minutes, printed, or forwarded to a chief of staff
- It gives every feature a test: does this make tomorrow's brief better?

**Consequence:** Pages that did not serve the brief — Projects, Research, Calendar grid, generic AI chat — were removed rather than redesigned.

---

## ADR-002: Recommend, never act

**Decision:** No endpoint sends email, moves a deal or accepts a meeting. Integration scopes are read-only.

**Why:**
- Trust is the binding constraint for an AI product with access to a founder's inbox and pipeline
- A wrong summary costs a minute; a wrong send costs a relationship
- Draft-and-approve is a useful workflow on its own

**How it shows up:** `suggestedResponse` on every email, a "Draft — not sent" label on generated text, and `autoApproveActions` in settings that exists only to be permanently disabled.

---

## ADR-003: Cite every AI statement

**Decision:** Recommendations, risks and Ask Briefly reports name the systems they came from.

**Why:**
- An executive cannot act on a claim they cannot verify
- Citations expose the failure mode where the model is confident about a system it never read
- Once generation is retrieval-backed, citations fall out of which records were retrieved

**Implementation:** `Source` and `CitationSchema` in `schemas/common.py`; `SourceChip` renders them identically everywhere.

---

## ADR-004: One urgency vocabulary

**Decision:** `critical`, `high`, `medium`, `low` across every domain — email priority, risk severity, deal risk, recommendation priority.

**Why:**
- Three different colour schemes for "urgent" teaches the reader nothing and slows scanning
- Lists can be sorted by consequence with one shared comparator
- The API enforces it via a shared `Literal`, so the UI never encounters an unmapped value

**Implementation:** `schemas/common.py` on the backend, `lib/signals.js` on the frontend.

---

## ADR-005: JavaScript, not TypeScript

**Decision:** The frontend is plain JavaScript with JSX.

**Why:**
- Explicitly specified for this product
- Pydantic already defines and validates the API contract at the boundary that matters
- `jsconfig.json` preserves path aliases and editor intelligence

**Trade-off:** No compile-time guarantee that a component matches an API response. Mitigated by keeping every fetch in `services/briefly.js` and rendering directly from responses, and by a smoke test that mounts each page against the live API.

---

## ADR-006: Pages hold no local copy of server data

**Decision:** Each page runs one `useApiQuery`. Mutations return the updated object and the page applies it via `setData`.

**Why:**
- Two copies of the truth drift; one does not
- Optimistic local state would have to replicate server rules (checklist progress, pipeline weighting)
- Keeps pages small enough to read in one screen

---

## ADR-007: Thin routes, fat services

**Decision:** Routes receive, inject the session, delegate and return. All logic lives in service classes.

**Why:**
- Services are testable without HTTP
- Swapping curated data for a database query or an integration touches one class
- Each domain has one obvious owner

```python
@router.get("", response_model=CRMResponse)
def get_pipeline(db: Session = Depends(get_db)) -> CRMResponse:
    return CRMService(db).get_pipeline()
```

---

## ADR-008: Curated data behind real service boundaries

**Decision:** Services read from `mock_data.py`, but only through the same methods that will later query the database.

**Why:**
- The frontend can be built and demonstrated end to end immediately
- Response shapes are proven against a real UI before an integration is written
- Computed values (weighted pipeline, prep counts, scheduled minutes) are calculated, not hardcoded, so they stay correct when the source changes

**Trade-off:** Mutations live in process memory and reset on restart. Acceptable while there is no persistence layer wired up.

---

## ADR-009: Schemas separate from ORM models

**Decision:** `app/schemas/` defines the API contract; `app/models/` defines storage.

**Why:**
- The frontend wants camelCase and flattened, composed objects; the database wants snake_case and normalised rows
- A response often spans several tables (a brief pulls from meetings, emails and opportunities)
- Prevents internal columns from leaking into the API

---

## ADR-010: Integration modules, never direct SDK calls

**Decision:** Each provider gets a module in `app/integrations/` exposing a consistent internal interface.

**Why:**
- A Gmail API change touches one file
- Integrations can be stubbed in tests
- Services stay readable — they express business rules, not HTTP plumbing

---

## ADR-011: Tailwind v4 theme tokens over a config file

**Decision:** Design tokens are CSS custom properties in `@theme` inside `src/index.css`.

**Why:**
- Tailwind v4's native approach; no `tailwind.config.js` to keep in sync
- Tokens are inspectable in the browser and reusable in plain CSS (print styles, scrollbars)
- Renaming a colour is one edit, and every utility follows

---

## ADR-012: The brief is a document, not a dashboard

**Decision:** The Morning Brief uses numbered sections, a serif face for prose, and a print stylesheet.

**Why:**
- Executives read reports; they scan dashboards. The brief is meant to be read
- Printing and presenting are real behaviours for a document that summarises a business day
- Visual separation from the rest of the app signals that this page is the output

---

## ADR-013: Flat routes, no `/api` prefix

**Decision:** `/overview`, `/inbox`, `/morning-brief` at the root; health at `/health`.

**Why:**
- Frontend and backend deploy separately, so there is no path collision to avoid
- Simpler client code
- A `/v1` prefix can be added when there is a second version to serve

---

## ADR-014: Configuration through pydantic-settings

**Decision:** All configuration loads from environment variables into a cached `Settings` object.

**Why:**
- Railway injects configuration as environment variables
- Type-safe with sensible defaults for local development
- One source of truth for database URL, CORS origins and log level
