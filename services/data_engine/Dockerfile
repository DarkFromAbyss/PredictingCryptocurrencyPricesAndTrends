# Sử dụng Python 3.10 bản nhẹ (slim)
FROM python:3.10-slim

# Thiết lập thư mục làm việc trong container
WORKDIR /app

# Copy file thư viện trước để tận dụng Docker Cache
COPY requirements.txt .

# Cài đặt thư viện
RUN pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ mã nguồn vào
COPY src/ src/

# Chạy App trên cổng 8000 (Cổng nội bộ container)
# Lưu ý: docker-compose sẽ map cổng này ra 8001 ở máy thật
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]