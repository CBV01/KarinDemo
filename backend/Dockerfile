FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Expose the port FastAPI runs on
EXPOSE 7860

# FastAPI strictly requires host 0.0.0.0 and port 7860 for Hugging Face Spaces Docker environments.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
