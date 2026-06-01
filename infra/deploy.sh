#!/bin/bash
# BuyerOS Production Deployment Script

set -e

echo "=== BuyerOS Deployment ==="

# Load environment
if [ -f .env.production ]; then
    export $(cat .env.production | grep -v '^#' | xargs)
fi

# Build backend
echo "Building backend..."
cd backend
pip install -r requirements.txt --quiet
python -m py_compile app/main.py
cd ..

# Run migrations
echo "Running database migrations..."
cd backend
alembic upgrade head || echo "No migrations to run"
cd ..

# Start backend
echo "Starting backend on port 8000..."
nohup uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 > backend.log 2>&1 &

echo "Backend started with PID $!"
echo "Logs: backend.log"

# Health check
sleep 2
curl -s http://localhost:8000/health || echo "Health check failed"
