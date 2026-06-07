import re
import json
import logging
import os
import tempfile

import gradio as gr
from PIL import Image

# ── Tat log on ao ─────────────────────────────────────────────────────────────
os.environ["GLOG_v"] = "0"
os.environ["FLAGS_call_stack_level"] = "0"
logging.getLogger("ppocr").setLevel(logging.ERROR)
logging.getLogger("paddle").setLevel(logging.ERROR)

# ── Config ────────────────────────────────────────────────────────────────────
DEVICE = "cpu"   # HF Spaces free tier chi co CPU

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
#  VLMLoader -- khoi tao pipeline PaddleOCR-VL tu paddlex
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class VLMLoader:
    """Khoi tao (lazy) pipeline PaddleOCR-VL tu paddlex."""

    PIPELINE_NAME = "PaddleOCR-VL"

    def __init__(self, device: str = "cpu"):
        self.device    = device
        self._pipeline = None

    def load(self):
        """Tai pipeline. Tra ve self de chain."""
        try:
            from paddlex import create_pipeline
        except ImportError:
            raise ImportError(
                "Thieu paddlex. Cai: pip install paddlepaddle paddleocr paddlex"
            )
        print(f"[MODEL] Khoi tao {self.PIPELINE_NAME} tren {self.device.upper()} ...")
        self._pipeline = create_pipeline(
            pipeline=self.PIPELINE_NAME,
            device=self.device,
        )
        print("[MODEL] San sang.\n")
        return self

    @property
    def pipeline(self):
        if self._pipeline is None:
            self.load()
        return self._pipeline


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  VLMInferencer -- chay inference cho 1 anh
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class VLMInferencer:
    """Gui anh + prompt vao PaddleOCR-VL, tra ve chuoi ket qua tho."""

    def __init__(self, loader: VLMLoader, prompt: str = KIE_PROMPT):
        self.loader = loader
        self.prompt = prompt

    def predict(self, image_path: str) -> str:
        """
        Chay PaddleOCR-VL, tra ve plain text ghep tu parsing_res_list.
        PaddleOCRVLResult chua data trong parsing_res_list la custom objects
        (khong phai dict) voi thuoc tinh: label, bbox, content.
        """
        results = self.loader.pipeline.predict(image_path, query=self.prompt)

        for res in results:
            def _get(key):
                return res[key] if isinstance(res, dict) else getattr(res, key, None)

            parsing = _get("parsing_res_list")
            if not parsing:
                return ""

            lines = []
            items = parsing if isinstance(parsing, list) else [parsing]
            for item in items:
                # Lay content: thu dict access truoc, roi attribute access
                if isinstance(item, dict):
                    label   = item.get("label", "")
                    content = item.get("content", "")
                else:
                    label   = getattr(item, "label",   "")
                    content = getattr(item, "content", "")

                content = str(content or "").strip()
                if not content:
                    continue

                # Strip HTML tags (table content la HTML)
                content_plain = re.sub(r"<[^>]+>", " ", content)
                content_plain = " ".join(content_plain.split())

                lines.append(content_plain)

            return "\n".join(lines)

        return ""


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  KIEParser -- regex KIE tren plain text tu parsing_res_list
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class KIEParser:
    """
    Trich xuat company / date / total bang regex tu plain text.
    plain text duoc ghep tu parsing_res_list cua PaddleOCRVLResult.
    """

    # Total keywords theo do uu tien giam dan
    _TOTAL_KEYWORDS = [
        r'(?:grand\s+total)',
        r'(?:order\s+total)',
        r'(?:t[o0]tal\s+(?:tax|amount|due)?)',
        r'(?:balance\s+due)',
        r'(?:take[\-\s]?[o0]ut\s+t[o0]tal)',
        r'(?:t[o0]ta[l\]1])',
        r'(?:subt[o0]tal)',
    ]
    _AMOUNT_PAT = r'[\$\s:=\-]*(\d+[.,]\d{2})'
    _DATE_PAT   = r'\b(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})\b'

    def parse(self, raw_text: str) -> dict:
        result = {"company": None, "date": None, "total": None}
        if not raw_text or not raw_text.strip():
            return result

        text = raw_text.replace("\r\n", "\n").replace("\r", "\n")
        lines = [l.strip() for l in text.split("\n") if l.strip()]

        # --- Company: dong dau tien khong rong ---
        if lines:
            company = re.sub(r'^[^a-zA-Z0-9\u00C0-\u024F]+', '', lines[0]).strip()
            result["company"] = company if company else lines[0]

        # --- Date ---
        m = re.search(self._DATE_PAT, text)
        if m:
            result["date"] = m.group(1)

        # --- Total (thu theo do uu tien) ---
        for kw in self._TOTAL_KEYWORDS:
            m = re.search(rf'(?i){kw}{self._AMOUNT_PAT}', text)
            if m:
                try:
                    result["total"] = float(m.group(1).replace(',', '.'))
                except ValueError:
                    pass
                break

        return result


