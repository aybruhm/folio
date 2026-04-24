.PHONY: help setup up down logs clean test lint format

help:
	@echo "Folio - Investment Tracking Platform"
	@echo ""
	@echo "Infrastructure Commands:"
	@echo "  make setup          Setup environment (.env files from examples)"
	@echo "  make up             Start all services (Docker Compose)"
	@echo "  make down           Stop all services"
	@echo "  make restart        Restart all services"
	@echo "  make logs           View logs from all services"
	@echo "  make logs-api       View API service logs"
	@echo "  make logs-web       View Web service logs"
	@echo "  make logs-db        View Database service logs"
	@echo ""
	@echo "Database Commands:"
	@echo "  make db-shell       Access PostgreSQL shell"
	@echo "  make db-reset       Reset database (drop and recreate)"
	@echo "  make db-migrate     Run database migrations"
	@echo "  make db-seed        Seed database with sample data"
	@echo ""
	@echo "API Commands:"
	@echo "  make api-shell      Access API container shell"
	@echo "  make api-lint       Lint Python code"
	@echo "  make api-format     Format Python code (black, isort)"
	@echo "  make api-test       Run API tests"
	@echo "  make api-repl       Start Python REPL in API container"
	@echo ""
	@echo "Web Commands:"
	@echo "  make web-shell      Access Web container shell"
	@echo "  make web-build      Build production frontend"
	@echo "  make web-lint       Lint TypeScript/Svelte code"
	@echo "  make web-test       Run frontend tests"
	@echo ""
	@echo "Utility Commands:"
	@echo "  make clean          Clean up containers and volumes"
	@echo "  make clean-hard     Remove all containers, volumes, and images"
	@echo "  make health         Check service health status"
	@echo "  make env            Generate .env files from examples"
	@echo "  make validate       Validate docker-compose configuration"
	@echo ""

# Setup & Environment
setup:
	@echo "Setting up environment..."
	@cp -n api/.env.example api/.env && echo "✓ Created api/.env" || echo "ℹ api/.env already exists"
	@cp -n web/.env.local.example web/.env.local && echo "✓ Created web/.env.local" || echo "ℹ web/.env.local already exists"
	@echo ""
	@echo "Setup complete! Next steps:"
	@echo "  1. Review and customize api/.env if needed"
	@echo "  2. Review and customize web/.env.local if needed"
	@echo "  3. Run 'make up' to start services"

env: setup

validate:
	@echo "Validating docker-compose configuration..."
	@which docker-compose > /dev/null || which docker > /dev/null && \
		(docker compose config > /dev/null && echo "✓ Configuration is valid" || echo "✗ Configuration is invalid") || \
		echo "✗ Docker/Docker Compose not found"

# Docker Compose Operations
up:
	@echo "Starting services..."
	@docker compose up -d
	@echo ""
	@echo "Services starting. Wait for health checks..."
	@sleep 3
	@make health

down:
	@echo "Stopping services..."
	@docker compose down
	@echo "✓ Services stopped"

restart:
	@echo "Restarting services..."
	@docker compose restart
	@echo "✓ Services restarted"

logs:
	@docker compose logs -f

logs-api:
	@docker compose logs -f api

logs-web:
	@docker compose logs -f web

logs-db:
	@docker compose logs -f db

health:
	@echo "Checking service health..."
	@echo ""
	@echo "Database:"
	@docker compose exec -T db pg_isready -U folio 2>/dev/null && echo "  ✓ PostgreSQL healthy" || echo "  ✗ PostgreSQL unhealthy"
	@echo ""
	@echo "API:"
	@curl -s http://localhost:8000/health > /dev/null && echo "  ✓ API healthy" || echo "  ✗ API unhealthy"
	@echo ""
	@echo "Web:"
	@curl -s http://localhost:3000 > /dev/null && echo "  ✓ Web healthy" || echo "  ✗ Web unhealthy"

# Database Operations
db-shell:
	@echo "Connecting to PostgreSQL..."
	@docker compose exec db psql -U folio -d folio

db-reset:
	@echo "WARNING: This will delete all data in the database!"
	@read -p "Continue? (y/n) " -n 1 -r; \
	echo ""; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker compose exec -T db psql -U folio -d folio -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;" && \
		docker compose exec api python -m alembic upgrade head && \
		echo "✓ Database reset and migrated"; \
	else \
		echo "Cancelled"; \
	fi

db-migrate:
	@echo "Running database migrations..."
	@docker compose exec api python -m alembic upgrade head
	@echo "✓ Migrations complete"

db-seed:
	@echo "Seeding database with sample data..."
	@docker compose exec api python -m infrastructure.db.seed
	@echo "✓ Database seeded"

# API Operations
api-shell:
	@echo "Accessing API container..."
	@docker compose exec api /bin/bash

api-lint:
	@echo "Linting Python code..."
	@docker compose exec api python -m flake8 api/
	@echo "✓ Linting complete"

api-format:
	@echo "Formatting Python code..."
	@docker compose exec api black api/
	@docker compose exec api isort api/
	@echo "✓ Formatting complete"

api-test:
	@echo "Running API tests..."
	@docker compose exec api python -m pytest
	@echo "✓ Tests complete"

api-repl:
	@echo "Starting Python REPL in API container..."
	@docker compose exec api python

# Web Operations
web-shell:
	@echo "Accessing Web container..."
	@docker compose exec web /bin/bash

web-build:
	@echo "Building production frontend..."
	@docker compose exec web npm run build
	@echo "✓ Build complete"

web-lint:
	@echo "Linting TypeScript/Svelte code..."
	@docker compose exec web npm run lint
	@echo "✓ Linting complete"

web-test:
	@echo "Running frontend tests..."
	@docker compose exec web npm test
	@echo "✓ Tests complete"

# Cleanup Operations
clean:
	@echo "Cleaning up containers and temporary files..."
	@docker compose down
	@docker system prune -f
	@echo "✓ Cleanup complete"

clean-hard:
	@echo "WARNING: This will remove all containers, volumes, and images!"
	@read -p "Continue? (y/n) " -n 1 -r; \
	echo ""; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker compose down -v; \
		docker system prune -af; \
		echo "✓ Hard cleanup complete"; \
	else \
		echo "Cancelled"; \
	fi

# Additional Utilities
reset: clean setup up
	@echo "✓ Full reset complete"

install-api-deps:
	@echo "Installing API dependencies..."
	@docker compose exec api pip install -r requirements.txt
	@echo "✓ Dependencies installed"

install-web-deps:
	@echo "Installing Web dependencies..."
	@docker compose exec web npm install
	@echo "✓ Dependencies installed"

status:
	@echo "Service Status:"
	@docker compose ps

backup:
	@echo "Backing up database..."
	@docker compose exec -T db pg_dump -U folio folio > backups/folio_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "✓ Backup created in backups/"

ps: status
