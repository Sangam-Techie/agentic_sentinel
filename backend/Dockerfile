FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir fastapi uvicorn wheel==0.47.0
COPY pyproject.toml .
COPY agentic_sentinel ./agentic_sentinel
RUN pip install --no-cache-dir -e .
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
