from __future__ import annotations

import base64
import io
import os
from functools import lru_cache
from pathlib import Path
from typing import Any


def _default_model_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "03_AI로직"
        / "models"
        / "filter_detection"
        / "best.pt"
    )


def _strip_data_url(value: str) -> str:
    if "," in value and value.lstrip().startswith("data:"):
        return value.split(",", 1)[1]
    return value


def _decode_image_bytes(payload: str | None) -> bytes | None:
    if not payload:
        return None
    try:
        return base64.b64decode(_strip_data_url(payload), validate=False)
    except Exception:
        return None


class FilterDetectionService:
    def __init__(self, model_path: Path | None = None) -> None:
        configured = os.getenv("CARESHOT_FILTER_YOLO_MODEL_PATH")
        self.model_path = Path(configured) if configured else (model_path or _default_model_path())
        self._model: Any | None = None
        self._load_error: str | None = None

    @property
    def model_loaded(self) -> bool:
        return self._model is not None

    def _load_model(self) -> Any | None:
        if self._model is not None or self._load_error is not None:
            return self._model
        if not self.model_path.exists():
            self._load_error = f"YOLO model not found: {self.model_path}"
            return None
        try:
            from ultralytics import YOLO  # type: ignore

            self._model = YOLO(str(self.model_path))
        except Exception as exc:
            self._load_error = f"YOLO model load failed: {exc}"
        return self._model

    def detect(
        self,
        image_payload: str | None,
        image_width: int,
        image_height: int,
        confidence_threshold: float,
        mock_fallback: bool,
    ) -> dict[str, Any]:
        model = self._load_model()
        if model is not None and image_payload:
            detections = self._detect_with_yolo(
                model=model,
                image_payload=image_payload,
                confidence_threshold=confidence_threshold,
            )
            return {
                "model_loaded": True,
                "mode": "yolo",
                "image_width": image_width,
                "image_height": image_height,
                "detections": detections,
                "message": None,
            }

        if mock_fallback:
            return {
                "model_loaded": False,
                "mode": "mock",
                "image_width": image_width,
                "image_height": image_height,
                "detections": [self._mock_filter_box(image_width, image_height)],
                "message": self._load_error or "YOLO model is not configured; mock bbox returned.",
            }

        return {
            "model_loaded": False,
            "mode": "none",
            "image_width": image_width,
            "image_height": image_height,
            "detections": [],
            "message": self._load_error or "YOLO model is not configured.",
        }

    def _detect_with_yolo(
        self,
        model: Any,
        image_payload: str,
        confidence_threshold: float,
    ) -> list[dict[str, float | str]]:
        image_bytes = _decode_image_bytes(image_payload)
        if not image_bytes:
            return []
        try:
            from PIL import Image

            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            results = model.predict(image, conf=confidence_threshold, verbose=False)
        except Exception:
            return []

        detections: list[dict[str, float | str]] = []
        for result in results:
            names = getattr(result, "names", {}) or {}
            boxes = getattr(result, "boxes", None)
            if boxes is None:
                continue
            for box in boxes:
                cls_id = int(box.cls[0].item()) if getattr(box, "cls", None) is not None else 0
                class_name = str(names.get(cls_id, "filter"))
                if class_name != "filter":
                    continue
                x1, y1, x2, y2 = [float(v) for v in box.xyxy[0].tolist()]
                confidence = float(box.conf[0].item()) if getattr(box, "conf", None) is not None else 0.0
                detections.append(
                    {
                        "x": x1,
                        "y": y1,
                        "width": max(0.0, x2 - x1),
                        "height": max(0.0, y2 - y1),
                        "confidence": confidence,
                        "class_name": class_name,
                    }
                )
        return detections

    @staticmethod
    def _mock_filter_box(image_width: int, image_height: int) -> dict[str, float | str]:
        width = max(1.0, image_width * 0.58)
        height = max(1.0, image_height * 0.24)
        x = (image_width - width) / 2
        y = image_height * 0.34
        return {
            "x": x,
            "y": y,
            "width": width,
            "height": height,
            "confidence": 0.62,
            "class_name": "filter",
        }


@lru_cache(maxsize=1)
def get_filter_detection_service() -> FilterDetectionService:
    return FilterDetectionService()

