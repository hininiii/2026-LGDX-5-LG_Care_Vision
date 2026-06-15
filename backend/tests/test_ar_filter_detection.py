from fastapi.testclient import TestClient

from app.main import app


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
