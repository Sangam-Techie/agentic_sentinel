# Streamlit dashboard - same pattern as backend

FROM docker.io/library/python:3.12-slim AS builder

#Grab the uv binary
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /build
COPY pyproject.toml .

# Install dependencies (Project + Streamlit) in one go
# We add 'streamlit' here so uv handles all the math for versions at once
RUN uv pip install --system -r pyproject.toml streamlit

# Copy source and install project as editable
COPY agentic_sentinel/ ./agentic_sentinel/
RUN uv pip install --system -e .

# --- STAGE 2: runtime -------------------
FROM docker.io/library/python:3.12-slim AS runtime

RUN useradd --create-home --shell /bin/bash sentinel

WORKDIR /app

# Copying the lean library files and binaries
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /build /app

# Copy the dashboard-specific code
COPY dashboard/ ./dashboard/

# Switch to sentinel user
USER sentinel

ENV AGENT_KILL_SWITCH=false
ENV DATABASE_URL=sqlite:////data/agent_audit.sqlite

# Placeholder entrypoint - later week replaces this with:
# CMD ["uvicorn", "dashboard.main:app", "--host", "0.0.0.0", "--port", "8001"]
CMD ["python", "-c", "print('Dashboard image OK - Streamlit app wired in/around Week 9')"]
