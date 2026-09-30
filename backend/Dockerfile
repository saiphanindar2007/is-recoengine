FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
# No default JWT_SECRET_KEY or APP_ENV baked in here on purpose: the production-secret
# check in app/auth.py deliberately refuses to start with a known/default secret when
# APP_ENV=production. Pass real values at `docker run` / compose / Render time, e.g.:
#   docker run -e APP_ENV=production -e JWT_SECRET_KEY=$(openssl rand -hex 32) ...
# Without APP_ENV set, it defaults to "development" and runs with a dev secret so the
# container is still usable out-of-the-box for local testing.
CMD sh -c "python -m app.seed && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"
