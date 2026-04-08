#!/usr/bin/env bash
# Start the Chainlit test UI for the agent system
#
# Usage:
#   export DEBUG=True
#   ./scripts/start_test_ui.sh

set -e

cd "$(dirname "$0")/.."

# Check for DEBUG mode
if [ "${DEBUG}" != "True" ] && [ "${DEBUG}" != "true" ]; then
  echo "⚠️  Test UI requires DEBUG=True in environment."
  echo "   Set it with: export DEBUG=True"
  echo ""
  read -p "Continue anyway? (y/N): " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
  fi
fi

echo "🚀 Starting Chainlit test UI..."
echo "   URL: http://localhost:8001"
echo "   Debug mode: ${DEBUG:-False}"
echo "   Press Ctrl+C to stop"
echo ""

uv run chainlit run src/app/chat/test_ui.py --host 0.0.0.0 --port 8001
