#!/bin/sh

curl -f -H "x-api-key: ${API_KEY}" http://localhost:8085/trigger || exit 1

