#!/bin/sh

# Set default interval to every 1 minute if not provided
CRON_INTERVAL=${CRON_INTERVAL:-"* * * * *"}
echo "${CRON_INTERVAL} /app/run_endpoint.sh" > /etc/crontabs/root

crond
exec uv run uvicorn main:app --host 0.0.0.0 --port 8085

