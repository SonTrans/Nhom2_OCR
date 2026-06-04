import os
import io
import pytesseract
import requests
from PIL import Image


class TesseractService:
    def __init__(self):
        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        self.lang = "vie+eng"
        self.config = "--psm 3"

    def extract_text(self, image_input) -> str:
        """
        Hàm này trích xuất ra string từ ảnh với các input
        - Nếu là chuỗi bắt đầu bằng 'http': Tải ảnh từ URL.
        - Nếu là chuỗi thông thường: Tìm ảnh theo đường dẫn local.
        - Nếu là bytes: Đọc trực tiếp qua io.BytesIO.
        - Nếu là đối tượng PIL Image: Quét trực tiếp.
        """
        try:
            img = None

            # Đầu vào là một chuỗi
            if isinstance(image_input, str):
                if image_input.strip().startswith(("http://", "https://")): # trích xuất từ url của ảnh
                    response = requests.get(image_input.strip(), timeout=10, stream=True)
                    if response.status_code == 200:
                        img = Image.open(io.BytesIO(response.content))
                    else:
                        return f"Loi: Khong the tai anh tu URL (Status code: {response.status_code})"
                else:
                    # ảnh local tuwf file cục bộ
                    if os.path.exists(image_input):
                        img = Image.open(image_input)
                    else:
                        return f"Loi: Khong tim thay file tai duong dan: {image_input}"

            # Đầu vào là dữ liệu dạng Bytes (kéo thả ảnh)
            elif isinstance(image_input, bytes):
                img = Image.open(io.BytesIO(image_input))

            # Đầu vào đã là một đối tượng PIL Image sẵn rồi
            elif isinstance(image_input, Image.Image):
                img = image_input

            else:
                return "Loi: Dinh dang dau vao khong duoc ho tro!"

            if img is not None:
                # Chuyển đổi ảnh sang ảnh xám để Tesseract đọc chuẩn hơn nếu ảnh bị nhiễu
                img = img.convert("L")
                result = pytesseract.image_to_string(img, lang=self.lang, config=self.config)
                return result.strip()

            return "Loi: Khong the khoi tao du lieu anh."

        except Exception as e:
            return f"Loi he thong Tesseract: {str(e)}"