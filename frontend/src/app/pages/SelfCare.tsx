import { useNavigate, useLocation } from "react-router";
import { ChevronLeft } from "lucide-react";
import { useEffect, useState } from "react";
import acImage from "../../imports/제품페이지관리/47f735f974d0900368394246ff236d4a45df2a58.png";
import { requestAiChat } from "../api/chat";
import type { ChatGuideOptions, ChatManualGuide } from "../types/chat";

const glass = {
  background: "rgba(255,255,255,0.55)",
  backdropFilter: "blur(28px)",
  WebkitBackdropFilter: "blur(28px)",
  border: "1px solid rgba(255,255,255,0.80)",
  boxShadow: "0 8px 32px rgba(0,0,0,0.08), inset 0 1px 0 rgba(255,255,255,0.95)",
} as React.CSSProperties;

const PROCEDURE_LABELS: Record<string, string> = {
  filter_cleaning: "Filter Cleaning",
  noise_self_check: "Noise/Vibration Self Check",
  no_cooling_self_check: "Weak Cooling/Airflow Self Check",
  odor_self_check: "Odor Self Check",
  water_leak_monsoon: "Water Leak Self Check",
  power_troubleshooting: "Power Self Check",
  remote_operation: "Remote/Function Use Guide",
};

const FILTER_CLEANING_STEPS = [
  "Turn off the power and unplug the unit.",
  "Slowly lift the filter cover.",
  "Release the lock and remove the filter.",
  "Rinse under running water, then dry in the shade.",
  "Reinstall the filter and close the cover.",
];

const KNOWN_GUIDE_STEPS: Record<string, string[]> = {
  filter_cleaning: FILTER_CLEANING_STEPS,
  noise_self_check: [
    "If you notice metallic sounds, a burning smell, or severe vibration, stop using the product and contact the service center.",
    "Check that the front cover and visible panels are fully closed.",
    "Check whether curtains, furniture, or loose items are shaking because of airflow.",
    "From a safe distance, check that the product is not tilted.",
    "Turn it back on with low airflow and check whether the noise decreases.",
    "Do not disassemble or touch internal covers, fans, or motor parts yourself.",
    "If the noise continues, request professional service.",
  ],
  no_cooling_self_check: [
    "Check that the desired temperature is set lower than the current indoor temperature.",
    "If the filter has a lot of dust, clean it and try operating again.",
    "Check that nothing is blocking ventilation around the outdoor unit.",
    "Check whether doors or windows are open or strong sunlight is coming in.",
    "If cooling remains weak, request professional service.",
  ],
  power_troubleshooting: [
    "If there is a burning smell, smoke, or sparks, turn off the power and contact the service center immediately.",
    "Check the remote batteries and display status.",
    "Visually check that the power plug is securely connected.",
    "Check whether the circuit breaker is off, but do not touch it with wet hands.",
    "If the same symptom repeats, request professional service without disassembling the product.",
  ],
};

const AR_GUIDE_STEP_TITLES: Record<string, string[]> = {
  filter_cleaning: ["Turn Off Power", "Open Cover", "Remove Filter", "Wash and Dry", "Reinstall"],
  no_cooling_self_check: ["Check Temperature Setting", "Check Filter Status", "Check Air Outlet", "Check Indoor Environment", "Request Professional Service"],
};

const AR_GUIDE_STEP_TARGETS: Record<
  string,
  Array<{ targetHint?: string; targetClasses?: string[]; contextClasses?: string[] }>
