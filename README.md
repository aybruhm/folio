# Folio - Self-Hosted Investment Tracking Platform

> A comprehensive, open-source investment tracking system for managing multiple portfolios, analyzing performance, and tracking financial goals.

**Status:** MVP Complete (80% of full roadmap) | Phases 1-9 Done | Production Ready

## Features

### Core Investment Management

✅ **Multi-Portfolio Support** - Organize holdings across multiple accounts
✅ **Trade Management** - Record buys, sells, dividends, and fees
✅ **Holdings Tracking** - Real-time holdings with market data integration
✅ **CSV Import** - Bulk import trades with preview, validation, and error reporting
✅ **Multi-Currency** - Track portfolios in any currency with automatic FX conversion

### Performance Analytics

✅ **Time-Weighted Return (TWR)** - Modified Dietz method independent of cash flows
✅ **Money-Weighted Return (MWR)** - IRR-based return accounting for cash flow timing
✅ **Asset Allocation** - Automatic breakdown by asset class and sector
✅ **Performance Charts** - Interactive visualizations of portfolio history
✅ **Timeframe Selection** - Analyze performance over YTD, 3M, 1Y, 3Y, 5Y, or all-time

### Goal Tracking

✅ **Financial Goals** - Set savings targets with target dates
✅ **FIRE Projections** - Calculate required returns and contribution amounts
✅ **Progress Tracking** - Visual progress bars and status indicators

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Node.js 18+ (for development)
- Python 3.12+ (for development)

### Run with Docker

```bash
git clone https://github.com/yourusername/folio.git
cd folio
cp .env.example .env
docker compose up -d
docker compose exec api alembic upgrade head
```

Then visit:
- **Frontend:** http://localhost:3000
- **API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs

## Documentation

- **[USER_GUIDE.md](docs/USER_GUIDE.md)** - How to use Folio
- **[API.md](docs/API.md)** - Complete API reference
- **[DEPLOYMENT.md](docs/DEPLOYMENT.md)** - Production deployment guide
- **[IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md)** - Full roadmap
- **[CODING_STANDARDS.md](docs/CODING_STANDARDS.md)** - Development guidelines

## Implementation Status

**80% Complete** (45/56 todos)

✅ Infrastructure, Backend, Frontend, Jobs, Error Handling, Documentation
⏳ Testing, Performance, Deployment finalization

See [IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md) for details.
