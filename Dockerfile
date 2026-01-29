FROM ghcr.io/astral-sh/uv:alpine3.22

RUN apk add --no-cache curl

WORKDIR /app
COPY ./main.py /app/
COPY ./pyproject.toml /app/
COPY ./uv.lock /app/

ENV UV_COMPILE_BYTECODE=1
ENV UV_NO_DEV=1

RUN uv sync --locked

CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8085"]
HEALTHCHECK --interval=60s --start-period=5s --retries=2 CMD curl -f http://localhost:8085/health || exit 1
