"""
AI image analysis for DrainGuard AI.

Model: torchvision Faster R-CNN with MobileNetV3-Large-320 FPN, pretrained on
COCO. It runs on CPU and returns real class labels, confidence scores and boxes.

IMPORTANT LIMITATION: COCO classes (bottle, cup, bag, ...) are general object
categories. They are NOT trained on drain blockages and are NOT validated for
drain or litter assessment. Outputs are shown as detector labels only and are
never used to claim a drain is blocked.

Torch is an optional dependency (see requirements-ai.txt). Torch imports are
kept inside functions so the rest of the app works without them.
"""

from collections import Counter
from dataclasses import dataclass

from PIL import Image, ImageDraw

SCORE_THRESHOLD = 0.35
MODEL_NAME = "Faster R-CNN MobileNetV3-Large-320 FPN"
MODEL_VERSION = "torchvision default weights"
MODEL_DATASET_NAME = "COCO object detection categories"
MODEL_SOURCE_NAME = "torchvision pretrained detection model"
MODEL_SOURCE_URL = (
    "https://pytorch.org/vision/stable/models/generated/"
    "torchvision.models.detection.fasterrcnn_mobilenet_v3_large_320_fpn.html"
)

LIMITATION_TEXT = (
    "Limitation: this detector was trained on COCO general object categories, "
    "not on drain blockages or litter-specific data, and has not been validated "
    "for this task. Detections are shown for transparency and do not, on their "
    "own, establish that a drain is blocked."
)


@dataclass
class Detection:
    label: str
    score: float
    box: tuple[float, float, float, float]


def detector_status() -> tuple[bool, str]:
    """Return (available, message) describing whether the AI detector can run."""
    try:
        import torch  # noqa: F401
        import torchvision  # noqa: F401
    except ImportError:
        return False, (
            "AI detector not installed. Run: pip install -r requirements-ai.txt "
            "(the rest of the app works without it)."
        )
    return True, (
        f"AI detector ready: COCO-pretrained {MODEL_NAME} (CPU). "
        "Weights are downloaded once on first use."
    )


def detections_to_records(detections: list[Detection]) -> list[dict]:
    """Serialize detections for provenance storage."""
    return [
        {"label": det.label, "score": det.score, "box": list(det.box)}
        for det in detections
    ]


def load_detector() -> dict:
    """Load the pretrained detector. Raises ImportError if torch is missing."""
    import torch
    import torchvision
    from torchvision.models.detection import (
        FasterRCNN_MobileNet_V3_Large_320_FPN_Weights,
        fasterrcnn_mobilenet_v3_large_320_fpn,
    )

    weights = FasterRCNN_MobileNet_V3_Large_320_FPN_Weights.DEFAULT
    # weights_backbone=None avoids downloading a second, unused backbone file.
    model = fasterrcnn_mobilenet_v3_large_320_fpn(weights=weights, weights_backbone=None)
    model.eval()
    return {
        "torch": torch,
        "to_tensor": torchvision.transforms.functional.to_tensor,
        "model": model,
        "categories": list(weights.meta["categories"]),
    }


def filter_detections(raw: list[dict], categories: list[str],
                      threshold: float = SCORE_THRESHOLD) -> list[Detection]:
    """Convert raw model outputs into Detections, dropping low-confidence ones."""
    detections = []
    for item in raw:
        if item["score"] < threshold:
            continue
        label_id = item["label_id"]
        name = categories[label_id] if 0 <= label_id < len(categories) else f"class {label_id}"
        detections.append(Detection(label=name, score=item["score"], box=tuple(item["box"])))
    return sorted(detections, key=lambda d: d.score, reverse=True)


def run_detector(bundle: dict, image: Image.Image,
                 threshold: float = SCORE_THRESHOLD) -> list[Detection]:
    """Run real CPU inference on a PIL image."""
    torch = bundle["torch"]
    tensor = bundle["to_tensor"](image.convert("RGB"))
    with torch.no_grad():
        output = bundle["model"]([tensor])[0]
    raw = [
        {"label_id": int(label), "score": float(score), "box": [float(v) for v in box]}
        for label, score, box in zip(
            output["labels"].tolist(), output["scores"].tolist(), output["boxes"].tolist()
        )
    ]
    return filter_detections(raw, bundle["categories"], threshold)


def summarize(detections: list[Detection]) -> str:
    """Plain-language summary of detector output, with the limitation stated."""
    if not detections:
        return (
            f"No objects above the {SCORE_THRESHOLD:.2f} confidence threshold were "
            "detected by the general-purpose COCO detector. This does not mean the "
            "drain is clear."
        )
    counts = Counter(d.label for d in detections)
    parts = ", ".join(f"{count} x {label}" for label, count in counts.most_common())
    return (
        f"Detected (COCO classes, threshold {SCORE_THRESHOLD:.2f}): {parts}. "
        "These are general object labels, not drain-blockage findings."
    )


def render_annotated(image: Image.Image, detections: list[Detection]) -> Image.Image:
    """Return a copy of the image with boxes and labels drawn on it."""
    annotated = image.convert("RGB").copy()
    draw = ImageDraw.Draw(annotated)
    for det in detections:
        x1, y1, x2, y2 = det.box
        draw.rectangle([x1, y1, x2, y2], outline=(15, 118, 110), width=3)
        draw.text((x1 + 3, max(0, y1 - 12)), f"{det.label} {det.score:.2f}",
                  fill=(15, 118, 110))
    return annotated