> = {
  filter_cleaning: [
    { targetHint: "Air conditioner body", targetClasses: ["aircon"] },
    { targetHint: "Air conditioner body", targetClasses: ["aircon"] },
    { targetHint: "Filter mesh", targetClasses: ["filter"], contextClasses: ["aircon"] },
    { targetHint: "Removed filter", targetClasses: ["filter"] },
    { targetHint: "Air conditioner body", targetClasses: ["aircon"] },
  ],
  no_cooling_self_check: [
    { targetHint: "Air conditioner body", targetClasses: ["aircon"] },
    { targetHint: "Filter mesh", targetClasses: ["filter"], contextClasses: ["aircon"] },
    { targetHint: "Air outlet / airflow path", targetClasses: ["outlet"], contextClasses: ["aircon"] },
    { targetHint: "Air conditioner body", targetClasses: ["aircon"] },
    { targetHint: "Air conditioner body", targetClasses: ["aircon"] },
  ],
};

const getProcedureLabel = (procedure?: string) =>
  (procedure && PROCEDURE_LABELS[procedure]) || "Guide";

const getGuideDisplayTitle = (guideOptions?: ChatGuideOptions | null) =>
  guideOptions?.display_title || `${getProcedureLabel(guideOptions?.procedure_type)} Steps`;

const youtubeEmbedUrl = (url?: string, videoId?: string) => {
  if (videoId) return `https://www.youtube.com/embed/${videoId}`;
  if (!url) return null;
  const watchMatch = url.match(/[?&]v=([^&]+)/);
  if (watchMatch?.[1]) return `https://www.youtube.com/embed/${watchMatch[1]}`;
  const shortMatch = url.match(/youtu\.be\/([^?&]+)/);
  if (shortMatch?.[1]) return `https://www.youtube.com/embed/${shortMatch[1]}`;
  return null;
};

const extractGuideSteps = (guide?: ChatManualGuide, procedureType?: string) => {
  if (procedureType && KNOWN_GUIDE_STEPS[procedureType]) return KNOWN_GUIDE_STEPS[procedureType];
  const text = guide?.guide_text || guide?.summary || "";
  const steps = text
    .split(/\n+/)
    .map((line) => line.replace(/^\s*(?:\d+[\).\s-]*|[①-⑳]\s*)/, "").trim())
    .filter((line) => line.length > 0);
  return steps.length > 0 ? steps : ["Review the official guide and proceed step by step within a safe range."];
};

const arGuideStepsFromOptions = (guideOptions?: ChatGuideOptions) => {
  const procedureType = guideOptions?.procedure_type;
  const manual = guideOptions?.manual_guides?.[0];
  const titles = procedureType ? AR_GUIDE_STEP_TITLES[procedureType] : undefined;
  const targets = procedureType ? AR_GUIDE_STEP_TARGETS[procedureType] : undefined;
  const displaySteps = guideOptions?.display_steps ?? [];
  const descriptions = displaySteps.length
    ? displaySteps
        .map((step) => (step.text || step.source_text || "").trim())
        .filter(Boolean)
    : extractGuideSteps(manual, procedureType);
  return descriptions.map((desc, index) => ({
    title: displaySteps[index]?.title || titles?.[index] || `STEP ${index + 1}`,
    desc,
    tts_enabled: displaySteps[index]?.tts_enabled ?? true,
    tts_text: displaySteps[index]?.tts_text || desc,
    tts_language_code: displaySteps[index]?.tts_language_code || "en-IN",
    tts_provider: displaySteps[index]?.tts_provider || "web_speech",
    audio_url: displaySteps[index]?.audio_url,
    sourceType: displaySteps[index]?.source_type,
    sourceUrl: displaySteps[index]?.source_url,
    sourceText: displaySteps[index]?.source_text,
    ...targets?.[index],
  }));
};

const guideVideo = (guideOptions?: ChatGuideOptions) => {
  const youtube = guideOptions?.youtube_recommendations?.[0];
  const manual = guideOptions?.manual_guides?.[0];
  const embedUrl = youtubeEmbedUrl(youtube?.source_url, youtube?.video_id) || youtubeEmbedUrl(manual?.video_url || undefined);
  return {
    title: youtube?.title || manual?.title || "LG Official Video Guide",
    embedUrl,
    videoUrl: manual?.video_url || youtube?.source_url || null,
    channel: youtube?.channel_name,
  };
};

