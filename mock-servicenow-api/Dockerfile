FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VENV_PATH=/opt/venv

WORKDIR /src

RUN python -m venv ${VENV_PATH}

ENV PATH="${VENV_PATH}/bin:${PATH}"

COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VENV_PATH=/opt/venv \
    PATH="/opt/venv/bin:${PATH}" \
    SERVICENOW_API_HOST=0.0.0.0 \
    SERVICENOW_API_PORT=8000 \
    SERVICENOW_DB_PATH=/app/data/servicenow_mock.sqlite \
    SERVICENOW_RESEED_ON_STARTUP=false \
    MOCK_URL_BASE=http://localhost:8000

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY app ./app
COPY data ./data
COPY .env.example ./.env.example

RUN useradd --create-home --shell /usr/sbin/nologin appuser && \
    chown -R appuser:appuser /app /opt/venv

USER appuser

EXPOSE 8000

CMD ["python", "-m", "app.main"]
