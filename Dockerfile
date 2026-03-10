FROM ghcr.io/astral-sh/uv:alpine3.22

RUN apk add --no-cache curl dcron

WORKDIR /app
COPY ./main.py /app/
COPY ./pyproject.toml /app/
COPY ./uv.lock /app/
COPY ./run_endpoint.sh /app/run_endpoint.sh
COPY ./entrypoint.sh /app/entrypoint.sh

RUN chmod +x /app/run_endpoint.sh /app/entrypoint.sh

ENV UV_COMPILE_BYTECODE=1
ENV UV_NO_DEV=1

RUN uv sync --locked

HEALTHCHECK --interval=75s --start-period=5s --retries=2 CMD curl -f http://localhost:8085/status || exit 1

CMD ["/app/entrypoint.sh"]
