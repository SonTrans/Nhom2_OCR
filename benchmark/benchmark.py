from benchmark import adapter


def benchmark_model(output_model, model_OCR=None, model_KIE=None):
    output = None
    # OCR
    if model_KIE == None:
        if model_OCR == "PaddleOCR":
            output = adapter.PaddleOCR_to_string(output_model)
        elif model_OCR == "VietOCR":
            output = adapter.VietOCR_to_string(output_model)
        elif model_OCR == "Tesseract":
            output = adapter.Tesseract_to_string(output_model)
        else:
            return None

        feature = adapter.get_feature(output)

    # KIE
    else:
        if model_KIE == "Regex":
            output = adapter.Regex_to_dict(output_model)
        elif model_KIE == "LayoutLM":
            output = adapter.LayoutLM_to_dict(output_model)
        elif model_KIE == "VLM":
            output = adapter.VLM_to_dict(output_model)
        else:
            return None

        feature = output