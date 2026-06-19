import { useNavigate, useLocation } from "react-router";
import { useCallback, useEffect, useRef, useState } from "react";
import { ChevronLeft, Camera, Volume2, VolumeX, Lightbulb, Check, ArrowUp } from "lucide-react";
import { motion, AnimatePresence } from "motion/react";
import { API_BASE_URL } from "../api/client";
import {
  getCaptureSizeFromDimensions,
  getObjectCoverTransform,
  smoothBox,
  type DetectionBox,
  type DetectionMode,
  type FilterDetectionResponse,
  type CameraState,
} from "./arGuideDetection";

const CHAT_STORAGE_KEY = "chat_messages_v20260612";
const TTS_STORAGE_KEY = "careshot_ar_tts_enabled";

interface ARGuideStep {
  title: string;
  desc: string;
  tts_enabled?: boolean;
  tts_text?: string;
  tts_language_code?: string;
  tts_provider?: "web_speech" | string;
  audio_url?: string | null;
  safety?: string;
  hint?: string;
  targetHint?: string;
  targetClasses?: string[];
  contextClasses?: string[];
  sourceType?: string;
  sourceUrl?: string | null;
  sourceText?: string;
}

interface GuideDisplayStep {
  title?: string;
  text?: string;
  tts_enabled?: boolean;
  tts_text?: string;
  tts_language_code?: string;
  tts_provider?: "web_speech" | "google_cloud_tts" | string;
  audio_url?: string | null;
  source_type?: string;
  source_url?: string | null;
  source_text?: string;
}

interface ARGuideLocationState {
  from?: string;
  procedureType?: string;
  guideTitle?: string;
  guideSteps?: ARGuideStep[];
}

const defaultSteps: ARGuideStep[] = [
  {
    title: "Turn Off Power",
    desc: "Turn off the power and unplug the unit.",
    safety: "Move to the next step only after the power is completely off.",
    hint: "Press and hold the air conditioner power button\nor unplug it directly.",
    targetHint: "Air conditioner body",
    targetClasses: ["aircon"],
  },
  {
    title: "Open Cover",
    desc: "Slowly lift the filter cover.",
    safety: "If the cover is stuck, do not force it. Check the opening direction again.",
    hint: "Hold both sides of the filter cover\nand slowly lift it upward.",
    targetHint: "Air conditioner body",
    targetClasses: ["aircon"],
  },
  {
    title: "Remove Filter",
    desc: "Release both locks and remove the filter.",
    safety: "Check that the marked filter position matches your hand position before removing it.",
    hint: "Press the lock tabs on both sides of the filter\nand pull it downward.",
    targetHint: "Filter mesh",
    targetClasses: ["filter"],
    contextClasses: ["aircon"],
  },
  {
    title: "Wash and Dry",
    desc: "Rinse under running water, then dry in the shade.",
    safety: "Reinstall the filter only after it is completely dry.",
    hint: "Rinse only with lukewarm running water\nwithout detergent.",
    targetHint: "Removed filter",
    targetClasses: ["filter"],
  },
  {
    title: "Reinstall",
    desc: "Reinstall the filter and close the cover.",
    safety: "Check the filter direction and close the cover slowly.",
    hint: "After inserting the filter, press the cover\nuntil it clicks.",
    targetHint: "Air conditioner body",
    targetClasses: ["aircon"],
  },
];

const noCoolingSelfCheckSteps: ARGuideStep[] = [
  {
    title: "Check Temperature Setting",
    desc: "Check that the desired temperature is set lower than the current indoor temperature.",
    hint: "Set the target temperature lower\nthan the room temperature.",
    targetHint: "Air conditioner body",
    targetClasses: ["aircon"],
  },
  {
    title: "Check Filter Status",
    desc: "If the filter has a lot of dust, clean it and try operating again.",
    hint: "Look for dust buildup on the filter mesh\nbefore restarting the unit.",
    targetHint: "Filter mesh",
    targetClasses: ["filter"],
    contextClasses: ["aircon"],
  },
  {
    title: "Check Air Outlet",
    desc: "Check that nothing is blocking the air outlet or airflow path.",
    hint: "Keep curtains, furniture, and loose items\naway from the airflow path.",
    targetHint: "Air outlet / airflow path",
    targetClasses: ["outlet"],
    contextClasses: ["aircon"],
  },
  {
    title: "Check Indoor Environment",
    desc: "Check whether doors or windows are open or strong sunlight is coming in.",
    hint: "Close open windows and reduce direct sunlight\nbefore checking cooling again.",
    targetHint: "Air conditioner body",
    targetClasses: ["aircon"],
  },
  {
    title: "Request Professional Service",
    desc: "If cooling remains weak, request professional service.",
    hint: "If the symptom continues after self-check,\nconnect to professional service.",
    targetHint: "Air conditioner body",
    targetClasses: ["aircon"],
  },
];

