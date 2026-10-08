#!/usr/bin/env bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

if [ ! -f .env ]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
fi

if command -v docker &> /dev/null; then
    echo "Starting Cyber Eco with Docker Compose..."
    docker compose up --build
else
    echo "Starting local Python server..."
    source .venv/bin/activate 2>/dev/null || true
    python backend/manage.py migrate
    python backend/manage.py runserver 127.0.0.1:8000
fi
