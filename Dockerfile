FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
COPY pyproject.toml ./
COPY ai-engine/holoassist ./ai-engine/holoassist
COPY datasets/fixtures/instruction-catalog.json datasets/fixtures/diagnostic-catalog.json datasets/fixtures/sensor-current.json datasets/fixtures/sensor-temperature.json datasets/fixtures/sensor-vibration.json ./datasets/fixtures/
COPY docs/examples/safety-analysis.json docs/examples/diagnostic-analysis.json ./docs/examples/
COPY docs/equipment-intake.template.json ./docs/
RUN pip install --no-cache-dir --report /app/container-dependency-resolution.json '.[api,postgres]' \
    && pip check \
    && pip freeze > /app/requirements-container.lock.txt \
    && useradd --uid 10001 --create-home holoassist
USER 10001:10001
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "holoassist.api.app:container_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
