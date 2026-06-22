from __future__ import annotations

import base64
import io
import os
from functools import lru_cache
from pathlib import Path
from typing import Any


YOLO_INFERENCE_CONFIDENCE_FLOOR = 0.25
FILTER_STRONG_CONFIDENCE_WITHOUT_CONTEXT = 0.70
AIRCON_MIN_ASPECT_RATIO = 1.75
AIRCON_CONTEXT_MIN_CONFIDENCE = 0.35
OUTLET_MIN_CONFIDENCE = 0.50
OUTLET_MIN_ASPECT_RATIO = 2.5
OUTLET_MAX_ASPECT_RATIO = 24.0
OUTLET_MIN_WIDTH_PX = 24.0
OUTLET_MIN_HEIGHT_PX = 4.0
AIRCON_CLASS_ALIASES = {
    "aircon": "aircon",
    "aircon-top": "aircon",
    "aircon-bottom": "aircon",
}


def _normalize_class_name(class_name: str) -> str:
    return AIRCON_CLASS_ALIASES.get(class_name, class_name)


def _looks_like_wall_mounted_aircon(detection: dict[str, float | str]) -> bool:
    width = float(detection.get("width", 0.0))
    height = float(detection.get("height", 0.0))
    if width <= 0.0 or height <= 0.0:
        return False
    return width / height >= AIRCON_MIN_ASPECT_RATIO


def _context_confidence_threshold(class_name: str, requested_threshold: float) -> float:
    if class_name == "aircon":
        return min(requested_threshold, AIRCON_CONTEXT_MIN_CONFIDENCE)
    return requested_threshold


def _looks_like_air_outlet(detection: dict[str, float | str]) -> bool:
    width = float(detection.get("width", 0.0))
    height = float(detection.get("height", 0.0))
    if width < OUTLET_MIN_WIDTH_PX or height < OUTLET_MIN_HEIGHT_PX:
        return False
    aspect_ratio = width / height
    return OUTLET_MIN_ASPECT_RATIO <= aspect_ratio <= OUTLET_MAX_ASPECT_RATIO


def _box_edges(detection: dict[str, float | str]) -> tuple[float, float, float, float]:
    x1 = float(detection.get("x", 0.0))
    y1 = float(detection.get("y", 0.0))
    width = float(detection.get("width", 0.0))
    height = float(detection.get("height", 0.0))
    return x1, y1, x1 + width, y1 + height


def _outlet_sits_in_aircon_lower_region(
    outlet: dict[str, float | str],
    aircon: dict[str, float | str],
) -> bool:
    aircon_x1, aircon_y1, aircon_x2, aircon_y2 = _box_edges(aircon)
    outlet_x1, outlet_y1, outlet_x2, outlet_y2 = _box_edges(outlet)
    aircon_width = max(1.0, aircon_x2 - aircon_x1)
    aircon_height = max(1.0, aircon_y2 - aircon_y1)
    outlet_width = max(0.0, outlet_x2 - outlet_x1)
    outlet_height = max(0.0, outlet_y2 - outlet_y1)
    outlet_center_x = (outlet_x1 + outlet_x2) / 2.0
    outlet_center_y = (outlet_y1 + outlet_y2) / 2.0

    horizontal_margin = aircon_width * 0.10
    if outlet_center_x < aircon_x1 - horizontal_margin or outlet_center_x > aircon_x2 + horizontal_margin:
        return False
    if outlet_center_y < aircon_y1 + aircon_height * 0.35:
        return False
    if outlet_center_y > aircon_y2 + aircon_height * 0.18:
        return False
    if outlet_width > aircon_width * 1.10:
        return False
    if outlet_width < aircon_width * 0.18:
        return False
    if outlet_height > aircon_height * 0.55:
        return False
    return True


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def _expand_aircon_part_box(
    source_class_name: str,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    image_width: int,
    image_height: int,
) -> tuple[float, float, float, float]:
    if source_class_name not in {"aircon-top", "aircon-bottom"}:
        return x1, y1, x2, y2

    width = max(1.0, x2 - x1)
    height = max(1.0, y2 - y1)
    expanded_x1 = x1 - width * 0.08
    expanded_x2 = x2 + width * 0.08

    if source_class_name == "aircon-bottom":
        expanded_y1 = y1 - height * 2.8
        expanded_y2 = y2 + height * 0.45
    else:
        expanded_y1 = y1 - height * 0.25
        expanded_y2 = y2 + height * 2.8

    return (
        _clamp(expanded_x1, 0.0, float(image_width)),
        _clamp(expanded_y1, 0.0, float(image_height)),
        _clamp(expanded_x2, 0.0, float(image_width)),
        _clamp(expanded_y2, 0.0, float(image_height)),
    )


