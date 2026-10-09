from PIL import Image

from drainguard.vision import (
    LIMITATION_TEXT,
    SCORE_THRESHOLD,
    detections_to_records,
    filter_detections,
    render_annotated,
    summarize,
    detector_status,
)

CATEGORIES = ["__background__", "bottle", "cup", "bag"]
RAW = [
    {"label_id": 1, "score": 0.90, "box": [10, 10, 50, 50]},
    {"label_id": 3, "score": 0.20, "box": [0, 0, 5, 5]},   # below threshold
    {"label_id": 2, "score": 0.50, "box": [20, 20, 30, 40]},
    {"label_id": 99, "score": 0.80, "box": [1, 1, 2, 2]},  # unknown id
]


def test_filter_drops_low_confidence_and_sorts_by_score():
    dets = filter_detections(RAW, CATEGORIES, threshold=0.35)
    assert [d.label for d in dets] == ["bottle", "class 99", "cup"]
    assert dets[0].score == 0.90


def test_summary_empty_says_not_clear_claim():
    text = summarize([])
    assert "does not mean the drain is clear" in text


def test_summary_counts_labels():
    dets = filter_detections(RAW, CATEGORIES, threshold=SCORE_THRESHOLD)
    text = summarize(dets)
    assert "1 x bottle" in text
    assert "not drain-blockage findings" in text


def test_annotated_image_keeps_size():
    img = Image.new("RGB", (120, 90), "white")
    dets = filter_detections(RAW, CATEGORIES)
    out = render_annotated(img, dets)
    assert out.size == img.size


def test_detector_status_returns_flag_and_message():
    available, message = detector_status()
    assert isinstance(available, bool)
    assert isinstance(message, str) and message


def test_limitation_text_is_present():
    assert "not on drain blockages" in LIMITATION_TEXT


def test_detections_to_records_serializes_model_output():
    dets = filter_detections(RAW, CATEGORIES, threshold=SCORE_THRESHOLD)
    records = detections_to_records(dets)
    assert records[0]["label"] == "bottle"
    assert isinstance(records[0]["box"], list)
