# Folio

A self-hosted investment tracking platform for managing portfolios, analyzing performance, and tracking financial goals.

> **Disclaimer:** This is a personal vibe-coded project and my second public attempt at vibe coding. The current implementation may not reflect best practices in architecture or code design, that's intentional for now. A refactor is planned in the coming weeks to address that, given that my intentions for this project is to make use of it as my own portfolio tracking tool.

## Features

**Authentication**
- Open self-registration
- JWT access tokens (15 min) + refresh tokens (7 days) delivered via HTTP-only cookies
- Token rotation with family-based reuse detection
- All data scoped to the authenticated user

**Portfolio Management**
- Multi-portfolio support with trade history (buy, sell, dividend, fee)
- Holdings tracking with live market data via yfinance
- Asset classes: stocks, ETFs, crypto, and cash
- CSV import with column mapping, validation, and error reporting
- Multi-currency support with automatic FX conversion

**Analytics**
- Time-weighted return (TWR) and money-weighted return (MWR)
- Asset allocation breakdown by class and sector
- Portfolio performance history and contribution charts

**Goal Tracking**
- Financial goals with target dates and expected return inputs
- FIRE projection calculations
- Visual progress tracking

## Preview

[folio-demo.webm](https://github.com/user-attachments/assets/bb43d330-5571-4a6c-aeb7-e9ac58a1e26a)

## Stack

| Layer    | Technology                        |
|----------|-----------------------------------|
| Frontend | SvelteKit, TypeScript, Tailwind, shadcn-svelte, bits-ui |
| Backend  | FastAPI, SQLAlchemy (async)       |
| Database | PostgreSQL                        |
| Data     | yfinance, tiingo, ngnmarket       |
| Infra    | Docker, Docker Compose            |

## Getting Started

**Requirements:** Docker and Docker Compose.

```bash
git clone https://github.com/aybruhm/folio.git
cd folio
make setup
```

### Running in Production

If you just want to run Folio locally for personal use, pull the pre-built images from GHCR and start the stack.

**First-time setup** — create your environment files from the provided examples:

```bash
make prod-setup
```

Open `api/.env.prod` and `web/.env.local` and fill in your values (database credentials, API URL, `SECRET_KEY`, etc.), then:

```bash
make prod-pull
make prod-up
make prod-migrate
```

Optionally seed the database with a demo portfolio (stocks, crypto, and cash positions):

```bash
make prod-seed
```

Once running:

| Service  | URL                        |
|----------|----------------------------|
| Frontend | http://localhost:3000      |
| API      | http://localhost:8000      |
| API Docs | http://localhost:8000/docs |

### Running for Development

If you want to contribute or run the app with hot reload, use the dev stack instead. This builds images locally from source:

```bash
make up
make db-migrate
```

Optionally seed demo data:

```bash
make db-seed
```

## Make Commands

### Production

| Command              | Description                             |
|----------------------|-----------------------------------------|
| `make prod-setup`    | Create production `.env` files from examples |
| `make prod-up`       | Start production services               |
| `make prod-down`     | Stop production services                |
| `make prod-restart`  | Restart production services             |
| `make prod-logs`     | Stream production logs                  |
| `make prod-migrate`  | Run database migrations in production   |
| `make prod-seed`     | Seed production database with demo data |
| `make prod-health`   | Check production service health         |
| `make prod-pull`     | Pull latest images from GHCR            |

### Development Infrastructure

| Command        | Description                        |
|----------------|------------------------------------|
| `make setup`   | Create `.env` files from examples  |
| `make up`      | Start all services                 |
| `make down`    | Stop all services                  |
| `make restart` | Restart all services               |
| `make logs`    | Stream logs from all services      |
| `make health`  | Check service health status        |
| `make clean`   | Remove containers and prune system |

### Database

| Command           | Description                        |
|-------------------|------------------------------------|
| `make db-migrate` | Run pending Alembic migrations     |
| `make db-seed`    | Seed demo portfolio data           |
| `make db-reset`   | Drop and recreate schema           |
| `make db-shell`   | Open PostgreSQL shell              |

### Development

| Command           | Description                        |
|-------------------|------------------------------------|
| `make api-shell`  | Shell into the API container       |
| `make api-lint`   | Lint Python code                   |
| `make api-format` | Format with black and isort        |
| `make api-test`   | Run API tests                      |
| `make web-shell`  | Shell into the web container       |
| `make web-lint`   | Lint TypeScript/Svelte code        |
| `make web-build`  | Build the production frontend      |

## Breaking Changes

### v1.2.0 — Authentication

All API endpoints now require authentication. Existing deployments must run migrations before restarting:

```bash
# Production
make prod-migrate

# Development
make db-migrate
```

A `SECRET_KEY` environment variable is now required in `api/.env` / `api/.env.prod`. Generate one with:

```bash
openssl rand -hex 32
```

The demo seed user (`demo@folio.local` / `demo1234`) owns the seeded portfolio. After seeding, register your own account and create a new portfolio to get started.

## What's Next

- **Refactor**: improve code patterns, architecture, and design decisions across the stack

## License

[GNU GPL v2](LICENSE)
