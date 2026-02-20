#!/bin/bash

# Marketing Dashboard Start Script
# Starts both backend and frontend servers

echo "🚀 Starting Marketing Dashboard..."
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "Shutting down servers..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    wait $BACKEND_PID 2>/dev/null
    wait $FRONTEND_PID 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM

# Start Backend
echo -e "${BLUE}[Backend]${NC} Setting up Python environment..."
cd "$SCRIPT_DIR/backend"

if [ ! -d "venv" ]; then
    echo -e "${BLUE}[Backend]${NC} Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate
pip install -r requirements.txt -q

echo -e "${GREEN}[Backend]${NC} Starting FastAPI server on http://localhost:8000"
# Exclude venv directory from file watching to prevent unnecessary reloads
uvicorn main:app --reload --host 0.0.0.0 --port 8000 --reload-exclude 'venv/*' &
BACKEND_PID=$!

# Start Frontend
echo -e "${BLUE}[Frontend]${NC} Installing dependencies..."
cd "$SCRIPT_DIR/frontend"

if [ ! -d "node_modules" ]; then
    npm install
fi

echo -e "${GREEN}[Frontend]${NC} Starting Vite dev server on http://localhost:5173"
npm run dev &
FRONTEND_PID=$!

echo ""
echo "=========================================="
echo -e "${GREEN}Dashboard ready!${NC}"
echo ""
echo "  Frontend: http://localhost:5173"
echo "  Backend:  http://localhost:8000"
echo "  API Docs: http://localhost:8000/docs"
echo ""
echo "  Model:    gpt-5-mini-2025-08-07"
echo ""
echo "Press Ctrl+C to stop all servers"
echo "=========================================="

# Wait for both processes
wait
