# API image, self-contained for deployment. Build from the repository root:
#   docker build -f backend/Dockerfile -t hatua-api .
# The risk model release and the under-24 model are baked in. ml/artefacts is git-ignored,
# so build on a machine that has them. docker-compose.yml still mounts ml/artefacts over
# /srv/ml/artefacts for local development, so a new local release needs no rebuild there.
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /srv

# hatua_ml first, then the API requirements, so code edits do not reinstall everything
COPY ml/pyproject.toml ml/pyproject.toml
COPY ml/src ml/src
COPY backend/requirements.txt backend/requirements.txt
RUN cd backend && pip install -r requirements.txt

# Models: the release the API serves and the under-24 model
ARG MODEL_RELEASE=1.1.0
COPY ml/artefacts/release/${MODEL_RELEASE} ml/artefacts/release/${MODEL_RELEASE}
COPY ml/artefacts/xgboost_under2/short_30 ml/artefacts/xgboost_under2/short_30
ENV MODEL_DIR=/srv/ml/artefacts \
    MODEL_RELEASE=${MODEL_RELEASE} \
    UNDER2_MODEL_DIR=/srv/ml/artefacts/xgboost_under2/short_30

# The website (main.py serves web/) and the Swahili lines (i18n.py reads i18n/sw.json),
# both read from the repository root
COPY web web
COPY i18n/sw.json i18n/sw.json

COPY backend backend
RUN useradd --create-home hatua && chown -R hatua /srv
USER hatua
WORKDIR /srv/backend

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4)"
# Apply migrations, then serve. Two workers: each loads the models once.
# --forwarded-allow-ips trusts the X-Forwarded-* headers from Caddy, so redirects keep https.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2 --proxy-headers --forwarded-allow-ips='*'"]