# ── Khoi tao pipeline khi Space bat dau ──────────────────────────────────────
print("[MODEL] Dang tai PaddleOCR-VL pipeline...")
_loader     = VLMLoader(device=DEVICE)
_inferencer = VLMInferencer(loader=_loader, prompt=KIE_PROMPT)
_parser     = KIEParser()
_loader.load()
print("[MODEL] Pipeline san sang.\n")


# ── Ham xu ly mot anh (internal) ──────────────────────────────────────────────
def _process_single(image_path: str) -> dict:
    """Chay VLM + KIE cho 1 anh, tra ve dict ket qua."""
    try:
        raw_text   = _inferencer.predict(image_path)
        kie_result = _parser.parse(raw_text)

        # Them truong note thay cho ocr_text
        if not raw_text or not raw_text.strip():
            kie_result["note"] = "empty_ocr"
        else:
            missing = [k for k in ("company", "date", "total") if kie_result.get(k) is None]
            kie_result["note"] = f"missing: {', '.join(missing)}" if missing else "ok"

        return kie_result
    except Exception as e:
        return {"company": None, "date": None, "total": None, "note": f"error: {e}"}



# ── Ham xu ly chinh cho Gradio (1 anh) ───────────────────────────────────────
def process_image(image):
    """
    Nhan 1 anh tu Gradio (PIL.Image hoac duong dan file).
    Chay VLM + KIE, tra ve:
       - JSON ket qua (hien thi tren UI)
       - File JSON de tai ve
    """
    if image is None:
        return "{}", None

    # Gradio co the tra ve PIL.Image hoac duong dan file tuy phien ban
    if isinstance(image, str):
        img_path = image
    else:
        # PIL.Image -- luu tam ra file
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        image.save(tmp.name)
        img_path = tmp.name

    img_name = os.path.basename(img_path)
    print(f"[IMG] Dang xu ly: {img_name}")

    result = _process_single(img_path)
    result["image"] = img_name

    print(f"  company : {result.get('company')}")
    print(f"  date    : {result.get('date')}")
    print(f"  total   : {result.get('total')}")

    # Luu ket qua ra file JSON tam de user tai ve
    out_path = tempfile.mktemp(suffix="_vlm_results.json")
    with open(out_path, "w", encoding="utf-8") as fout:
        json.dump(result, fout, indent=4, ensure_ascii=False)

    json_str = json.dumps(result, indent=4, ensure_ascii=False)
    print("[DONE] Hoan thanh.")
    return json_str, out_path


# ── Giao dien Gradio ──────────────────────────────────────────────────────────
with gr.Blocks(title="Receipt KIE – PaddleOCR-VL") as demo:
    gr.Markdown(
        """
        # 🧾 Receipt Key Information Extraction
        Powered by **PaddleOCR-VL** (Vision Language Model – 0.9B)

        Upload **1 anh receipt** (.jpg / .png) de trich xuat
        **ten cua hang**, **ngay**, **tong tien**.
        """
    )

    with gr.Row():
        with gr.Column(scale=1):
            img_input = gr.Image(
                label="📷 Upload anh receipt",
                type="filepath",
            )
            run_btn = gr.Button("🔍 Phan tich anh", variant="primary")

        with gr.Column(scale=2):
            json_output = gr.Code(
                label="📊 Ket qua KIE (JSON)",
                language="json",
                interactive=False,
                lines=15,
            )
            dl_output = gr.File(
                label="⬇️ Tai ket qua JSON",
                interactive=False,
            )

    run_btn.click(
        fn=process_image,
        inputs=[img_input],
        outputs=[json_output, dl_output],
    )

if __name__ == "__main__":
    demo.launch()

