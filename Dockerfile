# Use a slim Python image
FROM python:3.11-slim

# Set working directory inside container
WORKDIR /app

# Copy and install backend dependencies
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project directory (backend, shared, test files, etc.)
COPY . .

# Expose FastAPI's default port
EXPOSE 8000

# CMD to run tests (use uvicorn here to run the actual app)
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
