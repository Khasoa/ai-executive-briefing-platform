# Relay — AI Executive Partner

Relay is an AI-powered executive workspace that helps founders and executives manage their business from one place. It combines AI, automation, business intelligence, and operational support into a single command center.

## Repository Structure

```
ai-executive-partner/
├── src/                  # React frontend (Vite + TypeScript)
├── backend/              # FastAPI backend
├── docs/                 # Architecture and API documentation
├── automation/         # Workflow automations (future)
├── assets/               # Screenshots and demo assets
└── README.md
```

## Tech Stack

### Frontend
- React 19, TypeScript, Vite
- Tailwind CSS, shadcn/ui, Framer Motion

### Backend
- Python 3.12, FastAPI, SQLAlchemy 2.0
- Alembic, PostgreSQL, Pydantic v2

## Quick Start

### Frontend

```bash
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173).

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

### Connect Frontend to Backend

Set in the frontend `.env`:

```
VITE_API_URL=http://localhost:8000
```

Then replace direct `@/data/mock` imports with API calls.

## Health Check

```bash
curl http://localhost:8000/health
# {"status":"healthy"}
```

## Documentation

- [Architecture](docs/architecture.md)
- [API Reference](docs/api.md)
- [Roadmap](docs/roadmap.md)
- [Decisions](docs/decisions.md)
- [Backend README](backend/README.md)

## License

See [LICENSE](LICENSE).
