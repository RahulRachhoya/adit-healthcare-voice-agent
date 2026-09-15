FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.12.11 /uv /uvx /bin/
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 PYTHONUNBUFFERED=1
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project
COPY src ./src
RUN uv sync --frozen --no-dev && useradd --create-home app
USER app
RUN /app/.venv/bin/adit-agent download-files
CMD ["/app/.venv/bin/adit-agent", "start"]
