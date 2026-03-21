FROM python:3.11-slim

WORKDIR /app

# Copy the backend requirements and install
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire backend directory into the container
COPY backend/ /app/

# Expose the mandatory Hugging Face port
EXPOSE 7860

# Launch the FastAPI app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
