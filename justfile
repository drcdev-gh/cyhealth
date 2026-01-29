set shell := ["bash", "-eu", "-o", "pipefail", "-c"]

TAG_BASE:="ghcr.io/drcdev-gh/cyhealth"

run-dev:
    docker compose -f docker-compose-build.yaml up -d --build

build-latest tag:
    docker build -t {{TAG_BASE}}:{{tag}} .
    docker tag {{TAG_BASE}}:{{tag}} {{TAG_BASE}}:latest

push-latest tag:
    docker push {{TAG_BASE}}:{{tag}}
    docker push {{TAG_BASE}}:latest

run-tag tag:
    docker run -v ./cyhealth.ini:/etc/cyhealth.ini {{TAG_BASE}}::{{tag}}
