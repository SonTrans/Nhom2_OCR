"""
vlm_kie.py — KIE bằng PaddleOCR-VL (0.9B) trên ảnh receipt
Tác giả: Sơn — 06/2025

Pipeline : paddlex → PaddleOCR-VL-0.9B
Đầu vào  : folder images/ chứa ảnh receipt (.jpg/.png)
Đầu ra   : vlm_results.json

Cài đặt:
    pip install paddlepaddle paddleocr paddlex

Chạy:
    python vlm_kie.py
    python vlm_kie.py --images ./images --output ./vlm_results.json --device gpu:0
"""

import re
import json
import argparse
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
DEFAULT_IMAGE_DIR   = "/home/sown23/Documents/python/images"
DEFAULT_OUTPUT_JSON = "/home/sown23/Documents/python/vlm_results.json"

KIE_PROMPT = (
    "This is a receipt image. "
    "Extract the following fields and return ONLY a valid JSON object:\n"
    "  - \"company\": store or company name (string or null)\n"
    "  - \"date\": transaction date as shown (string or null)\n"
    "  - \"total\": final total amount as a number, e.g. 12.50 (float or null)\n"
    "If a field is not found, set it to null. "
    "Return ONLY the JSON object, no explanation."
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Class 1: VLMLoader — khởi tạo pipeline PaddleOCR-VL từ paddlex
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class VLMLoader:
    """Khởi tạo (lazy) pipeline PaddleOCR-VL từ paddlex."""

    PIPELINE_NAME = "PaddleOCR-VL"

    def __init__(self, device: str = "cpu"):
        self.device    = device
        self._pipeline = None

    def load(self):
        """Tải pipeline. Trả về self để chain."""
        try:
            from paddlex import create_pipeline
        except ImportError:
            raise ImportError(
                "Thiếu paddlex. Cài: pip install paddlepaddle paddleocr paddlex"
            )
        print(f"[MODEL] Khởi tạo {self.PIPELINE_NAME} trên {self.device.upper()} ...")
        self._pipeline = create_pipeline(
            pipeline=self.PIPELINE_NAME,
            device=self.device,
        )
        print("[MODEL] Sẵn sàng.\n")
        return self

    @property
    def pipeline(self):
        if self._pipeline is None:
            self.load()
        return self._pipeline


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Class 2: VLMInferencer — chạy inference cho 1 ảnh
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class VLMInferencer:
    """Gửi ảnh + prompt vào PaddleOCR-VL, trả về chuỗi kết quả thô."""

    def __init__(self, loader: VLMLoader, prompt: str = KIE_PROMPT):
        self.loader = loader
        self.prompt = prompt

    def predict(self, image_path: str) -> str:
        results  = self.loader.pipeline.predict({"image": image_path, "query": self.prompt})
        raw_text = ""
        for res in results:
            if isinstance(res, dict):
                raw_text = (
                    res.get("result", {}).get("answer", "")
                    or res.get("answer", "")
                    or res.get("rec_text", "")
                    or str(res)
                )
            else:
                raw_text = (
                    getattr(res, "answer", None)
                    or getattr(res, "rec_text", None)
                    or str(res)
                )
            break
        return raw_text.strip()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Class 3: KIEParser — parse output VLM → dict {company, date, total}
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class KIEParser:
    """Parse chuỗi JSON từ output VLM thành dict có cấu trúc."""

    def parse(self, raw_text: str) -> dict:
        result = {"company": None, "date": None, "total": None}

        # Loại bỏ markdown code block nếu có
        cleaned = re.sub(r"```(?:json)?\s*", "", raw_text, flags=re.IGNORECASE)
        cleaned = cleaned.replace("```", "").strip()

        json_match = re.search(r"\{.*?\}", cleaned, re.DOTALL)
        if json_match:
            try:
                parsed = json.loads(json_match.group())
                result["company"] = parsed.get("company") or None
                result["date"]    = parsed.get("date") or None
                total_raw = parsed.get("total")
                if total_raw is not None:
                    try:
                        result["total"] = float(str(total_raw).replace(",", "."))
                    except (ValueError, TypeError):
                        result["total"] = None
            except json.JSONDecodeError:
                result["raw_output"] = raw_text
        else:
            result["raw_output"] = raw_text

        return result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Class 4: ReceiptKIEPipeline — điều phối toàn bộ pipeline
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class ReceiptKIEPipeline:
    """
    Pipeline đầu cuối để trích xuất KIE từ nhiều ảnh receipt.

    Sử dụng:
        pipeline = ReceiptKIEPipeline(device="cpu")
        results  = pipeline.run(image_dir="./images", output_json="./out.json")
    """

    SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png"}

    def __init__(self, device: str = "cpu", prompt: str = KIE_PROMPT):
        self.loader     = VLMLoader(device=device)
        self.inferencer = VLMInferencer(loader=self.loader, prompt=prompt)
        self.parser     = KIEParser()

    def _collect_images(self, image_dir: str) -> list[Path]:
        img_dir = Path(image_dir)
        if not img_dir.exists():
            raise FileNotFoundError(f"Thư mục không tồn tại: {image_dir}")
        return sorted(
            f for f in img_dir.iterdir()
            if f.suffix.lower() in self.SUPPORTED_EXTENSIONS
        )

    def process_image(self, image_path: Path) -> dict:
        """Chạy VLM + parse KIE cho 1 ảnh."""
        print(f"[IMG] {image_path.name}")
        try:
            raw_text = self.inferencer.predict(str(image_path))
            preview  = raw_text[:200] + ("..." if len(raw_text) > 200 else "")
            print(f"  [VLM] {preview}")
            result = self.parser.parse(raw_text)
        except Exception as exc:
            print(f"  [ERROR] {exc}")
            result = {"company": None, "date": None, "total": None, "error": str(exc)}

        result["image"] = image_path.name
        print(f"  company : {result.get('company')}")
        print(f"  date    : {result.get('date')}")
        print(f"  total   : {result.get('total')}\n")
        return result

    @staticmethod
    def _save_json(data: dict, output_path: str) -> None:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"[DONE] {len(data)} ảnh → {output_path}")

    def run(
        self,
        image_dir: str = DEFAULT_IMAGE_DIR,
        output_json: str = DEFAULT_OUTPUT_JSON,
    ) -> dict:
        images = self._collect_images(image_dir)
        if not images:
            print(f"[ERROR] Không có ảnh trong: {image_dir}")
            return {}

        print(f"[INPUT] {len(images)} ảnh trong '{image_dir}':")
        for img in images:
            print(f"  {img.name}")
        print()

        self.loader.load()

        final = {}
        for img_path in images:
            final[img_path.name] = self.process_image(img_path)

        self._save_json(final, output_json)
        return final


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="KIE receipt bằng PaddleOCR-VL")
    parser.add_argument("--images", default=DEFAULT_IMAGE_DIR,   help="Thư mục chứa ảnh")
    parser.add_argument("--output", default=DEFAULT_OUTPUT_JSON, help="File JSON kết quả")
    parser.add_argument("--device", default="cpu",               help="cpu | gpu:0")
    args, _ = parser.parse_known_args()

    kie = ReceiptKIEPipeline(device=args.device)
    kie.run(image_dir=args.images, output_json=args.output)
