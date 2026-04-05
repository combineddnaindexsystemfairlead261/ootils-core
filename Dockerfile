FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[dev]"

COPY src/ /app/src/
COPY scripts/ /app/scripts/

CMD ["uvicorn", "ootils_core.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
