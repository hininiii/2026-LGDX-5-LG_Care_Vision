export interface DetectionBox {
  x: number;
  y: number;
  width: number;
  height: number;
  confidence: number;
  class_name: string;
}

export interface FilterDetectionResponse {
  model_loaded: boolean;
  mode: "yolo" | "mock" | "none";
  model_profile?: string | null;
  model_path?: string | null;
  image_width: number;
  image_height: number;
  detections: DetectionBox[];
  message?: string | null;
}

export type CameraState = "loading" | "ready" | "denied";
export type DetectionMode = "yolo" | "mock" | "none";

export const CAPTURE_WIDTH = 416;

export const smoothBox = (previous: DetectionBox | null, next: DetectionBox, alpha = 0.35): DetectionBox => {
  if (!previous) return next;
  return {
    ...next,
    x: previous.x + (next.x - previous.x) * alpha,
    y: previous.y + (next.y - previous.y) * alpha,
    width: previous.width + (next.width - previous.width) * alpha,
    height: previous.height + (next.height - previous.height) * alpha,
  };
};

export const getCaptureSizeFromDimensions = (videoWidth: number, videoHeight: number) => {
  const sourceRatio = videoHeight ? videoWidth / videoHeight : 4 / 3;
  return {
    width: CAPTURE_WIDTH,
    height: Math.max(1, Math.round(CAPTURE_WIDTH / sourceRatio)),
  };
};

export const getObjectCoverTransform = (
  containerWidth: number,
  containerHeight: number,
  sourceWidth: number,
  sourceHeight: number,
) => {
  const sourceRatio = sourceWidth / Math.max(1, sourceHeight);
  const containerRatio = containerWidth / Math.max(1, containerHeight);
  if (sourceRatio > containerRatio) {
    const renderedWidth = containerHeight * sourceRatio;
    return {
      offsetX: (containerWidth - renderedWidth) / 2,
      offsetY: 0,
      scaleX: renderedWidth / sourceWidth,
      scaleY: containerHeight / sourceHeight,
    };
  }

  const renderedHeight = containerWidth / sourceRatio;
  return {
    offsetX: 0,
    offsetY: (containerHeight - renderedHeight) / 2,
    scaleX: containerWidth / sourceWidth,
    scaleY: renderedHeight / sourceHeight,
  };
};