def _default_model_path() -> Path:
    ar_2class_model = _model_root() / "ar_2class_detection" / "best.pt"
    if ar_2class_model.exists():
        return ar_2class_model
    ar_multiclass_model = _model_root() / "ar_multiclass_detection" / "best.pt"
    if ar_multiclass_model.exists():
        return ar_multiclass_model
    return _model_root() / "filter_detection" / "best.pt"


def _model_root() -> Path:
    return Path(__file__).resolve().parents[1] / "models"


def _latest_existing_model(pattern: str) -> Path | None:
    candidates = sorted(
        (path for path in _model_root().glob(pattern) if (path / "best.pt").exists()),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        return None
    return candidates[0] / "best.pt"


def _normalize_model_profile(model_profile: str | None, procedure_type: str | None) -> str:
    value = (model_profile or "").strip()
    procedure = (procedure_type or "").strip()
    if procedure == "no_cooling_self_check":
        return "self_as_no_cooling"
    if value in {"self_as", "self_as_no_cooling", "no_cooling_self_check"}:
        return "self_as_no_cooling"
    if value == "self_care":
        return "self_care"
    return "self_care"


def _model_path_for_profile(model_profile: str) -> Path:
    if model_profile == "self_as_no_cooling":
        configured = os.getenv("CARESHOT_AR_SELF_AS_YOLO_MODEL_PATH")
        if configured:
            return Path(configured)
        stable = _model_root() / "ar_self_as_no_cooling_detection" / "best.pt"
        if stable.exists():
            return stable
        latest_outlet = _latest_existing_model("ar_self_as_no_cooling_detection_outlet_*")
        if latest_outlet:
            return latest_outlet
        firstpass = _model_root() / "ar_self_as_no_cooling_detection_20260617_firstpass" / "best.pt"
        if firstpass.exists():
            return firstpass
    return _default_model_path()


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
    def __init__(self, model_path: Path | None = None, model_profile: str = "self_care") -> None:
        configured = os.getenv("CARESHOT_AR_YOLO_MODEL_PATH") or os.getenv("CARESHOT_FILTER_YOLO_MODEL_PATH")
        self.model_profile = model_profile
        self.model_path = Path(configured) if configured and model_profile == "self_care" else (
            model_path or _model_path_for_profile(model_profile)
        )
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
        target_classes: list[str] | None = None,
        require_context_classes: list[str] | None = None,
        mock_fallback: bool = False,
        debug_detections: bool = False,
    ) -> dict[str, Any]:
        model = self._load_model()
        if model is not None and image_payload:
            raw_detections = self._detect_with_yolo(
                model=model,
                image_payload=image_payload,
                confidence_threshold=confidence_threshold,
            )
            detections = self._filter_detections(
                raw_detections,
                confidence_threshold=confidence_threshold,
                target_classes=target_classes,
                require_context_classes=require_context_classes,
            )
            response: dict[str, Any] = {
                "model_loaded": True,
                "mode": "yolo",
                "model_profile": self.model_profile,
                "model_path": str(self.model_path),
                "image_width": image_width,
                "image_height": image_height,
                "detections": detections,
                "message": None,
            }
            if debug_detections:
                response["raw_detections"] = raw_detections
                response["filtered_detections"] = detections
            return response

        if mock_fallback:
            return {
                "model_loaded": False,
                "mode": "mock",
                "model_profile": self.model_profile,
                "model_path": str(self.model_path),
                "image_width": image_width,
                "image_height": image_height,
                "detections": [self._mock_filter_box(image_width, image_height)],
                "message": self._load_error or "YOLO model is not configured; mock bbox returned.",
            }

        return {
            "model_loaded": False,
            "mode": "none",
            "model_profile": self.model_profile,
            "model_path": str(self.model_path),
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
            image_width, image_height = image.size
            inference_confidence = min(confidence_threshold, YOLO_INFERENCE_CONFIDENCE_FLOOR)
            results = model.predict(image, conf=inference_confidence, verbose=False)
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
                source_class_name = str(names.get(cls_id, "filter"))
                class_name = _normalize_class_name(source_class_name)
                x1, y1, x2, y2 = [float(v) for v in box.xyxy[0].tolist()]
                x1, y1, x2, y2 = _expand_aircon_part_box(
                    source_class_name,
                    x1,
                    y1,
                    x2,
                    y2,
                    image_width=image_width,
                    image_height=image_height,
                )
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
    def _filter_detections(
        detections: list[dict[str, float | str]],
        confidence_threshold: float,
        target_classes: list[str] | None,
        require_context_classes: list[str] | None,
    ) -> list[dict[str, float | str]]:
        normalized_targets = {
            _normalize_class_name(value.strip()) for value in target_classes or [] if value.strip()
        }
        normalized_context = {
            _normalize_class_name(value.strip()) for value in require_context_classes or [] if value.strip()
        }
        context_detections = [
            {**detection, "class_name": _normalize_class_name(str(detection.get("class_name")))}
            for detection in detections
            if _normalize_class_name(str(detection.get("class_name"))) in normalized_context
            and float(detection.get("confidence", 0.0)) >= _context_confidence_threshold(
                _normalize_class_name(str(detection.get("class_name"))),
                confidence_threshold,
            )
            and (
                _normalize_class_name(str(detection.get("class_name"))) != "aircon"
                or _looks_like_wall_mounted_aircon(detection)
            )
        ]
        context_present = True
        if normalized_context:
            context_present = bool(context_detections)

        aircon_context_detections = [
            {**detection, "class_name": _normalize_class_name(str(detection.get("class_name")))}
            for detection in detections
            if _normalize_class_name(str(detection.get("class_name"))) == "aircon"
            and float(detection.get("confidence", 0.0)) >= AIRCON_CONTEXT_MIN_CONFIDENCE
            and _looks_like_wall_mounted_aircon(detection)
        ]

        filtered: list[dict[str, float | str]] = []
        for detection in detections:
            class_name = _normalize_class_name(str(detection.get("class_name")))
            confidence = float(detection.get("confidence", 0.0))
            if confidence < confidence_threshold:
                continue
            if normalized_targets and class_name not in normalized_targets:
                continue
            if class_name == "aircon" and not _looks_like_wall_mounted_aircon(detection):
                continue
            if class_name == "outlet":
                if confidence < OUTLET_MIN_CONFIDENCE:
                    continue
                if not _looks_like_air_outlet(detection):
                    continue
                if not any(
                    _outlet_sits_in_aircon_lower_region(detection, aircon_detection)
                    for aircon_detection in aircon_context_detections
                ):
                    continue
            if normalized_context and class_name not in normalized_context and not context_present:
                if class_name == "filter" and confidence >= FILTER_STRONG_CONFIDENCE_WITHOUT_CONTEXT:
                    pass
                else:
                    continue
            detection = {**detection, "class_name": class_name}
            filtered.append(detection)
        return filtered

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


@lru_cache(maxsize=4)
def get_filter_detection_service_for_profile(model_profile: str, procedure_type: str = "") -> FilterDetectionService:
    normalized = _normalize_model_profile(model_profile, procedure_type)
    return FilterDetectionService(model_profile=normalized)
