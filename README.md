# Folio

A self-hosted investment tracker. Record your trades, see what you own and how it has performed, compare yourself against the market, and plan toward your goals. Your data stays on your own machine.

> **Disclaimer:** This is a personal vibe-coded project and my second public attempt at vibe coding. The current implementation may not reflect best practices in architecture or code design, that's intentional for now. A refactor is planned in the coming weeks to address that, given that my intentions for this project is to make use of it as my own portfolio tracking tool.

## Preview

[folio-tour.webm](https://github.com/user-attachments/assets/4f254d53-49a3-4b02-8f92-55e6c3c12a83)

## Features

**Portfolios and trades**
- Several portfolios per user, each with its own base currency, and an archive to hide the ones you no longer use
- Buy, sell, dividend and fee trades, with quantities up to 8 decimal places (handy for crypto)
- Add trades one at a time, several at once, or import a CSV with column mapping, validation and error reporting
- Trade history you can search, filter by type and date range, and page through
- A trade that fails because your session expired is kept in the browser and offered back for review after you sign in, instead of being lost
- Stocks, ETFs, crypto and cash, in any mix of currencies, with dated FX conversion

**Performance**
- Time-weighted (TWR) and money-weighted (MWR) return, for one portfolio or all of them combined
- Timeframes: YTD, 3M, 1Y, 3Y, 5Y and All
- Asset allocation by class and sector, performance history and contribution charts

**Benchmarking**
- Compare a portfolio, or all of them, with an index, ETF or crypto over YTD, 3M, 6M, 1Y, 3Y, 5Y or 10Y
- Pick from a built-in list (S&P 500, Nasdaq-100, FTSE 100, VOO, QQQ, Bitcoin, NGX All-Share and more) or type any ticker
- Both lines are in your chosen currency, using each day's exchange rate, and money you add or withdraw is not counted as performance
- Results are cached for 35 minutes

**Goals**
- Financial goals with target dates and expected returns, FIRE projections and progress tracking

**Accounts and security**
- Self-registration, which can be switched off
- 15-minute access tokens and 7-day refresh tokens in HTTP-only cookies, with rotation and reuse detection
- Every record is scoped to the signed-in user

**Quality of life**
- A footer in the sidebar shows the running version and tells you when a newer release is available on GitHub
- Works offline for what you have already loaded, with a local cache in the browser
- Light and dark themes, and an installable PWA

## Stack

| Layer    | Technology                                                       |
|----------|------------------------------------------------------------------|
| Frontend | SvelteKit 3, Svelte 5, TypeScript, Tailwind CSS, shadcn-svelte, bits-ui |
| Backend  | Python 3.13, FastAPI, SQLAlchemy (async), Alembic                 |
| Database | PostgreSQL                                                       |
| Cache    | Valkey (Redis-compatible)                                        |
| Data     | yfinance, Tiingo, NGNMarket, NGXPulse, TradingView               |
| Infra    | Docker, Docker Compose                                           |

## Quick start

**Requirements:** Docker and Docker Compose.

### Run it for personal use

This pulls the pre-built images from GHCR. PostgreSQL and Valkey are included.

```bash
git clone https://github.com/aybruhm/folio.git
cd folio
make prod-setup      # creates api/.env.prod
cp web/.env.prod.example web/.env.prod
```

Open `api/.env.prod` and `web/.env.prod` and set at least `SECRET_KEY` (use the same value in both). The examples already use the right Docker hostnames for the database and cache. Then:

```bash
make prod-pull
make prod-up
make prod-migrate
make prod-seed       # optional: a demo portfolio with stocks, crypto and cash
```

| Service  | URL                        |
|----------|----------------------------|
| Frontend | http://localhost:3000      |
| API      | http://localhost:8010      |
| API docs | http://localhost:8010/docs |

Database credentials can be overridden with `DB_USER`, `DB_PASSWORD`, `DB_NAME` and `DB_PORT`; the ports with `WEB_PORT` and `API_PORT`.

### Run it for development

This builds images from source and reloads on change.

```bash
make setup           # creates api/.env and web/.env.local from the examples
make up
make db-migrate
make db-seed         # optional demo data
```

| Service  | URL                       |
|----------|---------------------------|
| Frontend | http://localhost:3000     |
| API      | http://localhost:8000     |
| API docs | http://localhost:8000/docs |

## Configuration

The examples (`api/.env.example`, `api/.env.prod.example`, `web/.env.local.example`, `web/.env.prod.example`) list every setting. The ones you are most likely to touch:

| Setting | Where | What it does |
|---------|-------|--------------|
| `SECRET_KEY` | api and web | Signs auth tokens. Required, and must match in both. |
| `ENABLE_REGISTRATION` / `PUBLIC_ENABLE_REGISTRATION` | api / web | Set both to `false` to close sign-ups once your account exists. |
| `ALLOWED_ORIGINS` | api | Origins the browser may call the API from. |
| `PUBLIC_API_BASE_URL` / `PRIVATE_API_URL` | web | Where the browser, and the server-side renderer, reach the API. |
| `MARKET_DATA_CACHE_TTL`, `YFINANCE_*_CACHE_TTL` | api | How long prices are cached in Valkey. The web `PUBLIC_*_CACHE_TTL` values should match. |
| `BENCHMARK_CACHE_TTL` | api | How long a finished benchmark comparison is cached. Default 2100 seconds (35 minutes). |
| `PUBLIC_UPDATE_CHECK` | web | Set to `false` to stop checking GitHub for new releases. |
| `SCHEDULER_ENABLED` | api | Turns on the background price refresh jobs. |

### Market data providers

yfinance works with no setup. The others are optional and need an API key in `api/.env`:

| Provider  | Key needed | Good for |
|-----------|------------|----------|
| yfinance  | No | Global stocks, ETFs, indices, crypto and FX. The default, and the only source of FX rates. |
| Tiingo    | `TIINGO_API_KEY` | US stocks and ETFs |
| NGNMarket | `NGNMARKET_API_KEY` | Nigerian equities, indices and the NGN exchange rate |
| NGXPulse  | `NGXPULSE_API_KEY` | NGX stocks, ETFs and index history (limited to 100 requests a day) |
| TradingView | `RAPID_API_KEY` | Extra exchange coverage, through RapidAPI |

Each asset records which provider prices it, so you can mix them in one portfolio. Benchmarks use yfinance, NGXPulse or NGNMarket; NGX indices are in the built-in list and need the matching key.

## Make commands

Run `make help` for the full list. The common ones:

**Production**

| Command             | Description                                  |
|---------------------|----------------------------------------------|
| `make prod-setup`   | Create the production `.env` files           |
| `make prod-pull`    | Pull the latest images from GHCR             |
| `make prod-up`      | Start the production stack                   |
| `make prod-down`    | Stop it                                      |
| `make prod-restart` | Restart it                                   |
| `make prod-logs`    | Stream the logs                              |
| `make prod-migrate` | Run database migrations                      |
| `make prod-seed`    | Seed the demo portfolio                      |
| `make prod-health`  | Check service health                         |

**Development**

| Command          | Description                          |
|------------------|--------------------------------------|
| `make setup`     | Create the dev `.env` files from the examples |
| `make up`        | Start all services                   |
| `make down`      | Stop all services                    |
| `make restart`   | Restart all services                 |
| `make logs`      | Stream logs (`logs-api`, `logs-web`, `logs-db` for one service) |
| `make health`    | Check service health                 |
| `make status`    | Show running containers              |
| `make clean`     | Remove containers and prune          |
| `make reset`     | Clean, set up and start from scratch |

**Database**

| Command           | Description                       |
|-------------------|-----------------------------------|
| `make db-migrate` | Run pending Alembic migrations    |
| `make db-seed`    | Seed demo portfolio data          |
| `make db-reset`   | Drop and recreate the schema (asks first) |
| `make db-shell`   | Open a PostgreSQL shell           |
| `make backup`     | Dump the database to `backups/`   |

**Code**

| Command           | Description                       |
|-------------------|-----------------------------------|
| `make api-shell`  | Shell into the API container      |
| `make api-test`   | Run the API tests                 |
| `make api-lint`   | Lint the Python code              |
| `make api-format` | Format with black and isort       |
| `make web-shell`  | Shell into the web container      |
| `make web-lint`   | Lint the TypeScript and Svelte code |
| `make web-build`  | Build the production frontend     |

## Upgrading

```bash
git pull
make prod-pull
make prod-up
make prod-migrate
```

Back up first with `make backup`. The sidebar footer shows the version you are running and links to the release notes when a newer one exists.

## Project layout

```
api/    FastAPI backend: adapters (HTTP, persistence, market data), application, domain, migrations, tests
web/    SvelteKit frontend: routes, components, stores, API client
infra/  Helper scripts
static/ Images used in the docs
```

## License

[GNU GPL v2](LICENSE)