const guideStepsByProcedure: Record<string, ARGuideStep[]> = {
  filter_cleaning: defaultSteps,
  no_cooling_self_check: noCoolingSelfCheckSteps,
};

const guideStepTargetsByProcedure: Record<
  string,
  Array<{ targetHint?: string; targetClasses?: string[]; contextClasses?: string[] }>
> = {
  filter_cleaning: defaultSteps.map(({ targetHint, targetClasses, contextClasses }) => ({
    targetHint,
    targetClasses,
    contextClasses,
  })),
  no_cooling_self_check: [
    { targetHint: "Air conditioner body", targetClasses: ["aircon"] },
    { targetHint: "Air conditioner body", targetClasses: ["aircon"] },
    { targetHint: "Air outlet / airflow path", targetClasses: ["outlet"], contextClasses: ["aircon"] },
    { targetHint: "Filter mesh", targetClasses: ["filter"], contextClasses: ["aircon"] },
    { targetHint: "Air conditioner body", targetClasses: ["aircon"] },
    { targetHint: "Air conditioner body", targetClasses: ["aircon"] },
    { targetHint: "Air conditioner body", targetClasses: ["aircon"] },
  ],
};

const guideStepsFromDisplaySteps = (procedureType: string, displaySteps?: GuideDisplayStep[]): ARGuideStep[] => {
  const targets = guideStepTargetsByProcedure[procedureType] ?? [];
  return (displaySteps ?? [])
    .map((step, index) => {
      const desc = (step.text || step.source_text || "").trim();
      if (!desc) return null;
      return {
        title: step.title || `STEP ${index + 1}`,
        desc,
        tts_enabled: step.tts_enabled ?? true,
        tts_text: step.tts_text || desc,
        tts_language_code: step.tts_language_code || "en-IN",
        tts_provider: step.tts_provider || "web_speech",
        audio_url: step.audio_url,
        hint: guideStepsByProcedure[procedureType]?.[index]?.hint,
        sourceType: step.source_type,
        sourceUrl: step.source_url,
        sourceText: step.source_text,
        ...(targets[index] ?? {}),
      };
    })
    .filter((step): step is ARGuideStep => Boolean(step));
};

const getCaptureSize = (video: HTMLVideoElement) => {
  return getCaptureSizeFromDimensions(video.videoWidth, video.videoHeight);
};

const detectionLabelMap: Record<string, string> = {
  filter: "필터",
  aircon: "에어컨",
  outlet: "토출구",
};

const DEFAULT_DETECTION_CONFIDENCE_THRESHOLD = 0.35;
const AIRCON_DETECTION_CONFIDENCE_THRESHOLD = 0.35;
const OUTLET_DETECTION_CONFIDENCE_THRESHOLD = 0.55;
const DETECTION_JPEG_QUALITY = 0.85;
const DETECTION_HOLD_MS = 1100;

const getDetectionLabel = (detection: DetectionBox) =>
  `${detectionLabelMap[detection.class_name] ?? detection.class_name} ${(
    detection.confidence * 100
  ).toFixed(0)}%`;

const formatDebugDetections = (detections?: DetectionBox[] | null) => {
  if (!detections?.length) return "none";
  return detections
    .slice(0, 5)
    .map((detection) => `${detection.class_name}:${(detection.confidence * 100).toFixed(0)}%`)
    .join(", ");
};

const getModelProfileForProcedure = (procedureType: string) =>
  procedureType === "no_cooling_self_check" ? "self_as_no_cooling" : "self_care";

