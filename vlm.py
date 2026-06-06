import base64
import json
import logging
import os
import re
import sys

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ── Cac hang so mac dinh ─────────────────────────────────────────────────────
DEFAULT_MODEL      = "meta-llama/llama-4-scout-17b-16e-instruct"
DEFAULT_MAX_TOKENS = 512

KIE_PROMPT = (
    "This is a receipt image. "
    "Extract the following fields and return ONLY a valid JSON object:\n"
    "  - \"company\": store or company name (string or null)\n"
    "  - \"date\": transaction date as shown (string or null)\n"
    "  - \"total\": final total amount as a number, e.g. 12.50 (float or null)\n"
    "If a field is not found, set it to null. "
    "Return ONLY the JSON object, no explanation, no markdown, no code block."
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ReceiptKIE -- class chinh, dung cho ca script lan import tu file khac
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class ReceiptKIE:
    """
    Trich xuat thong tin hoa don (company, date, total) bang Groq Vision API.

    Vi du su dung:
        kie = ReceiptKIE()                          # doc API key tu .env
        kie = ReceiptKIE(api_key="gsk_...")         # truyen truc tiep

        result  = kie.extract("receipt.jpg")        # 1 anh -> dict
        results = kie.extract_folder("images/")     # nhieu anh -> list[dict]
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        prompt: str = KIE_PROMPT,
    ):
        """
        Khoi tao ReceiptKIE.

        Args:
            api_key:    Groq API key. Mac dinh lay tu bien moi truong GROQ_API_KEY.
            model:      Ten model tren Groq (mac dinh Llama 4 Scout Vision).
            max_tokens: So token toi da trong phan hoi.
            prompt:     Prompt gui kem anh.
        """
        key = api_key or os.getenv("GROQ_API_KEY", "")
        if not key:
            raise ValueError(
                "Thieu GROQ_API_KEY. "
                "Hay truyen api_key=... hoac them vao file .env: GROQ_API_KEY=gsk_..."
            )

        try:
            from groq import Groq
            self._client = Groq(api_key=key)
        except ImportError:
            raise ImportError("Chua cai thu vien groq. Chay: pip install groq")

        self.model      = model
        self.max_tokens = max_tokens
        self.prompt     = prompt
        logger.info(f"ReceiptKIE khoi tao thanh cong. Model: {self.model}")

    # ── Public API ────────────────────────────────────────────────────────────

    def extract(self, image_path: str) -> dict:
        """
        Trich xuat KIE tu 1 anh receipt.

        Args:
            image_path: Duong dan toi file anh (.jpg, .jpeg, .png, .webp).

        Returns:
            dict voi cac truong: company, date, total, image, note.
            Vi du: {"company": "Starbucks", "date": "05/06/2025", "total": 12.5,
                    "image": "receipt.jpg", "note": "ok"}
        """
        if not os.path.isfile(image_path):
            raise FileNotFoundError(f"Khong tim thay file: {image_path}")

        filename = os.path.basename(image_path)
        logger.info(f"Xu ly: {filename}")

        try:
            raw    = self._call_api(image_path)
            result = self._parse_json(raw)
        except Exception as e:
            logger.error(f"Loi khi xu ly {filename}: {e}")
            result = {"company": None, "date": None, "total": None, "error": str(e)}

        result["image"] = filename
        if "error" not in result:
            missing = [k for k in ("company", "date", "total") if result.get(k) is None]
            result["note"] = f"missing: {', '.join(missing)}" if missing else "ok"

        return result

    # ── Private helpers ───────────────────────────────────────────────────────

    def _call_api(self, image_path: str) -> str:
        """Gui anh len Groq API, tra ve raw text phan hoi."""
        data_uri = self._encode_image(image_path)
        resp = self._client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": data_uri}},
                        {"type": "text",      "text": self.prompt},
                    ],
                }
            ],
            max_tokens=self.max_tokens,
        )
        return (resp.choices[0].message.content or "").strip()

    @staticmethod
    def _encode_image(image_path: str) -> str:
        """Doc file anh va ma hoa sang base64 data-URI."""
        ext = os.path.splitext(image_path)[1].lower()
        mime = {".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                ".png": "image/png",  ".webp": "image/webp"}.get(ext, "image/jpeg")
        with open(image_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        return f"data:{mime};base64,{b64}"

    @staticmethod
    def _parse_json(raw: str) -> dict:
        """Parse JSON tu phan hoi model, co fallback."""
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

        # Thu 1: parse truc tiep
        try:
            return normalize(json.loads(raw))
        except json.JSONDecodeError:
            pass

        # Thu 2: trong markdown code block
        m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
        if m:
            try:
                return normalize(json.loads(m.group(1)))
            except json.JSONDecodeError:
                pass

        # Thu 3: tim { ... } bat ky
        m = re.search(r"\{.*?\}", raw, re.DOTALL)
        if m:
            try:
                return normalize(json.loads(m.group(0)))
            except json.JSONDecodeError:
                pass

        logger.warning("Khong the parse JSON tu phan hoi model.")
        return {**empty, "_raw": raw}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Chay truc tiep
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python vlm_kie.py <duong-dan-anh>")
        print("  Vi du: python vlm_kie.py images/receipt.jpg")
        sys.exit(1)

    try:
        kie    = ReceiptKIE()
        result = kie.extract(sys.argv[1])
    except (ValueError, FileNotFoundError) as e:
        print(f"[ERROR] {e}")
        sys.exit(1)

    print(json.dumps(result, indent=4, ensure_ascii=False))