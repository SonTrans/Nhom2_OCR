import re
import json

def extract_kie_regex(ocr_text):
    result = {"company": None, "date": None, "total": None}

    # Normalize line endings (\r\n -> \n)
    ocr_text = ocr_text.replace('\r\n', '\n').replace('\r', '\n')

    # --- Lấy tên cửa hàng ---
    # Lấy dòng đầu tiên không rỗng, bỏ các ký tự đặc biệt ở đầu
    lines = [line.strip() for line in ocr_text.split('\n') if line.strip()]
    if lines:
        company = re.sub(r'^[^a-zA-Z0-9\u00C0-\u024F]+', '', lines[0]).strip()
        result["company"] = company if company else lines[0].strip()

    # --- Lấy ngày tháng ---
    # Hỗ trợ: DD/MM/YYYY, MM/DD/YYYY, M/D/YYYY, D/M/YYYY
    date_pattern = r'\b(\d{1,2}[/\-]\d{1,2}[/\-]\d{4})\b'
    date_match = re.search(date_pattern, ocr_text)
    if date_match:
        result["date"] = date_match.group(1)

    # --- Lấy tổng tiền ---
    # Ưu tiên: "Grand Total", "Total", "T0TAL", "TOTAL", "T0TA", rồi mới "Subtotal"
    # Hỗ trợ OCR noise: 0 thay vì O, ] thay vì l, etc.
    # Số tiền có thể có dấu $ và dấu cách xung quanh
    total_keywords = [
        r'(?:grand\s+total)',
        r'(?:t[o0]tal\s+(?:tax|amount|due)?)',
        r'(?:balance\s+due)',
        r'(?:take[\-\s]?[o0]ut\s+t[o0]tal)',
        r'(?:t[o0]ta[l\]1])',               # T0TAL, TOTAL, TOTAl
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


def process(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Normalize line endings
    content = content.replace('\r\n', '\n').replace('\r', '\n')

    # Tách dữ liệu theo từng ảnh
    # Separator: "=== KẾT QUẢ ẢNH: <filename> ==="
    blocks = re.split(r'=== KẾT QUẢ ẢNH:\s*', content)
    final_results = {}

    for block in blocks:
        if not block.strip():
            continue

        # Lấy tên file ảnh (phần trước " ===")
        header_match = re.match(r'(.+?)\s*===', block)
        if not header_match:
            continue
        filename = header_match.group(1).strip()

        # Trích xuất phần text nằm dưới [TESSERACT]:
        # Dừng khi gặp dòng ======= (separator) hoặc hết block
        tesseract_match = re.search(
            r'\[TESSERACT\]:\n(.*?)(?=\n={10,}|\Z)',
            block,
            re.DOTALL
        )

        if tesseract_match:
            tesseract_text = tesseract_match.group(1).strip()
            if tesseract_text:
                final_results[filename] = extract_kie_regex(tesseract_text)
            else:
                # Tesseract không trích được gì
                final_results[filename] = {"company": None, "date": None, "total": None, "note": "empty_tesseract"}
        else:
            final_results[filename] = {"company": None, "date": None, "total": None, "note": "no_tesseract_block"}

    return json.dumps(final_results, indent=4, ensure_ascii=False)


if __name__ == "__main__":
    output = process('/home/sown23/Documents/python/summary_report.txt')
    print(output)