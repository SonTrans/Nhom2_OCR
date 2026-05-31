import re
import unicodedata

# ======================================= OCR ===========================================
def PaddleOCR_to_string(paddle_ocr_output):
    text_lines = []

    if paddle_ocr_output and paddle_ocr_output[0]:
        for line in paddle_ocr_output[0]:
            text_lines.append(line[1][0])

    raw_text = "\n".join(text_lines)
    return raw_text


def VietOCR_to_string(viet_ocr_output):
    raw_text = ""
    # Nếu output là string
    if isinstance(viet_ocr_output, str):
        raw_text = viet_ocr_output

    # Nếu output là list
    elif isinstance(viet_ocr_output, list):
        text_lines = [str(line) for line in viet_ocr_output]
        raw_text = "\n".join(text_lines)

    return raw_text


def Tesseract_to_string(tesseract_output):
    raw_text = ""
    # Nếu đã là string thì return luôn
    if isinstance(tesseract_output, str):
        raw_text = tesseract_output.strip()

    # Nếu là dict từ image_to_data()
    elif isinstance(tesseract_output, dict):
        text_lines = []

        texts = tesseract_output.get("text", [])

        for text in texts:
            text = str(text).strip()

            if text:
                text_lines.append(text)

        raw_text = "\n".join(text_lines)

    return raw_text


def normalize(text):
    # viết thường
    text = text.lower()

    # bỏ dấu tiếng Việt
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")

    text.strip()

    return text

def get_feature(raw_text):
    list_raw_text = raw_text.split('\n')
    regex = r"\b\d{2}[\/\-.]\d{2}[\/\-.]\d{4}\b"
    for text_id in range(len(list_raw_text)):
        list_raw_text[text_id] = normalize(list_raw_text[text_id])

    feature = {}
    feature['store'] = list_raw_text[0]

    feature['date'] = None
    for text in list_raw_text:
        match = re.search(r"\d{1,2}/\d{1,2}/\d{4}", text)
        if match is not None:
            feature["date"] = match.group()
            break

    total_val = None
    for i in range(len(list_raw_text) - 1):
        if "total" in list_raw_text[i]:
            total_val = list_raw_text[i + 1]
            break

    feature["total"] = total_val
    # print (list_raw_text)
    return feature

# ============================================= KIE =========================================================

def normalize_text(text):

    if text is None:
        return ""

    # lowercase
    text = text.lower()

    # bỏ dấu tiếng Việt
    text = unicodedata.normalize("NFD", text)

    text = "".join(
        c for c in text
        if unicodedata.category(c) != "Mn"
    )

    return text

def Regex_to_dict(raw_text):

    normalized_text = normalize_text(raw_text)

    result = {
        "store": None,
        "date": None,
        "total": None
    }

    lines = [
        line.strip()
        for line in normalized_text.split("\n")
        if line.strip()
    ]

    if lines:
        result["store"] = lines[0]

    date_match = re.search(
        r"\b\d{2}[\/\-.]\d{2}[\/\-.]\d{4}\b",
        normalized_text
    )

    if date_match:
        result["date"] = date_match.group()

    total_match = re.search(
        r"total[:\s]*\$?\s*([0-9]+(?:\.[0-9]{2})?)",
        normalized_text,
        re.IGNORECASE
    )

    if total_match:
        result["total"] = float(
            total_match.group(1)
        )

    return result

def LayoutLM_to_dict(layoutlm_entities):

    result = {
        "store": None,
        "date": None,
        "total": None
    }

    for item in layoutlm_entities:

        label = normalize_text(
            item.get("label", "")
        ).upper()

        token = normalize_text(
            item.get("token", "")
        )

        if label in ["STORE", "STORE_NAME"]:
            result["store"] = token

        elif label == "DATE":
            result["date"] = token

        elif label == "TOTAL":

            cleaned = re.sub(
                r"[^\d.]",
                "",
                token
            )

            if cleaned:
                result["total"] = float(cleaned)

    return result


def VLM_to_dict(vlm_json):

    normalized_json = {
        normalize_text(k): v
        for k, v in vlm_json.items()
    }

    result = {
        "store": None,
        "date": None,
        "total": None
    }

    store = (
        normalized_json.get("store")
        or normalized_json.get("merchant")
        or normalized_json.get("vendor")
    )

    if store:
        result["store"] = normalize_text(store)

    date = (
        normalized_json.get("date")
        or normalized_json.get("invoice_date")
    )

    if date:
        result["date"] = normalize_text(date)

    # ---------- total ----------
    raw_total = (
        normalized_json.get("total")
        or normalized_json.get("amount_due")
        or normalized_json.get("balance_due")
    )

    if raw_total is not None:

        cleaned = re.sub(
            r"[^\d.]",
            "",
            str(raw_total)
        )

        if cleaned:
            result["total"] = float(cleaned)

    return result


# =========================================================
# EXAMPLES
# =========================================================

receipt_text = """
CỬA HÀNG SASKA
3768 Mission Blvd
08/15/2017
total
179.94$
"""

# print(Regex_to_dict(receipt_text))


layoutlm_output = [
    {"token": "CỬA HÀNG SASKA", "label": "STORE_NAME"},
    {"token": "08/15/2017", "label": "DATE"},
    {"token": "179.94$", "label": "TOTAL"}
]

# print(LayoutLM_to_dict(layoutlm_output))


vlm_output = {
    "merchant": "CỬA HÀNG SASKA",
    "invoice_date": "08/15/2017",
    "total": "$179.94"
}

# print(VLM_to_dict(vlm_output))


