FROM ghcr.io/astral-sh/uv:latest AS uv

FROM python:3.12-slim

COPY --from=uv /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
COPY src ./src

RUN apt-get update \
    && apt-get install --yes --no-install-recommends socat \
    && rm -rf /var/lib/apt/lists/* \
    && uv sync --frozen --no-dev --extra web

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

# Keep the application's security-floor loopback bind unchanged. The relay listens only on the
# container interface so Docker can publish it to the host's loopback address in compose.yml.
CMD ["sh", "-c", "socat TCP-LISTEN:8000,bind=$(hostname -i | awk '{print $1}'),fork,reuseaddr TCP:127.0.0.1:8000 & exec living-narrative serve --project-root /projects --port 8000"]
