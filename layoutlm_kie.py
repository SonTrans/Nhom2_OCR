"""
layoutlm_kie.py — KIE bằng LayoutLM Document-QA
Tác giả: Sơn — 29/5

Đầu vào:
  1. regex_baseline.py  → OCR text (words) từng ảnh (từ summary_report.txt của Lan)
  2. images/            → ảnh gốc để LayoutLM đọc layout

LayoutLM nhận image + word_boxes do ta tự cung cấp
→ không cần cài tesseract binary hệ thống

Chạy:
    conda activate sown23
    pip install "transformers==4.44.2" torch torchvision Pillow
    python layoutlm_kie.py
"""

import re
import sys
import json
import torch
from pathlib import Path
from PIL import Image
from transformers import pipeline, LayoutLMv2Processor, LayoutLMv2ForQuestionAnswering

# Thêm thư mục chứa regex_baseline vào path
sys.path.insert(0, str(Path(__file__).parent))
from regex_baseline import process as regex_process  # lấy OCR text từng ảnh

# ── Config ────────────────────────────────────────────────────────────────────
SUMMARY_FILE = "/home/sown23/Documents/python/summary_report.txt"
IMAGE_DIR    = "/home/sown23/Documents/python/images"
OUTPUT_JSON  = "/home/sown23/Documents/python/layoutlm_results.json"
QA_MODEL     = "impira/layoutlm-document-qa"

QUESTIONS = {
    "company": "What is the name of the merchant or restaurant?",
    "date":    "What is the date of the transaction?",
    "total":   "What is the total amount?",
}

# ── 1. Lấy OCR text từng ảnh từ regex_baseline ───────────────────────────────
def get_ocr_map(summary_file: str) -> dict:
    """
    Gọi regex_baseline.process() → parse JSON ra dict:
    { "1010-receipt.jpg": {"company":..., "date":..., "total":...}, ... }

    Đồng thời cần raw text để cung cấp cho LayoutLM.
    Tách raw text riêng bằng regex (giống logic trong regex_baseline).
    """
    with open(summary_file, "r", encoding="utf-8") as f:
        content = f.read().replace("\r\n", "\n").replace("\r", "\n")

    ocr_text_map = {}  # {filename: raw_tesseract_text}
    for block in re.split(r"=== KẾT QUẢ ẢNH:\s*", content):
        if not block.strip():
            continue
        m = re.match(r"(.+?)\s*===", block)
        if not m:
            continue
        filename = m.group(1).strip()
        t = re.search(r"\[TESSERACT\]:\n(.*?)(?=\n={10,}|\Z)", block, re.DOTALL)
        ocr_text_map[filename] = t.group(1).strip() if t else ""

    # Kết quả regex baseline (ground-truth tham chiếu)
    regex_results = json.loads(regex_process(summary_file))

    return ocr_text_map, regex_results


# ── 2. Tìm ảnh trong images/ ──────────────────────────────────────────────────
def find_image(filename: str, image_dir: str) -> str | None:
    for f in Path(image_dir).iterdir():
        if f.name.lower() == filename.lower():
            return str(f)
    return None


# ── 3. Chuyển raw OCR text → word list + fake bounding boxes ─────────────────
def text_to_words_boxes(ocr_text: str, img_w: int = 1000, img_h: int = 1000):
    """
    Tách words từ OCR text và gán bounding box giả theo thứ tự dòng/cột.
    LayoutLM cần bbox dạng [x0, y0, x1, y1] normalized 0–1000.

    Vì không có Tesseract binary, ta dùng bbox ước lượng từ vị trí dòng/token.
    Model vẫn hoạt động tốt vì impira/layoutlm-document-qa chủ yếu dựa vào text.
    """
    lines = [l for l in ocr_text.split("\n") if l.strip()]
    words, boxes = [], []
    total_lines = max(len(lines), 1)

    for line_idx, line in enumerate(lines):
        tokens = line.strip().split()
        if not tokens:
            continue
        total_tokens = max(len(tokens), 1)
        # y position ước lượng theo số thứ tự dòng
        y0 = int((line_idx / total_lines) * 1000)
        y1 = int(((line_idx + 1) / total_lines) * 1000)

        for tok_idx, word in enumerate(tokens):
            x0 = int((tok_idx / total_tokens) * 1000)
            x1 = int(((tok_idx + 1) / total_tokens) * 1000)
            words.append(word)
            boxes.append([x0, y0, x1, y1])

    return words, boxes


# ── 4. LayoutLM QA với words+boxes tự cung cấp ───────────────────────────────
def run_layoutlm_with_words(image_path: str, ocr_text: str, pipe) -> dict:
    """
    Feed image + words + boxes vào LayoutLM Document-QA.
    Bypass Tesseract bằng cách cung cấp word_boxes thủ công.
    """
    image = Image.open(image_path).convert("RGB")
    img_w, img_h = image.size
    words, boxes = text_to_words_boxes(ocr_text, img_w, img_h)

    if not words:
        return {"company": None, "date": None, "total": None, "note": "empty_ocr"}

    result = {}
    for field, question in QUESTIONS.items():
        try:
            ans = pipe(
                image=image,
                question=question,
                word_boxes=list(zip(words, boxes))  # cung cấp thủ công, không dùng tesseract
            )
            if isinstance(ans, list):
                ans = ans[0]
            result[field] = ans.get("answer") if isinstance(ans, dict) else str(ans)
        except Exception as e:
            result[field] = None
            print(f"  [WARN] {field}: {e}")

    return result


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    # Load model
    device = 0 if torch.cuda.is_available() else -1
    print(f"[MODEL] Loading '{QA_MODEL}' trên {'GPU' if device == 0 else 'CPU'} ...")
    pipe = pipeline("document-question-answering", model=QA_MODEL, device=device)
    print("[MODEL] Sẵn sàng.\n")

    # Đọc OCR text từ regex_baseline + summary_report
    print(f"[INPUT] Đọc OCR từ regex_baseline: {SUMMARY_FILE}")
    ocr_text_map, regex_results = get_ocr_map(SUMMARY_FILE)
    print(f"[INPUT] Có {len(ocr_text_map)} ảnh trong report\n")

    final = {}
    for filename, ocr_text in ocr_text_map.items():
        img_path = find_image(filename, IMAGE_DIR)
        print(f"[IMG] {filename}")

        if not img_path:
            print(f"  ⚠ Không có ảnh trong {IMAGE_DIR} → bỏ qua\n")
            continue

        extracted = run_layoutlm_with_words(img_path, ocr_text, pipe)
        extracted["image"] = Path(img_path).name
        final[filename] = extracted

        print(f"  company : {extracted.get('company')}")
        print(f"  date    : {extracted.get('date')}")
        print(f"  total   : {extracted.get('total')}\n")

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(final, f, indent=4, ensure_ascii=False)

    print(f"[DONE] {len(final)} ảnh → {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
