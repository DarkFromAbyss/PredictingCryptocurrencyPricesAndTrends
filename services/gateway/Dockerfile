FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/

# Gateway chạy cổng 8000 (Cổng chính public ra ngoài)
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]