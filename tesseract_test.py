import os
from backend.service.tesseract_service import TesseractService


def test_scan_all():
    # 1. Khởi tạo duy nhất đối tượng Model Service
    ocr_service = TesseractService()

    IMAGE_DIR = "test_images"
    valid_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.webp')

    # 2. Lấy danh sách tất cả các file ảnh trong thư mục
    images = [f for f in os.listdir(IMAGE_DIR) if f.lower().endswith(valid_extensions)]

    print(f"🔥 Bắt đầu quét tổng số: {len(images)} ảnh...\n")

    # 3. Vòng lặp gọi model quét từng ảnh một
    for img_name in images:
        img_path = os.path.join(IMAGE_DIR, img_name)
        print(f"=== ĐANG QUÉT: {img_name} ===")

        # Gọi model bốc chữ
        result = ocr_service.extract_text(img_path)

        # In thẳng kết quả ra Terminal
        print(result)
        print("\n" + "=" * 50 + "\n")


if __name__ == "__main__":
    test_scan_all()