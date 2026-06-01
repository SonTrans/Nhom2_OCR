"""
vlm_kie.py — KIE bằng PaddleOCR trên ảnh receipt
Tác giả: Sơn — 01/6

Đầu vào : folder images/ chứa ảnh receipt (.jpg/.png)
Đầu ra  : vlm_results.json

Cài:
    # CPU only
    pip install paddlepaddle paddleocr

    # GPU (khuyên dùng nếu có CUDA)
    pip install paddlepaddle-gpu paddleocr

    python vlm_kie.py
    python vlm_kie.py --images ./images --output ./vlm_results.json
"""

import re
import json
import argparse
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
IMAGE_DIR   = "/home/sown23/Documents/python/images"
OUTPUT_JSON = "/home/sown23/Documents/python/vlm_results.json"

# ── Load PaddleOCR ─────────────────────────────────────────────────────────────
def load_paddle_ocr():
    try:
        from paddleocr import PaddleOCR
    except ImportError:
        raise ImportError(
            "PaddleOCR chưa được cài. Chạy:\n"
            "  pip install paddlepaddle paddleocr        # CPU\n"
            "  pip install paddlepaddle-gpu paddleocr    # GPU"
        )

    # Buộc dùng CPU: hệ thống có CUDA nhưng không có cuDNN
    # (paddlepaddle-gpu cần cu DNN để chạy GPU inference)
    print("[MODEL] Khởi tạo PaddleOCR 2.x (CPU mode) ...")
    ocr = PaddleOCR(
        use_angle_cls=True,  # phát hiện chữ xoay 180°
        lang="en",
        use_gpu=False,       # tắt GPU: tránh lỗi cuDNN không có
        show_log=False,
    )
    print("[MODEL] Sẵn sàng.\n")
    return ocr


# ── OCR một ảnh → chuỗi văn bản ───────────────────────────────────────────────
def ocr_image(image_path: str, ocr) -> str:
    """Trả về toàn bộ văn bản nhận diện được từ ảnh, mỗi dòng một dòng."""
    result = ocr.ocr(image_path, cls=True)
    # PaddleOCR 2.x trả về: [ [ [[bbox], [text, conf]], ... ] ]
    if not result or not result[0]:
        return ""

    lines = []
    for line in result[0]:
        # line = [[bbox_points], [text, confidence]]
        text = line[1][0]
        lines.append(text)

    return "\n".join(lines)


# ── KIE bằng Regex ────────────────────────────────────────────────────────────
def extract_kie_regex(ocr_text: str) -> dict:
    """Trích xuất company / date / total từ văn bản OCR bằng regex."""
    result = {"company": None, "date": None, "total": None}

    ocr_text = ocr_text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.strip() for line in ocr_text.split("\n") if line.strip()]

    # --- Tên cửa hàng: dòng đầu tiên không rỗng ---
    if lines:
        company = re.sub(r'^[^a-zA-Z0-9\u00C0-\u024F]+', '', lines[0]).strip()
        result["company"] = company if company else lines[0].strip()

    # --- Ngày tháng ---
    date_pattern = r'\b(\d{1,2}[/\-]\d{1,2}[/\-]\d{4})\b'
    date_match = re.search(date_pattern, ocr_text)
    if date_match:
        result["date"] = date_match.group(1)

    # --- Tổng tiền (Grand Total → Total → Subtotal, ưu tiên từ trên xuống) ---
    total_keywords = [
        r'(?:grand\s+total)',
        r'(?:t[o0]tal\s+(?:tax|amount|due)?)',
        r'(?:balance\s+due)',
        r'(?:take[\-\s]?[o0]ut\s+t[o0]tal)',
        r'(?:t[o0]ta[l\]1])',
        r'(?:subt[o0]tal)',
    ]
    amount_pattern = r'[\$\s:=\-]*(\d+[.,]\d{2})'

    for keyword in total_keywords:
        pattern = rf'(?i){keyword}{amount_pattern}'
        match = re.search(pattern, ocr_text)
        if match:
            amount_str = match.group(1).replace(',', '.')
            result["total"] = float(amount_str)
            break

    return result


# ── Xử lý một ảnh ─────────────────────────────────────────────────────────────
def run_paddle(image_path: str, ocr) -> dict:
    raw_text = ocr_image(image_path, ocr)
    kie = extract_kie_regex(raw_text)
    return kie


# ── Main ──────────────────────────────────────────────────────────────────────
def main(image_dir: str, output_json: str):
    # Buộc CPU: GPU có CUDA nhưng thiếu cuDNN → paddlepaddle-gpu sẽ crash
    print("[DEVICE] CPU (GPU bị tắt do không có cuDNN)\n")

    img_dir = Path(image_dir)
    images = sorted(
        f for f in img_dir.iterdir()
        if f.suffix.lower() in (".jpg", ".jpeg", ".png")
    )

    if not images:
        print(f"[ERROR] Không có ảnh trong: {image_dir}")
        return

    print(f"[INPUT] {len(images)} ảnh trong '{image_dir}':")
    for img in images:
        print(f"  {img.name}")
    print()

    ocr = load_paddle_ocr()

    final = {}
    for img_path in images:
        print(f"[IMG] {img_path.name}")
        try:
            result = run_paddle(str(img_path), ocr)
        except Exception as e:
            print(f"  [ERROR] {e}")
            result = {"company": None, "date": None, "total": None, "error": str(e)}

        result["image"] = img_path.name
        final[img_path.name] = result
        print(f"  company : {result.get('company')}")
        print(f"  date    : {result.get('date')}")
        print(f"  total   : {result.get('total')}\n")

    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(final, f, indent=4, ensure_ascii=False)

    print(f"[DONE] {len(final)} ảnh → {output_json}")


# ── Entry ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="KIE receipt bằng PaddleOCR")
    parser.add_argument("--images", default=IMAGE_DIR, help="Thư mục chứa ảnh")
    parser.add_argument("--output", default=OUTPUT_JSON, help="File JSON kết quả")
    args, _ = parser.parse_known_args()
    main(args.images, args.output)
