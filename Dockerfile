# Bắt đầu với image Python 3.10 phiên bản slim (nhỏ gọn, giảm thiểu kích thước image)
FROM python:3.10-slim

# Thiết lập thư mục làm việc mặc định bên trong container là /app
WORKDIR /app

# Cài đặt các thư viện hệ thống cần thiết (Cập nhật apt, sau đó cài tesseract và trình biên dịch gcc)
# Lệnh rm -rf /var/lib/apt/lists/* giúp dọn dẹp bộ nhớ cache của apt để làm nhẹ image
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-vie \
    libtesseract-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy file requirements.txt từ máy host (máy của bạn) vào thư mục hiện tại (/app) trong container
COPY requirements.txt .

# Cài đặt các thư viện Python từ requirements.txt. Tham số --no-cache-dir giúp giảm kích thước bộ nhớ tạm.
RUN pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ mã nguồn dự án từ máy bạn vào container (/app)
COPY . .

# Thông báo cho Docker biết container sẽ lắng nghe trên cổng 8000
EXPOSE 8000

# Lệnh mặc định sẽ được thực thi khi container bắt đầu chạy (Khởi động server uvicorn)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
