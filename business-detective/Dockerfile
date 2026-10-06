# One container: builds the React app, then serves site + API from FastAPI.  (Not exercised in the authoring sandbox: Docker was unavailable.)
FROM node:20-slim AS web
WORKDIR /web
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
ARG VITE_CONTACT_EMAIL=""
ENV VITE_CONTACT_EMAIL=$VITE_CONTACT_EMAIL
RUN npm run build

FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends fonts-dejavu-core && rm -rf /var/lib/apt/lists/*
WORKDIR /srv
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./backend/
COPY --from=web /web/dist ./frontend_dist
ENV APP_ENV=production FRONTEND_DIST=/srv/frontend_dist STORAGE_DIR=/data/storage PYTHONUNBUFFERED=1
RUN useradd -m app && mkdir -p /data/storage && chown -R app /data
USER app
WORKDIR /srv/backend
EXPOSE 8000
# Applies database migrations, then starts the server. $PORT is honoured by most PaaS hosts.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