export function SelfCare() {
  const navigate = useNavigate();
  const location = useLocation();
  const routeState = location.state as { tab?: "manual" | "ar"; guideOptions?: ChatGuideOptions } | null;
  const initialTab = routeState?.tab ?? "manual";
  const [activeTab, setActiveTab] = useState<"manual" | "ar">(initialTab);
  const [guideOptions, setGuideOptions] = useState<ChatGuideOptions | null>(routeState?.guideOptions ?? null);
  const [isGuideLoading, setIsGuideLoading] = useState(false);

  useEffect(() => {
    if (routeState?.tab) {
      setActiveTab(routeState.tab);
    }
  }, [routeState?.tab]);

  useEffect(() => {
    if (routeState?.guideOptions) {
      setGuideOptions(routeState.guideOptions);
      return;
    }

    let cancelled = false;

    const loadGuideOptions = async () => {
      setIsGuideLoading(true);
      try {
        const response = await requestAiChat("Air conditioner filter cleaning manual guide", {
          intent: "care",
          productCategory: "Air Conditioner",
          productType: "Air Conditioner",
          productName: "Living Room Air Conditioner",
          model: "AS-Q24ENXE",
          deviceId: "D001",
          symptom: "filter_cleaning",
          recommendedActions: ["manual", "ar"],
        });
        if (!cancelled) {
          setGuideOptions(response.guide_options ?? null);
        }
      } catch {
        if (!cancelled) {
          setGuideOptions(null);
        }
      } finally {
        if (!cancelled) {
          setIsGuideLoading(false);
        }
      }
    };

    loadGuideOptions();

    return () => {
      cancelled = true;
    };
  }, [routeState?.guideOptions]);

  const handleDone = () => {
    const history = JSON.parse(localStorage.getItem("careHistory") || "[]");
    history.push({
      id: Date.now().toString(),
      type: "Self Care",
      title: "Air Conditioner Filter Cleaning",
      date: new Date().toISOString(),
    });
    localStorage.setItem("careHistory", JSON.stringify(history));
    navigate("/", { state: { aiDismissed: true } });
  };

  const handleSkip = () => navigate("/");
  const handleStartArGuide = () => {
    navigate("/ar-guide", {
      state: {
        from: "/self-care",
        procedureType: guideOptions?.procedure_type || "filter_cleaning",
        guideTitle: guideOptions?.display_title || procedureLabel,
        guideSteps: arGuideStepsFromOptions(guideOptions ?? undefined),
        returnState: {
          tab: "ar",
          guideOptions,
        },
      },
    });
  };

  const cardCls = "rounded-[20px] p-5";
  const manual = guideOptions?.manual_guides?.[0];
  const procedureType = guideOptions?.procedure_type;
  const procedureLabel = getProcedureLabel(procedureType);
  const guideTitle = getGuideDisplayTitle(guideOptions);
  const steps = guideOptions ? extractGuideSteps(manual, procedureType) : FILTER_CLEANING_STEPS;
  const video = guideVideo(guideOptions ?? undefined);

  const DoneSection = () => (
    <div className="rounded-[16px] px-4 py-3 flex items-center justify-between gap-3" style={glass}>
      <p className="font-['Pretendard:SemiBold',sans-serif] text-[13px] text-[#444]">Did you complete the care task?</p>
      <div className="flex gap-2 shrink-0">
        <button
          onClick={handleDone}
          className="rounded-xl px-4 py-1.5 text-[12px] font-semibold text-white bg-gradient-to-r from-[#1DB87A] to-[#3DDC97] hover:opacity-90 transition-opacity"
        >
          Yes
        </button>
        <button
          onClick={handleSkip}
          className="rounded-xl px-4 py-1.5 text-[12px] font-semibold text-[#1DB87A] bg-white border border-[#1DB87A] hover:bg-[#f0fdf7] transition-colors"
        >
          No
        </button>
      </div>
    </div>
  );

  return (
    <div className="relative min-h-screen w-full bg-[#f7f9f8] overflow-x-hidden">
      {/* Aurora Glow — Home 동일 */}
      <div className="pointer-events-none absolute -top-24 -left-20 w-80 h-80 rounded-full"
        style={{ background: "rgba(61,220,151,0.10)", filter: "blur(90px)" }} />
      <div className="pointer-events-none absolute top-[360px] -right-16 w-64 h-64 rounded-full"
        style={{ background: "rgba(100,210,190,0.09)", filter: "blur(80px)" }} />
      <div className="pointer-events-none absolute bottom-[180px] left-0 w-56 h-56 rounded-full"
        style={{ background: "rgba(80,200,160,0.08)", filter: "blur(75px)" }} />
      <div className="relative z-10 px-[18px] pt-[40px] pb-10 w-full max-w-[390px] mx-auto">

        {/* 헤더 */}
        <div className="flex items-center gap-1 mb-5 -mx-[2px]">
          <button onClick={() => navigate("/")} className="p-1">
            <ChevronLeft size={22} className="text-[#555]" />
          </button>
          <p className="font-['Pretendard:Medium',sans-serif] text-[20px] tracking-[-0.3px] text-black leading-[15px]">
            Self Care
          </p>
        </div>

        {/* 제품 카드 — DeviceDetail 동일 구조 */}
        <div className="mb-5">
          <div className="rounded-[20px] p-5" style={glass}>
            <div className="relative flex justify-center mb-1 pt-[24px]">
              <span className="absolute top-0 left-1/2 -translate-x-1/2 whitespace-nowrap rounded-full border border-[#BFEAD4] bg-[#eaf8f1] px-[10px] py-[3px] font-['Pretendard:Medium',sans-serif] text-[9px] text-[#2d9b69]">
                LG Whisen Wall-mounted
              </span>
              <img src={acImage} alt="Air Conditioner" className="w-[200px] h-[100px] object-contain" />
            </div>
            <p className="font-['Pretendard:SemiBold',sans-serif] text-[16px] text-[#111] text-center mb-3">Living Room Air Conditioner</p>
            <div className="grid grid-cols-2 pt-4" style={{ borderTop: "1px solid rgba(200,200,200,0.3)" }}>
              <div className="flex flex-col items-center gap-[4px] border-r border-[rgba(200,200,200,0.28)] px-2">
                <p className="font-['Pretendard:Regular',sans-serif] text-[12px] text-[#888]">Product Type</p>
                <p className="font-['Pretendard:Medium',sans-serif] text-[13px] leading-tight text-[#111]">Air Conditioner</p>
              </div>
              <div className="flex flex-col items-center gap-[4px] px-2">
                <p className="font-['Pretendard:Regular',sans-serif] text-[12px] text-[#888]">Registered Date</p>
                <p className="font-['Pretendard:Medium',sans-serif] text-[13px] leading-tight text-[#111]">2024.01.15</p>
              </div>
            </div>
          </div>
        </div>

        {/* 탭 */}
        <div className="flex mb-5 border-b border-[#e0e0e0]">
          {(["manual", "ar"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`flex-1 py-3 text-[16px] font-semibold border-b-2 -mb-px transition-colors ${
                activeTab === tab
                  ? "text-[#1DB87A] border-[#1DB87A]"
                  : "text-[#b0b0b0] border-transparent"
              }`}
            >
              {tab === "manual" ? "Manual" : "AR"}
            </button>
          ))}
        </div>

        {/* Manual 탭 */}
        {activeTab === "manual" && (
          <div className="flex flex-col gap-4">
            {/* Chat.tsx 공식근거 기반 영상 표시 구조 */}
            <div className="rounded-[20px] p-[14px]" style={glass}>
              <div className="mb-3">
                <p className="flex items-baseline gap-[5px]">
                  <span className="font-['Pretendard:SemiBold',sans-serif] text-[13px] text-[#555]">Official Video Guide</span>
                  <span className="font-['Pretendard:Medium',sans-serif] text-[11px] text-[#aaa]">·</span>
                  <span className="font-['Pretendard:Medium',sans-serif] text-[11px] text-[#888]">{procedureLabel}</span>
                </p>
              </div>
              <div
                className="relative flex aspect-video w-full items-center justify-center overflow-hidden rounded-[16px]"
                style={{
                  background: "rgba(255,255,255,0.52)",
                  border: "1px solid rgba(255,255,255,0.80)",
                  boxShadow: "inset 0 1px 0 rgba(255,255,255,0.9), 0 4px 18px rgba(31,69,61,0.06)",
                }}
              >
                {video.embedUrl ? (
                  <iframe
                    title={video.title}
                    src={video.embedUrl}
                    className="w-full h-full"
                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                    allowFullScreen
                  />
                ) : video.videoUrl ? (
                  <video controls className="w-full h-full object-cover" src={video.videoUrl} controlsList="nodownload">
                    Your browser does not support the video tag.
                  </video>
                ) : (
                  <p className="font-['Pretendard:Regular',sans-serif] text-[13px] text-[#888]">
                    {isGuideLoading ? "Loading the official manual." : "No linked official video is available."}
                  </p>
                )}
              </div>
            </div>

            {/* Chat.tsx 공식근거 기반 단계별 Guide 구조 */}
            <div className={cardCls} style={glass}>
              <div className="flex items-center justify-between gap-2 mb-4">
                <p className="font-['Pretendard:SemiBold',sans-serif] text-[15px] text-[#111]">📋 {guideTitle}</p>
                <span className="font-['Pretendard:Medium',sans-serif] text-[9px] text-[#2d9b69] bg-[#eaf8f1] rounded-full px-2 py-[2px] whitespace-nowrap">
                  LG official standard
                </span>
              </div>
              <div className="flex flex-col gap-3">
                {steps.map((step, i) => (
                  <div key={i} className="flex items-start gap-3">
                    <span className="w-[22px] h-[22px] rounded-full bg-gradient-to-r from-[#1DB87A] to-[#3DDC97] flex items-center justify-center flex-shrink-0 mt-[1px]">
                      <span className="text-[11px] font-bold text-white">{i + 1}</span>
                    </span>
                    <p className="font-['Pretendard:Regular',sans-serif] text-[13px] text-[#555] leading-snug pt-[2px]">{step}</p>
                  </div>
                ))}
              </div>
            </div>

            <DoneSection />
          </div>
        )}

        {/* AR 탭 */}
        {activeTab === "ar" && (
          <div className="flex flex-col gap-4">
            {/* 단계 카드 */}
            <div className={cardCls} style={glass}>
              <p className="font-['Pretendard:SemiBold',sans-serif] text-[15px] text-[#111] mb-4">📋 {guideTitle}</p>
              <div className="flex flex-col gap-3">
                {steps.map((step, i) => (
                  <div key={i} className="flex items-start gap-3">
                    <span className="w-[22px] h-[22px] rounded-full bg-gradient-to-r from-[#1DB87A] to-[#3DDC97] flex items-center justify-center flex-shrink-0 mt-[1px]">
                      <span className="text-[11px] font-bold text-white">{i + 1}</span>
                    </span>
                    <p className="font-['Pretendard:Regular',sans-serif] text-[13px] text-[#555] leading-snug pt-[2px]">{step}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* AR Guide 버튼 */}
            <button
              onClick={handleStartArGuide}
              className="w-full rounded-2xl py-4 text-[15px] font-semibold text-white bg-gradient-to-r from-[#1DB87A] to-[#3DDC97] hover:opacity-90 transition-opacity"
            >
              AR Guide Get Started
            </button>

            <DoneSection />
          </div>
        )}
      </div>
    </div>
  );
}