const getConfidenceThresholdForStep = (step: ARGuideStep | undefined) => {
  const targetClasses = step?.targetClasses ?? [];
  if (targetClasses.includes("filter")) return DEFAULT_DETECTION_CONFIDENCE_THRESHOLD;
  if (targetClasses.includes("outlet")) return OUTLET_DETECTION_CONFIDENCE_THRESHOLD;
  if (targetClasses.includes("aircon")) return AIRCON_DETECTION_CONFIDENCE_THRESHOLD;
  return DEFAULT_DETECTION_CONFIDENCE_THRESHOLD;
};

const resolveAudioUrl = (audioUrl: string) => {
  if (!audioUrl.startsWith("/")) return audioUrl;
  const apiOrigin = new URL(API_BASE_URL, window.location.origin).origin;
  return `${apiOrigin}${audioUrl}`;
};

export function ARGuide() {
  const navigate = useNavigate();
  const location = useLocation();
  const routeState = (location.state as ARGuideLocationState | null) ?? {};
  const queryParams = new URLSearchParams(location.search);
  const queryProcedureType =
    queryParams.get("procedure_type") || queryParams.get("procedureType") || undefined;
  const debugDetectionEnabled =
    queryParams.get("debugDetection") === "1" || queryParams.get("debug_detection") === "1";
  const from = routeState.from ?? "/self-care";
  const procedureType = routeState.procedureType ?? queryProcedureType ?? "filter_cleaning";
  const [remoteGuideSteps, setRemoteGuideSteps] = useState<ARGuideStep[]>([]);
  const steps = routeState.guideSteps?.length
    ? routeState.guideSteps
    : remoteGuideSteps.length
      ? remoteGuideSteps
      : guideStepsByProcedure[procedureType] ?? defaultSteps;
  const [current, setCurrent] = useState(0);
  const [cameraState, setCameraState] = useState<CameraState>("loading");
  const [detectionMode, setDetectionMode] = useState<DetectionMode>("none");
  const [lastDetection, setLastDetection] = useState<DetectionBox | null>(null);
  const [detectionDebug, setDetectionDebug] = useState<FilterDetectionResponse | null>(null);
  const [statusText, setStatusText] = useState("카메라 준비 중");
  const [ttsEnabled, setTtsEnabled] = useState(() => localStorage.getItem(TTS_STORAGE_KEY) !== "false");
  const [ttsSupported] = useState(() => typeof window !== "undefined" && "speechSynthesis" in window);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const overlayRef = useRef<HTMLCanvasElement | null>(null);
  const captureRef = useRef<HTMLCanvasElement | null>(null);
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const audioObjectUrlRef = useRef<string | null>(null);
  const smoothedBoxRef = useRef<DetectionBox | null>(null);
  const lastDetectionAtRef = useRef(0);
  const currentStep = steps[current] ?? steps[0];

  useEffect(() => {
    if (current >= steps.length) setCurrent(0);
  }, [current, steps.length]);

  useEffect(() => {
    if (routeState.guideSteps?.length) return;
    let cancelled = false;
    const serviceFlowType = procedureType === "no_cooling_self_check" ? "self_as" : "self_care";
    const params = new URLSearchParams({
      user_id: "U001",
      device_id: "D001",
      procedure_type: procedureType,
      service_flow_type: serviceFlowType,
      language_code: "en",
    });

    fetch(`${API_BASE_URL}/v1/guides/options?${params.toString()}`)
      .then((response) => (response.ok ? response.json() : null))
      .then((data) => {
        if (cancelled || !data?.display_steps?.length) return;
        const nextSteps = guideStepsFromDisplaySteps(procedureType, data.display_steps);
        if (nextSteps.length) setRemoteGuideSteps(nextSteps);
      })
      .catch(() => {
        if (!cancelled) setRemoteGuideSteps([]);
      });

    return () => {
      cancelled = true;
    };
  }, [procedureType, routeState.guideSteps?.length]);

  const stopStepSpeech = useCallback(() => {
    if (ttsSupported) window.speechSynthesis.cancel();
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.src = "";
      audioRef.current = null;
    }
    if (audioObjectUrlRef.current) {
      URL.revokeObjectURL(audioObjectUrlRef.current);
      audioObjectUrlRef.current = null;
    }
    utteranceRef.current = null;
  }, [ttsSupported]);

  const speakWithWebSpeech = useCallback(
    (text: string) => {
      if (!ttsSupported) return;
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = currentStep.tts_language_code || "en-IN";
      utterance.rate = 0.92;
      utterance.pitch = 1;
      utterance.volume = 1;
      utteranceRef.current = utterance;
      window.speechSynthesis.speak(utterance);
    },
    [currentStep.tts_language_code, ttsSupported],
  );

  const speakCurrentStep = useCallback(
    async (force = false) => {
      if (!force && !ttsEnabled) return;
      if (currentStep.tts_enabled === false) return;
      const text = (currentStep.tts_text || currentStep.desc || "").trim();
      if (!text) return;

      stopStepSpeech();
      if (currentStep.tts_provider === "google_cloud_tts" || currentStep.audio_url) {
        try {
          const audioUrl =
            (currentStep.audio_url ? resolveAudioUrl(currentStep.audio_url) : "") ||
            URL.createObjectURL(
              await fetch(`${API_BASE_URL}/v1/tts/synthesize`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                  text,
                  language_code: currentStep.tts_language_code || "en-IN",
                  speaking_rate: 0.92,
                }),
              }).then((response) => {
                if (!response.ok) throw new Error(`Google TTS failed: ${response.status}`);
                return response.blob();
              }),
            );
          if (!currentStep.audio_url) audioObjectUrlRef.current = audioUrl;
          const audio = new Audio(audioUrl);
          audioRef.current = audio;
          await audio.play();
          return;
        } catch {
          stopStepSpeech();
        }
      }
      speakWithWebSpeech(text);
    },
    [currentStep, speakWithWebSpeech, stopStepSpeech, ttsEnabled],
  );

  useEffect(() => {
    if (!ttsSupported) return;
    speakCurrentStep(false);
    return () => stopStepSpeech();
  }, [current, speakCurrentStep, stopStepSpeech, ttsSupported]);

  useEffect(() => {
    const handleToggle = (event: Event) => {
      const enabled =
        event instanceof CustomEvent && typeof event.detail?.enabled === "boolean"
          ? event.detail.enabled
          : !ttsEnabled;
      setTtsEnabled(enabled);
      localStorage.setItem(TTS_STORAGE_KEY, String(enabled));
      if (!enabled) stopStepSpeech();
      if (enabled) speakCurrentStep(true);
    };
    const handleReplay = () => speakCurrentStep(true);
    const handleStop = () => stopStepSpeech();

    window.addEventListener("careshot:ar-tts:toggle", handleToggle);
    window.addEventListener("careshot:ar-tts:replay", handleReplay);
    window.addEventListener("careshot:ar-tts:stop", handleStop);
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement) return;
      const key = event.key.toLowerCase();
      if (key === "v") handleToggle(new CustomEvent("careshot:ar-tts:toggle"));
      if (key === "r") handleReplay();
      if (key === "s") handleStop();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("careshot:ar-tts:toggle", handleToggle);
      window.removeEventListener("careshot:ar-tts:replay", handleReplay);
      window.removeEventListener("careshot:ar-tts:stop", handleStop);
      window.removeEventListener("keydown", handleKeyDown);
      stopStepSpeech();
    };
  }, [speakCurrentStep, stopStepSpeech, ttsEnabled]);

  useEffect(() => {
    setLastDetection(null);
    smoothedBoxRef.current = null;
    lastDetectionAtRef.current = 0;
  }, [current]);

  useEffect(() => {
    let stream: MediaStream | null = null;
    let cancelled = false;

    async function startCamera() {
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: "environment", width: { ideal: 640 }, height: { ideal: 480 } },
          audio: false,
        });
        if (cancelled) return;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          await videoRef.current.play();
        }
        setCameraState("ready");
        setStatusText("확인 대상 탐지 중");
      } catch {
        setCameraState("denied");
        setStatusText("카메라 권한을 확인해주세요");
      }
    }

    startCamera();
    return () => {
      cancelled = true;
      stream?.getTracks().forEach((track) => track.stop());
    };
  }, []);

  useEffect(() => {
    if (cameraState !== "ready") return;

    let busy = false;
    const interval = window.setInterval(async () => {
      const video = videoRef.current;
      const canvas = captureRef.current;
      if (!video || !canvas || video.readyState < 2 || busy) return;

      const { width, height } = getCaptureSize(video);
      canvas.width = width;
      canvas.height = height;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;
      ctx.drawImage(video, 0, 0, width, height);
      const imageDataUrl = canvas.toDataURL("image/jpeg", DETECTION_JPEG_QUALITY);

      busy = true;
      try {
        const detectionModelProfile = getModelProfileForProcedure(procedureType);
        const detectionConfidenceThreshold = getConfidenceThresholdForStep(currentStep);
        const response = await fetch(`${API_BASE_URL}/v1/ar/filter-detect`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            image_data_url: imageDataUrl,
            image_width: width,
            image_height: height,
            confidence_threshold: detectionConfidenceThreshold,
            target_classes: currentStep.targetClasses ?? ["aircon"],
            require_context_classes: currentStep.contextClasses ?? null,
            model_profile: detectionModelProfile,
            procedure_type: procedureType,
            mock_fallback: false,
            debug_detections: debugDetectionEnabled,
          }),
        });
        if (!response.ok) throw new Error(`filter detect failed: ${response.status}`);
        const result = (await response.json()) as FilterDetectionResponse;
        setDetectionMode(result.mode);
        setDetectionDebug(debugDetectionEnabled ? result : null);
        const detection = result.detections[0] ?? null;
        if (detection) {
          const smoothed = smoothBox(smoothedBoxRef.current, detection);
          smoothedBoxRef.current = smoothed;
          setLastDetection(smoothed);
          lastDetectionAtRef.current = Date.now();
          const detectedLabel = detectionLabelMap[detection.class_name] ?? "확인 대상";
          setStatusText(result.mode === "mock" ? "확인 대상 예비 표시" : `${detectedLabel} 탐지됨`);
        } else {
          const shouldHoldLastDetection =
            smoothedBoxRef.current && Date.now() - lastDetectionAtRef.current <= DETECTION_HOLD_MS;
          if (shouldHoldLastDetection) {
            setLastDetection(smoothedBoxRef.current);
            setStatusText("탐지 유지 중");
          } else {
            setLastDetection(null);
            smoothedBoxRef.current = null;
            setStatusText("탐지 대기");
          }
        }
      } catch {
        setDetectionMode("none");
        setDetectionDebug(null);
        setStatusText("탐지 서버 연결 대기");
      } finally {
        busy = false;
      }
    }, 600);

    return () => window.clearInterval(interval);
  }, [cameraState, current, steps, procedureType, debugDetectionEnabled]);

  useEffect(() => {
    const canvas = overlayRef.current;
    const video = videoRef.current;
    if (!canvas || !video) return;

    const draw = () => {
      const rect = video.getBoundingClientRect();
      const width = Math.max(1, Math.round(rect.width));
      const height = Math.max(1, Math.round(rect.height));
      canvas.width = width;
      canvas.height = height;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;
      ctx.clearRect(0, 0, width, height);
      if (!lastDetection) return;

      const captureSize = getCaptureSize(video);
      const transform = getObjectCoverTransform(width, height, captureSize.width, captureSize.height);
      const x = transform.offsetX + lastDetection.x * transform.scaleX;
      const y = transform.offsetY + lastDetection.y * transform.scaleY;
      const boxWidth = lastDetection.width * transform.scaleX;
      const boxHeight = lastDetection.height * transform.scaleY;

      if (x + boxWidth < 0 || y + boxHeight < 0 || x > width || y > height) return;
      const visibleX = Math.max(0, x);
      const visibleY = Math.max(0, y);
      const visibleWidth = Math.min(width - visibleX, boxWidth - Math.max(0, -x));
      const visibleHeight = Math.min(height - visibleY, boxHeight - Math.max(0, -y));
      if (visibleWidth <= 0 || visibleHeight <= 0) return;

      ctx.strokeStyle = "#F77B50";
      ctx.lineWidth = 3;
      ctx.shadowColor = "rgba(247, 123, 80, 0.45)";
      ctx.shadowBlur = 12;
      ctx.strokeRect(visibleX, visibleY, visibleWidth, visibleHeight);
      ctx.shadowBlur = 0;
      ctx.fillStyle = "#F77B50";
      ctx.fillRect(visibleX, Math.max(0, visibleY - 28), 118, 24);
      ctx.fillStyle = "#fff";
      ctx.font = "12px sans-serif";
      ctx.fillText(
        getDetectionLabel(lastDetection),
        visibleX + 8,
        Math.max(16, visibleY - 11),
      );
    };

    draw();
  }, [lastDetection]);

  const goBack = () => navigate(from);
  const handlePrev = () => {
    if (current > 0) setCurrent(current - 1);
  };
  const handleNext = () => {
    if (current < steps.length - 1) {
      setCurrent(current + 1);
    } else {
      if (from === "/chat") {
        const saved = localStorage.getItem(CHAT_STORAGE_KEY);
        const messages = saved ? JSON.parse(saved) : [];
        const doneMsg = {
          id: Date.now().toString(),
          type: "bot",
          content: "Did you finish the AR guide?\nI'll record the care details.",
          time: new Date().toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit" }),
          showDoneAsk: true,
        };
        localStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify([...messages, doneMsg]));
      }
      navigate(from);
    }
  };
  return (
    <motion.div
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -14 }}
      transition={{ duration: 0.48, ease: [0.22, 1, 0.36, 1] }}
      className="relative flex h-full w-full flex-col overflow-hidden text-[#292B2E]"
      style={{ background: "linear-gradient(160deg, #d6f2e8 0%, #f0f8e8 30%, #fce8f0 65%, #ede8f8 100%)" }}
    >
      <header className="flex shrink-0 items-center justify-between px-[24px] pb-[24px] pt-[44px]">
        <button onClick={goBack} className="-ml-1 flex h-9 w-9 items-center justify-start" aria-label="Go back">
          <ChevronLeft size={32} strokeWidth={1.9} className="text-[#35383B]" />
        </button>
        <h1 className="text-[23px] font-semibold leading-none tracking-[0]">AR</h1>
        <div className="w-9" />
      </header>

      <nav className="flex shrink-0 items-center gap-[8px] px-[16px] pb-[16px]">
        {steps.map((_, idx) => {
          const isActive = idx === current;
          const isDone = idx < current;
          return (
            <div key={idx} className="flex flex-1 items-center">
              <motion.button
                onClick={() => setCurrent(idx)}
                aria-label={`STEP ${idx + 1}`}
                whileTap={{ scale: 0.95 }}
                transition={{ type: "spring", stiffness: 400, damping: 22 }}
                className="flex flex-1 flex-col items-center gap-[5px] rounded-[12px] py-[8px] transition-all"
                style={isActive ? {
                  background: "linear-gradient(135deg, #24C99A, #14B989)",
                  boxShadow: "0 4px 14px rgba(34,197,154,0.35), inset 0 1px 0 rgba(255,255,255,0.3)",
                  border: "1px solid rgba(255,255,255,0.3)",
                } : {
                  background: "rgba(255,255,255,0.45)",
                  backdropFilter: "blur(12px)",
                  WebkitBackdropFilter: "blur(12px)",
                  border: "1px solid rgba(255,255,255,0.65)",
                  boxShadow: "0 2px 8px rgba(31,69,61,0.06), inset 0 1px 0 rgba(255,255,255,0.8)",
                }}
              >
                {isDone
                  ? <Check size={14} strokeWidth={2.5} className="text-[#22C59A]" />
                  : <span className={`text-[11px] font-bold tracking-[0] ${isActive ? "text-white" : "text-[#B0B4B2]"}`}>{idx + 1}</span>
                }
              </motion.button>
            </div>
          );
        })}
      </nav>

      <main className="flex min-h-0 flex-1 flex-col gap-[12px] overflow-y-auto px-[12px] pb-[10px] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        <section className="relative flex flex-1 flex-col rounded-[18px] px-[14px] pb-[14px] pt-[14px]" style={{ background: "rgba(255,255,255,0.55)", backdropFilter: "blur(24px)", WebkitBackdropFilter: "blur(24px)", border: "1px solid rgba(255,255,255,0.75)", boxShadow: "0 16px 32px rgba(31,69,61,0.08), inset 0 1px 0 rgba(255,255,255,0.9)" }}>
          <button
            onClick={() => {
              const nextEnabled = !ttsEnabled;
              setTtsEnabled(nextEnabled);
              localStorage.setItem(TTS_STORAGE_KEY, String(nextEnabled));
              if (!nextEnabled) stopStepSpeech();
              if (nextEnabled) speakCurrentStep(true);
            }}
            className="absolute right-[12px] top-[22px] z-10 flex h-10 w-10 items-center justify-center rounded-full backdrop-blur-sm"
            style={{ background: "rgba(255,255,255,0.86)" }}
            aria-label="Voice guidance"
          >
            {ttsEnabled ? <Volume2 size={22} strokeWidth={1.9} className="text-[#35383B]" /> : <VolumeX size={22} strokeWidth={1.9} className="text-[#C7CECC]" />}
          </button>

          <AnimatePresence mode="wait">
            <motion.div
              key={current}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -14 }}
              transition={{ duration: 0.38, ease: [0.22, 1, 0.36, 1] }}
              className="relative shrink-0"
            >
              <span className="mx-[10px] inline-flex rounded-[7px] bg-[#E4F5F0] px-[10px] py-[5px] text-[13px] font-medium leading-none tracking-[0] text-[#20AD86]">STEP {current + 1} / {steps.length}</span>
              <h2 className="mb-0 ml-[10px] mr-12 mt-[10px] text-[22px] font-bold leading-tight tracking-[0] text-[#202124]">{currentStep.title}</h2>
              <p className="mb-0 ml-[10px] mr-12 mt-[6px] text-[13px] font-medium leading-[1.28] tracking-[0] text-[#6A6D70]">{currentStep.desc}</p>
            </motion.div>
          </AnimatePresence>

          <div className="relative mt-[12px] flex min-h-[160px] flex-1 overflow-hidden rounded-[15px] border-[1.5px] border-[#22C59A]/40 bg-white/20">
            <video ref={videoRef} autoPlay playsInline muted className="h-full w-full object-cover" />
            <canvas ref={overlayRef} className="absolute inset-0 z-20 h-full w-full pointer-events-none" />
            <canvas ref={captureRef} className="hidden" />
            <Corner className="left-[17px] top-[18px] rotate-0" />
            <Corner className="right-[17px] top-[18px] rotate-90" />
            <Corner className="bottom-[18px] right-[17px] rotate-180" />
            <Corner className="bottom-[18px] left-[17px] -rotate-90" />
            {cameraState !== "ready" && (
              <div className="absolute inset-0 z-30 flex flex-col items-center justify-center bg-black/60">
                <div className="flex h-[64px] w-[64px] items-center justify-center rounded-full bg-[#ECF5F2]">
                  <Camera size={36} strokeWidth={1.65} className="text-[#718E86]" />
                </div>
                <p className="mt-[16px] text-[15px] font-medium tracking-[0] text-white/80">
                  {cameraState === "denied" ? "Camera permission is required" : "Preparing camera"}
                </p>
              </div>
            )}
            {debugDetectionEnabled && detectionDebug && (
              <div className="absolute bottom-[8px] left-[8px] right-[8px] z-30 rounded-[8px] bg-black/70 px-[9px] py-[7px] text-[10px] font-medium leading-[1.35] tracking-[0] text-white">
                <div>model: {detectionDebug.model_profile ?? "unknown"}</div>
                <div>raw: {formatDebugDetections(detectionDebug.raw_detections)}</div>
                <div>filtered: {formatDebugDetections(detectionDebug.filtered_detections ?? detectionDebug.detections)}</div>
              </div>
            )}
          </div>
        </section>

        <section className="flex min-h-[104px] shrink-0 items-center rounded-[18px] bg-white px-[16px] py-[13px] shadow-[0_14px_32px_rgba(31,69,61,0.075)]">
          <div className="flex h-[78px] w-[98px] shrink-0 items-center justify-center overflow-hidden rounded-[11px] bg-[#F1F8F5]">
            <AirconIllustration className="h-[64px] w-[88px]" arrow />
          </div>
          <div className="mx-[16px] h-[70px] border-l border-dashed border-[#DDE5E2]" />
          <div className="min-w-0 flex-1">
            <div className="mb-[6px] flex items-center gap-[5px]">
              <span className="flex h-[18px] w-[18px] shrink-0 items-center justify-center rounded-full bg-[#DDF3EC] text-[#22B98F]"><Lightbulb size={11} strokeWidth={2} /></span>
              <strong className="text-[13px] font-semibold tracking-[0] text-[#20AD86]">Try this</strong>
            </div>
            <p className="whitespace-pre-line py-0 pl-[20px] pr-0 text-[13px] font-medium leading-[1.45] tracking-[0] text-[#55595D]">{currentStep.hint || currentStep.safety || currentStep.targetHint || currentStep.desc}</p>
          </div>
        </section>
      </main>

      <footer className="mx-[12px] mb-[20px] shrink-0 rounded-[16px] px-[8px] py-[8px]" style={{ background: "rgba(255,255,255,0.45)", backdropFilter: "blur(20px)", WebkitBackdropFilter: "blur(20px)", border: "1px solid rgba(255,255,255,0.65)", boxShadow: "0 4px 20px rgba(31,69,61,0.08), inset 0 1px 0 rgba(255,255,255,0.8)" }}>
        <div className="flex items-center gap-[8px]">
          <motion.button
            onClick={handlePrev}
            disabled={current === 0}
            whileTap={{ scale: 0.95 }}
            transition={{ type: "spring", stiffness: 400, damping: 22 }}
            className="h-[48px] flex-1 rounded-[12px] text-[15px] font-bold tracking-[0] transition disabled:opacity-30"
            style={{ background: "rgba(255,255,255,0.7)", border: "1px solid rgba(255,255,255,0.65)", color: "#20B88E", boxShadow: "0 2px 8px rgba(31,69,61,0.06), inset 0 1px 0 rgba(255,255,255,0.9)" }}
          >Previous</motion.button>
          <motion.button
            onClick={handleNext}
            whileTap={{ scale: 0.95 }}
            transition={{ type: "spring", stiffness: 400, damping: 22 }}
            className="h-[48px] flex-1 rounded-[12px] text-[15px] font-bold tracking-[0] text-white"
            style={{ background: "linear-gradient(135deg, #24C99A, #14B989)", boxShadow: "0 4px 14px rgba(34,197,154,0.35), inset 0 1px 0 rgba(255,255,255,0.3)", border: "1px solid rgba(255,255,255,0.3)" }}
          >{current === steps.length - 1 ? "Done" : "Next"}</motion.button>
        </div>
      </footer>
    </motion.div>
  );
}

