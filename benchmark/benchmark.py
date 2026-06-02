from benchmark import adapter
from jiwer import wer
import Levenshtein
import json

def benchmark_model(output_model, model_OCR=None, model_KIE=None, image="1005-receipt.jpg"):
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

        # Lấy ground_truth
        path_ground_truth = "data/ground_truth/OCR/lv1/"
        path_image = image.split(".")[0] + ".json"
        path = path_ground_truth + path_image
        with open(path) as json_file:
            ground_truth = json.load(json_file)

        # CER
        cer_score = wer.cer(output, ground_truth)

        # ANLS
        anls_score = anls(output, ground_truth)
        return {"cer_score": cer_score, "anls_score": anls_score}

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

        # dict -> string
        output_string = ""
        for i in output:
            output_string += output[i]

        # Lấy ground_truth
        path_ground_truth = "data/ground_truth/KIE/lv1/"
        path_image = image.split(".")[0] + ".json"
        path = path_ground_truth + path_image
        with open(path) as json_file:
            ground_truth = json.load(json_file)

        # dict -> string
        truth_string = ""
        for i in ground_truth:
            truth_string += ground_truth[i]

        anls_score = anls(output_string, truth_string)
        f1_score = f1(output, ground_truth)
        return f1_score + {"anls_score": anls_score}


def anls(gt, pred):

    distance = Levenshtein.distance(gt, pred)

    max_len = max(len(gt), len(pred))

    if max_len == 0:
        return 1.0

    anls = 1 - distance / max_len

    return max(anls, 0)

def f1(gt, pred):

    tp = 0
    fp = 0
    fn = 0

    for key in gt.keys():

        gt_value = str(gt[key]).strip()
        pred_value = str(pred.get(key, "")).strip()

        if gt_value == pred_value:
            tp += 1
        else:
            fp += 1
            fn += 1

    if tp == 0:
        return {
            "precision": 0.0,
            "recall": 0.0,
            "f1": 0.0
        }

    precision = tp / (tp + fp)
    recall = tp / (tp + fn)

    f1 = 2 * precision * recall / (precision + recall)

    return {
        "precision": precision,
        "recall": recall,
        "f1": f1
    }