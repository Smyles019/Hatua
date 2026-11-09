# API image. Build from the repository root (it needs ml/ as well as backend/):
#   docker compose --profile api up -d --build
# The model release is not baked in: ml/artefacts is mounted read-only at run time, so a
# new release needs no rebuild (set MODEL_RELEASE and restart).
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /srv

# hatua_ml first, then the API requirements, so code edits do not reinstall everything
COPY ml/pyproject.toml ml/pyproject.toml
COPY ml/src ml/src
COPY backend/requirements.txt backend/requirements.txt
RUN cd backend && pip install -r requirements.txt

COPY backend backend
RUN useradd --create-home hatua && chown -R hatua /srv
USER hatua
WORKDIR /srv/backend

EXPOSE 8000
# Apply migrations, then serve. Two workers: each loads the model release once.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2"]