function AirconIllustration({ className, arrow = false }: { className?: string; arrow?: boolean }) {
  return (
    <div className={`relative ${className ?? ""}`} aria-hidden="true">
      <div className="absolute left-[18%] top-[8%] h-[38%] w-[72%] rounded-[9px] border border-[#E2E7E5] bg-gradient-to-br from-white via-[#FDFEFE] to-[#F1F4F3] shadow-[8px_10px_18px_rgba(70,88,85,0.13)]" />
      <div className="absolute left-[22%] top-[43%] h-[9%] w-[63%] skew-x-[-10deg] rounded-sm bg-gradient-to-r from-[#646D6B] via-[#303534] to-[#8A9490] opacity-85" />
      <div className="absolute left-[23%] top-[51%] h-[24%] w-[56%] skew-x-[-12deg] border border-[#C9D2CF] bg-[#F8FBFA] shadow-[0_6px_10px_rgba(70,88,85,0.12)]">
        <div className="grid h-full grid-cols-4 grid-rows-2 gap-px p-[3px] opacity-70">
          {Array.from({ length: 8 }).map((_, idx) => <span key={idx} className="bg-[#DCE6E3]" />)}
        </div>
      </div>
      {arrow && (
        <div className="absolute left-[44%] top-[6%] flex h-[28px] w-[28px] items-center justify-center rounded-full bg-[#22C59A]/15 text-[#22B98F]">
          <ArrowUp size={18} strokeWidth={2.3} />
        </div>
      )}
    </div>
  );
}

function Corner({ className }: { className: string }) {
  return <span className={`absolute h-[24px] w-[24px] rounded-tl-[5px] border-l-2 border-t-2 border-[#22B98F] ${className}`} />;
}
