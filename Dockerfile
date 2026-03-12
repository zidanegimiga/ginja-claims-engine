FROM python:3.13-slim

RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    libgomp1 \
    gcc \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

# Install packages but skip the NVIDIA GPU libraries
# xgboost pulls nvidia-nccl-cu12 as an optional dep
# which is 293MB and useless on CPU-only deployments
RUN pip install --no-cache-dir -r requirements.txt \
    --extra-index-url https://pypi.org/simple \
    && pip uninstall -y nvidia-nccl-cu12 2>/dev/null || true

COPY . .

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]