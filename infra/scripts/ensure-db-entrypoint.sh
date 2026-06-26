#!/bin/sh
# ---------------------------------------------------------------------------
# Custom PostgreSQL entrypoint wrapper
#
# Starts PostgreSQL via the original entrypoint, waits for readiness, then
# ensures $POSTGRES_DB exists (creating it if missing).  Finally, brings
# PostgreSQL back to the foreground so the container stays alive.
#
# All POSTGRES_* environment variables are injected by docker-compose.
# ---------------------------------------------------------------------------
set -e

# Start the original PostgreSQL entrypoint in the background.
# We capture its PID so we can bring it to the foreground later.
/usr/local/bin/docker-entrypoint.sh postgres &
POSTGRES_PID=$!

# Wait until PostgreSQL is accepting connections.
echo "Waiting for PostgreSQL to become ready..."
until pg_isready -U "${POSTGRES_USER:-folio}" -d postgres > /dev/null 2>&1; do
    sleep 2
done
echo "PostgreSQL is ready."

# Resolve the target database name (same default as docker-compose.prod.yml).
DB_NAME="${POSTGRES_DB:-folio_prod}"
DB_USER="${POSTGRES_USER:-folio}"

# Check whether the database already exists.
EXISTS=$(psql -U "$DB_USER" -d postgres -tAc \
    "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME';" 2>/dev/null || true)

if [ "$EXISTS" = "1" ]; then
    echo "Database '$DB_NAME' already exists. Nothing to do."
else
    echo "Database '$DB_NAME' does not exist. Creating..."
    createdb -U "$DB_USER" "$DB_NAME"
    echo "Database '$DB_NAME' created successfully."
fi

# Bring PostgreSQL back to the foreground.
# If postgres exits, the container exits (as expected).
wait $POSTGRES_PID
