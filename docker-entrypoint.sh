#!/bin/bash
set -e

# Function to wait for postgres
wait_for_postgres() {
    echo "Waiting for PostgreSQL..."
    until PGPASSWORD=$POSTGRES_PASSWORD psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c '\q'; do
        >&2 echo "Postgres is unavailable - sleeping"
        sleep 1
    done
    >&2 echo "Postgres is up - continuing"
}

# Function to wait for Redis
wait_for_redis() {
    echo "Waiting for Redis..."
    until redis-cli -h redis ping; do
        >&2 echo "Redis is unavailable - sleeping"
        sleep 1
    done
    >&2 echo "Redis is up - continuing"
}

# Wait for dependencies
wait_for_postgres
wait_for_redis

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Apply database migrations
echo "Applying database migrations..."
python manage.py migrate

# Execute the main command
echo "Starting application..."
exec "$@"