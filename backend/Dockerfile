# Multi-stage build: buider installs deps, runtime is lean

# --- Stage 1: builder ----------
# using standard way to ensure CI build works everywhere
FROM docker.io/library/python:3.12-slim AS builder

# Install uv by copying the binary from the official image
# This is faster than 'pip install uv'
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /build

# Enable bytecode compilation for faster installs
ENV UV_COMPILE_BYTECODE=1

# Copy dependency files first to leverage Docker caching
COPY pyproject.toml .

# Install dependencies using the pyproject.toml file
RUN uv pip install --system -r pyproject.toml

# Now copying the source code and install the project. --system installs to /usr/local instead of /usr
COPY agentic_sentinel/ ./agentic_sentinel/
RUN uv pip install --system -e .


# --- STAGE 2: runtime -------------------
FROM docker.io/library/python:3.12-slim AS runtime

# Create a non-root user - running as root inside a container
# is a security anti-pattern. If the container is compromised,
# the attacker gets a non-privileged user, not root.
RUN useradd --create-home --shell /bin/bash sentinel

WORKDIR /app

# Copy installed packages from the builder stage(copy the site)
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /user/local/bin
COPY --from=builder /build /app

# Switch to non-root user
USER sentinel

# Environment defaults - override at runtime via --env or podman-compose.yml
ENV AGENT_KILL_SWITCH=false
ENV DATABASE_URL=sqlite:////data/agent_audit.sqlite
ENV LOG_LEVEL=INFO

# Placeholder entrypoint - later week replaces this with:
# CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
CMD ["python", "-c", \
    "from agentic_sentinel.agents import AgentBase; \
    print('Backend image OK - FastAPI app wired in/around Week 9')"]

# Document the port the app will listen on (informational only - doesn't publish it)
EXPOSE 8000
