FROM python:3.10-slim

WORKDIR /app

# Cài đặt thêm thư viện hệ thống (nếu cần cho Matplotlib/Numpy)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy mã nguồn
COPY src/ src/

# Copy file cấu hình quan trọng
COPY config.yaml .

# Tạo thư mục để lưu Model và Biểu đồ
RUN mkdir -p saved_models

# Chạy App
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]