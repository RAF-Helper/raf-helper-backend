#!/usr/bin/env bash
# Start Streamlit Admin Panel for Staff and Events management

# Configuration
SERVICE_URL="${SERVICE_URL:-http://localhost:8000}"
PORT="${ADMIN_PANEL_PORT:-8501}"

echo "🚀 Starting RAF Helper Admin Panel"
echo "📍 Backend API: $SERVICE_URL"
echo "🌐 Panel will be available at: http://localhost:$PORT"
echo ""

# Activate virtual environment if available
if [ -d ".venv" ]; then
    source .venv/bin/activate
    echo "✅ Activated virtual environment"
fi

# Run Streamlit
streamlit run src/app/chat/test_ui/admin/panel.py \
    --server.port $PORT \
    --server.address 0.0.0.0 \
    --browser.gatherUsageStats false \
    --logger.level=info
