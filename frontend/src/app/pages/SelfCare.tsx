import { useNavigate, useLocation } from "react-router";
import { ChevronLeft, Maximize2 } from "lucide-react";
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
  filter_cleaning: "필터 청소",
  noise_self_check: "소음/진동 자가점검",
  no_cooling_self_check: "냉방/바람 약함 자가점검",
  odor_self_check: "냄새 자가점검",
  water_leak_monsoon: "누수 자가점검",
  power_troubleshooting: "전원 자가점검",
  remote_operation: "리모컨/기능 사용 안내",
};

const FILTER_CLEANING_STEPS = [
  "전원을 끄고 플러그를 뽑으세요.",
  "필터 커버를 천천히 들어 올리세요.",
  "잠금을 풀고 필터를 분리하세요.",
  "흐르는 물로 헹군 후 그늘에 말리세요.",
  "필터를 재장착하고 커버를 닫으세요.",
];

const KNOWN_GUIDE_STEPS: Record<string, string[]> = {
  filter_cleaning: FILTER_CLEANING_STEPS,
  noise_self_check: [
    "금속성 소리, 타는 냄새, 심한 진동이 있으면 사용을 멈추고 서비스센터로 연결하세요.",
    "앞 커버나 보이는 패널이 완전히 닫혀 있는지 확인하세요.",
    "커튼, 가구, 느슨한 물건이 바람 때문에 떨리는지 확인하세요.",
    "안전한 거리에서 제품이 기울어져 있지 않은지 확인하세요.",
    "낮은 풍량으로 다시 켜서 소음이 줄어드는지 확인하세요.",
    "내부 커버, 팬, 모터 부위는 직접 분해하거나 만지지 마세요.",
    "소음이 계속되면 전문 A/S를 신청하세요.",
  ],
  no_cooling_self_check: [
    "희망 온도를 현재 실내 온도보다 낮게 설정했는지 확인하세요.",
    "필터에 먼지가 많으면 필터를 청소한 뒤 다시 작동해보세요.",
    "실외기 주변 통풍을 막는 물건이 없는지 확인하세요.",
    "문과 창문이 열려 있거나 햇빛이 강하게 들어오는지 확인하세요.",
    "냉방이 계속 약하면 전문 A/S를 신청하세요.",
  ],
  power_troubleshooting: [
    "타는 냄새, 연기, 스파크가 있으면 전원을 끄고 바로 서비스센터로 연결하세요.",
    "리모컨 배터리와 표시창 상태를 확인하세요.",
    "전원 플러그가 안전하게 연결되어 있는지 눈으로만 확인하세요.",
    "차단기가 내려갔는지 확인하되, 젖은 손으로 만지지 마세요.",
    "같은 증상이 반복되면 내부 분해 없이 전문 A/S를 신청하세요.",
  ],
};

const getProcedureLabel = (procedure?: string) =>
  (procedure && PROCEDURE_LABELS[procedure]) || "가이드";

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
  return steps.length > 0 ? steps : ["공식 가이드 내용을 확인한 뒤 안전한 범위에서 단계대로 진행하세요."];
};

