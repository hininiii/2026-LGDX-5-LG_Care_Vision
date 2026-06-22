from fastapi.testclient import TestClient
import csv
import json

from app.main import app
from app.yolo_filter_service import (
    FilterDetectionService,
    _expand_aircon_part_box,
    _normalize_model_profile,
)


def test_filter_detection_returns_mock_bbox_without_best_pt():
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/ar/filter-detect",
            json={
                "image_width": 640,
                "image_height": 480,
                "mock_fallback": True,
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["mode"] in {"mock", "yolo"}
    assert body["image_width"] == 640
    assert body["image_height"] == 480
    assert len(body["detections"]) >= 1
    detection = body["detections"][0]
    assert detection["class_name"] == "filter"
    assert detection["width"] > 0
    assert detection["height"] > 0


def test_aircon_part_classes_are_treated_as_aircon():
    detections = [
        {
            "x": 10,
            "y": 20,
            "width": 100,
            "height": 50,
            "confidence": 0.83,
            "class_name": "aircon-top",
        },
        {
            "x": 15,
            "y": 80,
            "width": 100,
            "height": 30,
            "confidence": 0.72,
            "class_name": "aircon-bottom",
        },
    ]

    filtered = FilterDetectionService._filter_detections(
        detections,
        confidence_threshold=0.5,
        target_classes=["aircon"],
        require_context_classes=None,
    )

    assert len(filtered) == 2


def test_aircon_detection_requires_wall_mounted_shape():
    detections = [
        {
            "x": 20,
            "y": 40,
            "width": 320,
            "height": 120,
            "confidence": 0.49,
            "class_name": "aircon",
        },
        {
            "x": 40,
            "y": 80,
            "width": 230,
            "height": 170,
            "confidence": 0.49,
            "class_name": "aircon",
        },
    ]

    filtered = FilterDetectionService._filter_detections(
        detections,
        confidence_threshold=0.25,
        target_classes=["aircon"],
        require_context_classes=None,
    )

    assert len(filtered) == 1
    assert filtered[0]["width"] == 320


def test_outlet_detection_requires_aircon_context_and_lower_region():
    detections = [
        {
            "x": 20,
            "y": 40,
            "width": 320,
            "height": 160,
            "confidence": 0.42,
            "class_name": "aircon",
        },
        {
            "x": 75,
            "y": 155,
            "width": 230,
            "height": 18,
            "confidence": 0.68,
            "class_name": "outlet",
        },
    ]

    filtered = FilterDetectionService._filter_detections(
        detections,
        confidence_threshold=0.60,
        target_classes=["outlet"],
        require_context_classes=["aircon"],
    )

    assert len(filtered) == 1
    assert filtered[0]["class_name"] == "outlet"


def test_outlet_detection_rejects_outlet_without_aircon_context():
    detections = [
        {
            "x": 75,
            "y": 155,
            "width": 230,
            "height": 18,
            "confidence": 0.91,
            "class_name": "outlet",
        },
    ]

    filtered = FilterDetectionService._filter_detections(
        detections,
        confidence_threshold=0.60,
        target_classes=["outlet"],
        require_context_classes=["aircon"],
    )

    assert filtered == []


def test_outlet_detection_rejects_low_confidence_and_wrong_position():
    detections = [
        {
            "x": 20,
            "y": 40,
            "width": 320,
            "height": 160,
            "confidence": 0.80,
            "class_name": "aircon",
        },
        {
            "x": 75,
            "y": 155,
            "width": 230,
            "height": 18,
            "confidence": 0.48,
            "class_name": "outlet",
        },
        {
            "x": 75,
            "y": 50,
            "width": 230,
            "height": 18,
            "confidence": 0.82,
            "class_name": "outlet",
        },
    ]

    filtered = FilterDetectionService._filter_detections(
        detections,
        confidence_threshold=0.35,
        target_classes=["outlet"],
        require_context_classes=["aircon"],
    )

    assert filtered == []


def test_aircon_bottom_box_expands_to_body_region():
    x1, y1, x2, y2 = _expand_aircon_part_box(
        "aircon-bottom",
        x1=100,
        y1=260,
        x2=400,
        y2=310,
        image_width=500,
        image_height=400,
    )

    assert x1 < 100
    assert y1 < 150
    assert x2 > 400
    assert y2 > 310


def test_no_cooling_procedure_uses_self_as_model_profile():
    assert _normalize_model_profile("self_care", "no_cooling_self_check") == "self_as_no_cooling"
    assert _normalize_model_profile(None, "no_cooling_self_check") == "self_as_no_cooling"
    assert _normalize_model_profile("self_as_no_cooling", "no_cooling_self_check") == "self_as_no_cooling"


def test_camera_review_capture_saves_false_positive_hard_negative(tmp_path, monkeypatch):
    monkeypatch.setenv("CARESHOT_AR_CAMERA_REVIEW_ROOT", str(tmp_path))
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/ar/camera-review-capture",
            json={
                "image_base64": "R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw==",
                "issue_type": "false_positive",
                "expected_class": "",
                "predicted_class": "filter",
                "confidence": 0.61,
                "step_index": 1,
                "step_title": "Turn off power",
                "target_classes": ["aircon", "aircon-bottom"],
                "session": "pytest",
                "notes": "keyboard false positive",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["saved"] is True
    paths = body["paths"]
    assert paths["image_path"]
    assert paths["csv_manifest"]
    assert paths["jsonl_manifest"]
    assert paths["yolo_image_path"]
    assert paths["yolo_label_path"]

    from pathlib import Path

    assert Path(paths["image_path"]).exists()
    with Path(paths["csv_manifest"]).open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 1
    assert rows[0]["issue_type"] == "false_positive"
    jsonl_rows = [
        json.loads(line)
        for line in Path(paths["jsonl_manifest"]).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(jsonl_rows) == 1
    assert jsonl_rows[0]["issue_type"] == "false_positive"
    assert Path(paths["yolo_image_path"]).exists()
    assert Path(paths["yolo_label_path"]).read_text(encoding="utf-8") == ""
