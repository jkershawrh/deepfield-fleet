# Stage 1: Build frontend
FROM node:20-slim AS frontend-build
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --legacy-peer-deps
COPY frontend/ ./
RUN npm run build

# Stage 2: Python backend + built frontend
FROM python:3.11-slim
WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir ".[db]"

COPY app/ ./app/
COPY migrations/ ./migrations/
COPY fixtures/ ./fixtures/
COPY config/ ./config/
COPY --from=frontend-build /build/dist ./frontend/dist/

RUN chown -R 1001:0 /app && chmod -R g=u /app
USER 1001

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
