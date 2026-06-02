import pytesseract
from PIL import Image
from paddleocr import PaddleOCR
from vietocr.tool.predictor import Predictor
from vietocr.tool.config import Cfg
import os

# Tesseract path
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

config = Cfg.load_config_from_name('vgg_transformer')
config['cnn']['pretrained'] = False
config['device'] = 'cpu'
vietocr_engine = Predictor(config)

paddle_engine = PaddleOCR(use_textline_orientation=True, lang='en')

def run_tesseract(image_name, image_dir="test_images"):

    img_path = os.path.join(image_dir, image_name)
    img = Image.open(img_path)

    result = pytesseract.image_to_string(img, lang="vie+eng")

    return result

def run_vietocr(image_name, image_dir="test_images"):

    img_path = os.path.join(image_dir, image_name)
    img = Image.open(img_path)

    result = vietocr_engine.predict(img)

    return result

def run_paddleocr(image_name, image_dir="test_images"):

    img_path = os.path.join(image_dir, image_name)

    result = paddle_engine.ocr(img_path, cls=True)

    return result