set shell := ["bash", "-eu", "-o", "pipefail", "-c"]

TAG_BASE:="ghcr.io/drcdev-gh/cyhealth"

run-dev:
    docker compose -f docker-compose-build.yaml up -d --build

run-tag tag:
    docker run -v ./cyhealth.ini:/etc/cyhealth.ini {{TAG_BASE}}::{{tag}}
