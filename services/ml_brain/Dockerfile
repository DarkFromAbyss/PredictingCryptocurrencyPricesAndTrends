# Sử dụng Python 3.9 (nhẹ và ổn định)
FROM python:3.9-slim

# Thiết lập thư mục làm việc
WORKDIR /app

# Copy file requirements trước để tận dụng Docker cache
COPY requirements.txt .

# Cài đặt thư viện
# Thêm --no-cache-dir để giảm dung lượng image
RUN pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ source code
COPY . .

# Mở port (Mặc định cho FastAPI là 8000 bên trong container)
EXPOSE 8000

# Lệnh chạy mặc định (Sẽ bị override bởi docker-compose, nhưng cứ để dự phòng)
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]