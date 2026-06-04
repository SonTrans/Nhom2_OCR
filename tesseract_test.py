import os
import pytesseract
from PIL import Image

# 1. Cấu hình cứng đường dẫn Tesseract trên Windows
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

IMAGE_DIR = "test_images"
valid_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.webp')

# 2. Lấy danh sách toàn bộ file ảnh từ folder test_images
images = [f for f in os.listdir(IMAGE_DIR) if f.lower().endswith(valid_extensions)]

print(f"--- Bắt đầu quét thẳng bằng Tesseract: {len(images)} ảnh ---\n")

# 3. Vòng lặp mở ảnh và quét chữ song ngữ
for img_name in images:
    img_path = os.path.join(IMAGE_DIR, img_name)
    print(f"📸 [QUÉT ẢNH]: {img_name}")

    # Gọi thẳng mô hình xử lý
    img = Image.open(img_path)
    img_gray = img.convert("L")  # Chuyển ảnh xám để tối ưu chính tả
    raw_text = pytesseract.image_to_string(img_gray, lang="vie+eng", config="--psm 3")

    # In kết quả thô ra Terminal
    print(raw_text.strip())
    print("\n" + "=" * 50 + "\n")