const guideVideo = (guideOptions?: ChatGuideOptions) => {
  const youtube = guideOptions?.youtube_recommendations?.[0];
  const manual = guideOptions?.manual_guides?.[0];
  const embedUrl = youtubeEmbedUrl(youtube?.source_url, youtube?.video_id) || youtubeEmbedUrl(manual?.video_url || undefined);
  return {
    title: youtube?.title || manual?.title || "LG 공식 영상 가이드",
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
    if (routeState?.guideOptions) {
      setGuideOptions(routeState.guideOptions);
      return;
    }

    let cancelled = false;

    const loadGuideOptions = async () => {
      setIsGuideLoading(true);
      try {
        const response = await requestAiChat("에어컨 필터 청소 매뉴얼 가이드", {
          intent: "care",
          productCategory: "에어컨",
          productType: "에어컨",
          productName: "거실 에어컨",
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
      title: "에어컨 필터 청소",
      date: new Date().toISOString(),
    });
    localStorage.setItem("careHistory", JSON.stringify(history));
    navigate("/", { state: { aiDismissed: true } });
  };

  const handleSkip = () => navigate("/");

  const cardCls = "rounded-[20px] p-5";
  const manual = guideOptions?.manual_guides?.[0];
  const procedureType = guideOptions?.procedure_type;
  const procedureLabel = getProcedureLabel(procedureType);
  const steps = guideOptions ? extractGuideSteps(manual, procedureType) : FILTER_CLEANING_STEPS;
  const video = guideVideo(guideOptions ?? undefined);

  const DoneSection = () => (
    <div className="rounded-[16px] px-4 py-3 flex items-center justify-between gap-3" style={glass}>
      <p className="font-['Pretendard:SemiBold',sans-serif] text-[13px] text-[#444]">관리를 완료하셨나요?</p>
      <div className="flex gap-2 shrink-0">
        <button
          onClick={handleDone}
          className="rounded-xl px-4 py-1.5 text-[12px] font-semibold text-white bg-gradient-to-r from-[#1DB87A] to-[#3DDC97] hover:opacity-90 transition-opacity"
        >
          예
        </button>
        <button
          onClick={handleSkip}
          className="rounded-xl px-4 py-1.5 text-[12px] font-semibold text-[#1DB87A] bg-white border border-[#1DB87A] hover:bg-[#f0fdf7] transition-colors"
        >
          아니요
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
      <div className="relative z-10 w-full max-w-[390px] mx-auto pb-10">

        {/* 헤더 */}
        <div className="flex items-center gap-1 px-4 pt-10 pb-5">
          <button onClick={() => navigate("/")} className="p-1">
            <ChevronLeft size={22} className="text-[#555]" />
          </button>
          <p className="font-['Pretendard:Medium',sans-serif] text-[20px] tracking-[-0.3px] text-black leading-[15px]">
            셀프 케어
          </p>
        </div>

        {/* 제품 카드 — DeviceDetail 동일 구조 */}
        <div className="mx-6 mb-5">
          <div className="rounded-[20px] p-5" style={glass}>
            <div className="flex justify-center mb-4">
              <img src={acImage} alt="에어컨" className="w-[200px] h-[100px] object-contain" />
            </div>
            <p className="font-['Pretendard:SemiBold',sans-serif] text-[18px] text-[#111] text-center mb-1">거실 에어컨</p>
            <p className="font-['Pretendard:Regular',sans-serif] text-[13px] text-[#888] text-center mb-4">
              LG 휘센 벽걸이
            </p>
            <div className="grid grid-cols-2 gap-2 pt-4" style={{ borderTop: "1px solid rgba(200,200,200,0.3)" }}>
              <div className="flex justify-between">
                <p className="font-['Pretendard:Regular',sans-serif] text-[13px] text-[#888]">제품군</p>
                <p className="font-['Pretendard:Medium',sans-serif] text-[13px] text-[#111]">에어컨</p>
              </div>
              <div className="flex justify-between">
                <p className="font-['Pretendard:Regular',sans-serif] text-[13px] text-[#888]">등록일</p>
                <p className="font-['Pretendard:Medium',sans-serif] text-[13px] text-[#111]">2024.01.15</p>
              </div>
            </div>
          </div>
        </div>

        {/* 탭 */}
        <div className="flex mx-6 mb-5 border-b border-[#e0e0e0]">
          {(["manual", "ar"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`flex-1 py-2.5 text-[14px] font-semibold border-b-2 -mb-px transition-colors ${
                activeTab === tab
                  ? "text-[#1DB87A] border-[#1DB87A]"
                  : "text-[#b0b0b0] border-transparent"
              }`}
            >
              {tab === "manual" ? "메뉴얼" : "AR"}
            </button>
          ))}
        </div>

        {/* 메뉴얼 탭 */}
        {activeTab === "manual" && (
          <div className="mx-6 flex flex-col gap-4">
            {/* Chat.tsx 공식근거 기반 영상 표시 구조 */}
            <div className="rounded-[20px] overflow-hidden" style={glass}>
              <div className="w-full aspect-video bg-[#e8ecef] flex items-center justify-center relative">
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
                    브라우저가 비디오 태그를 지원하지 않습니다.
                  </video>
                ) : (
                  <p className="font-['Pretendard:Regular',sans-serif] text-[13px] text-[#888]">
                    {isGuideLoading ? "공식 매뉴얼을 불러오는 중입니다." : "연결된 공식 영상이 없습니다."}
                  </p>
                )}
                <button className="absolute top-3 right-3 w-8 h-8 bg-white/80 rounded-lg flex items-center justify-center">
                  <Maximize2 size={16} className="text-[#555]" />
                </button>
              </div>
            </div>

            {/* Chat.tsx 공식근거 기반 단계별 가이드 구조 */}
            <div className={cardCls} style={glass}>
              <div className="flex items-center justify-between gap-2 mb-4">
                <p className="font-['Pretendard:SemiBold',sans-serif] text-[15px] text-[#111]">📋 {procedureLabel} 순서</p>
                <span className="font-['Pretendard:Medium',sans-serif] text-[9px] text-[#2d9b69] bg-[#eaf8f1] rounded-full px-2 py-[2px] whitespace-nowrap">
                  LG 공식 기준
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
          <div className="mx-6 flex flex-col gap-4">
            {/* 단계 카드 */}
            <div className={cardCls} style={glass}>
              <p className="font-['Pretendard:SemiBold',sans-serif] text-[15px] text-[#111] mb-4">📋 {procedureLabel} 순서</p>
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

            {/* AR 가이드 버튼 */}
            <button
              onClick={() => navigate("/ar-guide", { state: { from: "/self-care" } })}
              className="w-full rounded-2xl py-4 text-[15px] font-semibold text-white bg-gradient-to-r from-[#1DB87A] to-[#3DDC97] hover:opacity-90 transition-opacity"
            >
              AR 가이드 시작하기
            </button>

            <DoneSection />
          </div>
        )}
      </div>
    </div>
  );
}
