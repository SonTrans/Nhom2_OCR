import json
import logging
import os
import re

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ── Các hằng số mặc định ──────────────────────────────────────────────────────
DEFAULT_MODEL      = "meta-llama/llama-4-scout-17b-16e-instruct"
DEFAULT_MAX_TOKENS = 512

KIE_PROMPT_TEMPLATE = (
    "Below is the OCR text extracted from a receipt image.\n"
    "Extract the following fields and return ONLY a valid JSON object:\n"
    "  - \"store\": store or company name (string or null)\n"
    "  - \"date\": transaction date as shown (string or null)\n"
    "  - \"total\": final total amount as a number, e.g. 12.50 (float or null)\n"
    "If a field is not found, set it to null.\n"
    "Return ONLY the JSON object, no explanation, no markdown, no code block.\n\n"
    "OCR TEXT:\n"
    "{ocr_text}"
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ReceiptKIE -- class chính, dùng cho cả script lẫn import từ file khác
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class ReceiptKIE:
    """
    Trích xuất thông tin hóa đơn (store, date, total) từ một chuỗi OCR text
    bằng Groq LLM API (text-only, không cần ảnh).

    Ví dụ sử dụng:
        kie = ReceiptKIE()
        result = kie.extract(ocr_text)
        # Trả về dict {"store": ..., "date": ..., "total": ...}
    """

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

    def extract(self, ocr_text: str) -> dict:
        """
        Trích xuất thông tin hóa đơn từ một chuỗi OCR text.

        Args:
            ocr_text: Chuỗi văn bản OCR thô từ hóa đơn.

        Returns:
            dict với 3 trường:
            {
                "store": "Tên cửa hàng" | None,
                "date":  "ngày giao dịch" | None,
                "total": 77.83 | None
            }
        """
        if not isinstance(ocr_text, str) or not ocr_text.strip():
            logger.warning("ocr_text rỗng hoặc không hợp lệ.")
            return {"store": None, "date": None, "total": None}

        try:
            raw    = self._call_api(ocr_text)
            result = self._parse_json(raw)
        except Exception as e:
            logger.error(f"Lỗi khi xử lý: {e}")
            result = {"store": None, "date": None, "total": None}

        return result

    # ── Private helpers ───────────────────────────────────────────────────────

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
    def _parse_json(raw: str) -> dict:
        """Parse JSON từ phản hồi model, có fallback. Chỉ giữ store, date, total."""
        empty = {"store": None, "date": None, "total": None}
        if not raw:
            return empty

        def normalize(data: dict) -> dict:
            total = data.get("total")
            if total is not None:
                try:
                    total = float(str(total).replace(",", "."))
                except (ValueError, TypeError):
                    total = None
            # Hỗ trợ cả key "store" lẫn "company" từ model
            store = data.get("store") or data.get("company")
            date  = data.get("date")
            return {
                "store": str(store).strip() if store else None,
                "date":  str(date).strip()  if date  else None,
                "total": total,
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
        return empty


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Chạy trực tiếp (demo)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
if __name__ == "__main__":
    import sys

    # Đọc OCR text từ stdin hoặc argv
    if len(sys.argv) > 1:
        ocr_text = " ".join(sys.argv[1:])
    else:
        print("Nhập OCR text (kết thúc bằng EOF / Ctrl+D):")
        ocr_text = sys.stdin.read()

    try:
        kie    = ReceiptKIE()
        result = kie.extract(ocr_text)
    except ValueError as e:
        print(f"[ERROR] {e}")
        sys.exit(1)

    print(json.dumps(result, indent=4, ensure_ascii=False))