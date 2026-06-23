# Nebula Chess

Nebula Chess is a premium online chess platform starter kit with:

- FastAPI backend with authoritative real-time game state
- WebSocket multiplayer rooms, spectators, reconnect, rematch, invite links
- PostgreSQL schema and migration-ready SQL
- JWT auth with refresh-token rotation
- React + TypeScript frontend with a premium UI, drag-and-drop board, routing, and analysis views
- Redis Pub/Sub support for horizontal scaling
- Stockfish integration for AI and game analysis
- Anti-cheat scoring, audit trail, and health/metrics endpoints
- Docker Compose for local one-command startup

This repo is intentionally structured as a production-ready MVP foundation. It is fully runnable, and designed to be extended into a larger chess platform.

## Project tree

```text
nebula-chess/
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── migrations/0001_initial.sql
│   └── app/
│       ├── main.py
│       ├── models.py
│       ├── schemas.py
│       ├── deps.py
│       ├── core/
│       ├── db/
│       ├── services/
│       └── api/routes/
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.ts
│   ├── index.html
│   └── src/
├── docker-compose.yml
├── .env.example
└── nginx/nginx.conf
```

## Quick start

### With Docker

```bash
cp .env.example .env
docker compose up --build
```

Frontend: `http://localhost:5173`  
Backend API: `http://localhost:8000`  
Docs: `http://localhost:8000/docs`

### Local backend only

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e .
export DATABASE_URL=sqlite+aiosqlite:///./nebula.db
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Local frontend only

```bash
cd frontend
npm install
npm run dev
```

Set `VITE_API_BASE_URL=http://localhost:8000` in `frontend/.env`.

## Environment

See `.env.example` for all variables.

Important variables:

- `DATABASE_URL`
- `REDIS_URL`
- `JWT_SECRET`
- `ACCESS_TOKEN_EXPIRE_MINUTES`
- `REFRESH_TOKEN_EXPIRE_DAYS`
- `STOCKFISH_PATH`
- `CORS_ORIGINS`

## Database

The backend supports PostgreSQL by default. The initial schema is in `backend/migrations/0001_initial.sql`.

To create the DB locally with Docker:

```bash
docker compose exec db psql -U nebula -d nebula -f /docker-entrypoint-initdb.d/0001_initial.sql
```

The app uses SQLAlchemy ORM models and is migration-ready. You can adopt Alembic directly from the current schema.

## Multiplayer test flow

1. Open two browser windows.
2. Register or login two users.
3. Create a new game in one window.
4. Copy the invite link.
5. Join from the second window.
6. Make moves. The server validates legality and broadcasts real-time updates.

## Game features included

- 1v1 online chess
- Spectator mode
- Rematch
- Invite links
- Live chat
- Move list and PGN
- FEN import/export
- AI opponent support
- Daily puzzle-ready endpoint hooks
- Leaderboards
- Profiles and statistics
- Anti-cheat suspicion scoring and review flow

## Scaling notes

- The game engine is authoritative on the backend.
- Redis Pub/Sub enables multiple workers to stay in sync.
- For production, terminate TLS and proxy WebSockets through Nginx.
- Keep `X-Forwarded-For` headers and proper sticky session strategy if you use in-memory room optimization.
- Horizontal scaling works best when the DB and Redis are shared and the room state is hydrated from persistence on reconnect.

## Metrics

- `GET /metrics` exposes Prometheus metrics
- `GET /healthz` for health checks
- `GET /readyz` for readiness checks

## Load testing

Suggested starting point:

```bash
k6 run scripts/loadtest.js
```

Focus on:
- WebSocket concurrency
- Move validation throughput
- Redis fanout latency
- Reconnect behavior under worker restarts

## Security design

- JWT access + refresh token rotation
- Argon2 password hashing
- Server-side move validation
- CORS/CSP/security headers
- Rate limiting middleware
- Audit event logging
- Anti-tamper move request validation

## Notes on stockfish

The Docker image installs Stockfish. On systems without it, the service falls back to a safe heuristic and the app still runs.

## License

Internal demo / starter kit.
