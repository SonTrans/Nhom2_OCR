import json
import logging
import os
import re
import sys

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ── Các hằng số mặc định ──────────────────────────────────────────────────────
DEFAULT_MODEL      = "meta-llama/llama-4-scout-17b-16e-instruct"
DEFAULT_MAX_TOKENS = 512
DEFAULT_REPORT     = "/home/sown23/Documents/python/summary_report.txt"

KIE_PROMPT_TEMPLATE = (
    "Below is the OCR text extracted from a receipt image.\n"
    "Extract the following fields and return ONLY a valid JSON object:\n"
    "  - \"company\": store or company name (string or null)\n"
    "  - \"date\": transaction date as shown (string or null)\n"
    "  - \"total\": final total amount as a number, e.g. 12.50 (float or null)\n"
    "If a field is not found, set it to null.\n"
    "Return ONLY the JSON object, no explanation, no markdown, no code block.\n\n"
    "OCR TEXT:\n"
    "{ocr_text}"
)
class ReceiptKIE:
    def __init__(
        self,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ):
        """
        Khởi tạo ReceiptKIE.

        Args:
            api_key:    Groq API key. Mặc định lấy từ biến môi trường GROQ_API_KEY.
            model:      Tên model trên Groq (mặc định Llama 4 Scout).
            max_tokens: Số token tối đa trong phản hồi.
        """
        key = api_key or os.getenv("GROQ_API_KEY", "")
        if not key:
            raise ValueError(
                "Thiếu GROQ_API_KEY. "
                "Hãy truyền api_key=... hoặc thêm vào file .env: GROQ_API_KEY=gsk_..."
            )

        try:
            from groq import Groq
            self._client = Groq(api_key=key)
        except ImportError:
            raise ImportError("Chưa cài thư viện groq. Chạy: pip install groq")

        self.model      = model
        self.max_tokens = max_tokens
        logger.info(f"ReceiptKIE khởi tạo thành công. Model: {self.model}")

    # ── Public API ────────────────────────────────────────────────────────────

    def extract_from_report(self, report_path: str = DEFAULT_REPORT) -> list[dict]:
        if not os.path.isfile(report_path):
            raise FileNotFoundError(f"Không tìm thấy file báo cáo: {report_path}")

        blocks = self._parse_report(report_path)
        logger.info(f"Đã parse được {len(blocks)} hóa đơn từ {report_path}")

        results = []
        for image_name, ocr_text in blocks:
            logger.info(f"Xử lý: {image_name}")
            result = self._extract_one(image_name, ocr_text)
            results.append(result)

        return results

    def extract_one_from_text(self, image_name: str, ocr_text: str) -> dict:
        return self._extract_one(image_name, ocr_text)

    # ── Private helpers ───────────────────────────────────────────────────────

    def _extract_one(self, image_name: str, ocr_text: str) -> dict:
        """Gọi API cho một hóa đơn và trả về dict kết quả."""
        try:
            raw    = self._call_api(ocr_text)
            result = self._parse_json(raw)
        except Exception as e:
            logger.error(f"Lỗi khi xử lý {image_name}: {e}")
            result = {"company": None, "date": None, "total": None, "error": str(e)}

        result["image"] = image_name
        if "error" not in result:
            missing = [k for k in ("company", "date", "total") if result.get(k) is None]
            result["note"] = f"missing: {', '.join(missing)}" if missing else "ok"

        return result

    def _call_api(self, ocr_text: str) -> str:
        """Gửi OCR text lên Groq API (text-only), trả về raw text phản hồi."""
        prompt = KIE_PROMPT_TEMPLATE.format(ocr_text=ocr_text.strip())
        resp = self._client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=self.max_tokens,
        )
        return (resp.choices[0].message.content or "").strip()

    @staticmethod
    def _parse_report(report_path: str) -> list[tuple[str, str]]:
        """
        Parse file summary_report.txt thành danh sách (image_name, ocr_text).

        Định dạng mỗi block trong file:
            === KẾT QUẢ ẢNH: <tên ảnh> ===
            ...nội dung OCR...
            ========================================
        """
        with open(report_path, encoding="utf-8", errors="replace") as f:
            content = f.read()

        # Tách theo header "=== KẾT QUẢ ẢNH: ... ==="
        pattern = r"===\s*KẾT QUẢ ẢNH:\s*(.+?)\s*===\s*(.*?)(?====\s*KẾT QUẢ ẢNH:|\Z)"
        matches = re.findall(pattern, content, re.DOTALL)

        blocks = []
        for image_name, block_text in matches:
            image_name = image_name.strip()
            # Loại bỏ dòng phân cách ====... ở cuối block
            block_text = re.sub(r"={4,}\s*$", "", block_text.strip())
            blocks.append((image_name, block_text))

        return blocks

    @staticmethod
    def _parse_json(raw: str) -> dict:
        """Parse JSON từ phản hồi model, có fallback."""
        empty = {"company": None, "date": None, "total": None}
        if not raw:
            return empty

        def normalize(data: dict) -> dict:
            total = data.get("total")
            if total is not None:
                try:
                    total = float(str(total).replace(",", "."))
                except (ValueError, TypeError):
                    total = None
            company = data.get("company")
            date    = data.get("date")
            return {
                "company": str(company).strip() if company else None,
                "date":    str(date).strip()    if date    else None,
                "total":   total,
            }

        # Thử 1: parse trực tiếp
        try:
            return normalize(json.loads(raw))
        except json.JSONDecodeError:
            pass

        # Thử 2: trong markdown code block
        m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
        if m:
            try:
                return normalize(json.loads(m.group(1)))
            except json.JSONDecodeError:
                pass

        # Thử 3: tìm { ... } bất kỳ
        m = re.search(r"\{.*?\}", raw, re.DOTALL)
        if m:
            try:
                return normalize(json.loads(m.group(0)))
            except json.JSONDecodeError:
                pass

        logger.warning("Không thể parse JSON từ phản hồi model.")
        return {**empty, "_raw": raw}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Chạy trực tiếp
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
if __name__ == "__main__":
    # Cho phép truyền đường dẫn report tùy chỉnh qua argv, mặc định dùng file cố định
    report_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_REPORT

    try:
        kie     = ReceiptKIE()
        results = kie.extract_from_report(report_path)
    except (ValueError, FileNotFoundError) as e:
        print(f"[ERROR] {e}")
        sys.exit(1)

    print(json.dumps(results, indent=4, ensure_ascii=False))
