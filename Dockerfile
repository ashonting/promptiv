# ─── Stage 1: Build the React dashboard ─────────────────────────────
FROM node:20-alpine AS frontend-builder
WORKDIR /app/dashboard

# Install deps & copy everything in one go
COPY frontend/dashboard/package*.json ./
RUN npm ci

COPY frontend/dashboard ./
RUN npm run build

# ─── Stage 2: Assemble Python API + dashboard build ────────────────
FROM python:3.11-slim
WORKDIR /app

# Install system dependencies for psycopg/libpq (and any native deps)
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential gcc libpq-dev curl \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy your backend code
COPY backend ./backend

# Copy your main-site static (CSS/JS/fonts under /static)
COPY static ./static

# Copy the built dashboard
COPY --from=frontend-builder /app/dashboard/dist ./frontend/dashboard/dist

# Environment
COPY .env .env

EXPOSE 8000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
