import { useState, useRef, useEffect, useCallback } from "react";
import { useNavigate } from "react-router";
import { ChevronLeft, Send, Paperclip, Lightbulb, ClipboardList, Wrench, CircleHelp } from "lucide-react";
import { motion, AnimatePresence } from "motion/react";
import aiAlertVideo from "../../imports/AS-Q24ENXE_filter_cleaning_MVP_hyperframes.mp4";
import lgGif from "../../imports/LG______-1.gif";
import {
  getAllProductTypes,
  getAvailableDates,
  getInitialChatMessages,
  getProblemOptions,
  getProductCategories,
  getProductTypes,
  getTimeSlots,
  requestAiChat,
  saveChatMessage,
} from "../api/chat";
import { getRegisteredDevices } from "../api/devices";
import { getUserProfile } from "../api/user";
import type { AiChatResponse, ChatContext, ChatGuideOptions, ChatManualGuide, FlowType, Message, ServiceInfo, ServiceStep } from "../types/chat";
import type { ChatDeviceOption } from "../types/device";

const LEGACY_CHAT_STORAGE_KEYS = ["chat_messages"];
const CHAT_STORAGE_KEY = "chat_messages_v20260612";
const CHAT_ENDED_KEY = "chat_session_ended";

const now = () =>
  new Date().toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit" });

const PRODUCTS = getProductCategories();
const AVAILABLE_DATES = getAvailableDates();
const TIME_SLOTS = getTimeSlots();

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

const AR_GUIDE_STEP_TITLES: Record<string, string[]> = {
  filter_cleaning: ["전원 차단", "커버 열기", "필터 분리", "세척 및 건조", "재장착"],
  no_cooling_self_check: ["온도 설정 확인", "필터 상태 확인", "실외기 통풍 확인", "실내 환경 확인", "전문 A/S 신청"],
  noise_self_check: ["위험 신호 확인", "커버 상태 확인", "주변 물건 확인", "기울어짐 확인", "저풍량 확인", "분해 금지", "전문 A/S 신청"],
  power_troubleshooting: ["위험 신호 확인", "표시창 확인", "전원 연결 확인", "차단기 확인", "전문 A/S 신청"],
};

const arGuideStepsFromOptions = (guideOptions?: ChatGuideOptions) => {
  const procedureType = guideOptions?.procedure_type;
  const manual = guideOptions?.manual_guides?.[0];
  const titles = procedureType ? AR_GUIDE_STEP_TITLES[procedureType] : undefined;
  return extractGuideSteps(manual, procedureType).map((desc, index) => ({
    title: titles?.[index] || `STEP ${index + 1}`,
    desc,
  }));
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

export function Chat() {
  const navigate = useNavigate();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const problemMsgRef = useRef<HTMLDivElement>(null);

  const getInitialMessages = (): Message[] => {
    LEGACY_CHAT_STORAGE_KEYS.forEach((key) => localStorage.removeItem(key));

    const ended = sessionStorage.getItem(CHAT_ENDED_KEY);
    if (ended === "true") {
      sessionStorage.removeItem(CHAT_ENDED_KEY);
      localStorage.removeItem(CHAT_STORAGE_KEY);
      return getInitialChatMessages();
    }
    const saved = localStorage.getItem(CHAT_STORAGE_KEY);
    if (saved) {
      try { return JSON.parse(saved); } catch { /* ignore */ }
    }
    return getInitialChatMessages();
  };

  const [messages, setMessages] = useState<Message[]>(getInitialMessages);
  const [inputValue, setInputValue] = useState("");
  const [flow, setFlow] = useState<FlowType>(null);
  const [chatContext, setChatContext] = useState<ChatContext>({});
  const [serviceStep, setServiceStep] = useState<ServiceStep>("idle");
  const [serviceInfo, setServiceInfo] = useState<Partial<ServiceInfo>>({});
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [serviceCompleted, setServiceCompleted] = useState(false);
  const [gifPop, setGifPop] = useState(false);
  const [uiPhase, setUiPhase] = useState<"initial" | "selecting" | "selecting-type" | "pending-start" | "morphing">("initial");
  const [floatingChips, setFloatingChips] = useState<string[]>([]);
  const [selectingProducts, setSelectingProducts] = useState(false);
  const [selectingTypes, setSelectingTypes] = useState(false);
  const [selectedProduct, setSelectedProduct] = useState<string>("");

  const triggerGifPop = useCallback(() => {
    setGifPop(true);
    setTimeout(() => setGifPop(false), 700);
  }, []);

  const handleInitialSelect = (label: string) => {
    setFloatingChips([label]);
    setUiPhase("selecting");
    setSelectingProducts(false);
    setSelectingTypes(false);
    if (label === "제품 문제 해결") setFlow("trouble");
    else if (label === "가전 관리 방법") setFlow("care");
    else if (label === "서비스 센터 연결") setFlow("service");
    setTimeout(() => setSelectingProducts(true), 420);
  };

  const handleProductSelect = (product: string, mainFlow: string) => {
    setFloatingChips([mainFlow, product]);
    setSelectedProduct(product);
    setSelectingProducts(false);
    setUiPhase("selecting-type");
    setTimeout(() => setSelectingTypes(true), 420);
  };

  const handleTypeSelect = (type: string, mainFlow: string, product: string) => {
    setFloatingChips([mainFlow, product, type]);
    setSelectingTypes(false);
    setUiPhase("pending-start");
  };

  const handleStartChat = () => {
    const [mainFlow, product, type] = floatingChips;
    setUiPhase("morphing");
    setTimeout(() => {
      handleOptionClick(mainFlow);
      setTimeout(() => handleOptionClick(product), 750);
      setTimeout(() => {
        handleOptionClick(type);
        setTimeout(() => {
          problemMsgRef.current?.scrollIntoView({ behavior: "instant", block: "start" });
        }, 700);
      }, 1500);
    }, 520);
  };

  const isInitial = messages.length === 1 && uiPhase !== "morphing";

  const handleBack = () => {
    if (serviceCompleted) {
      endSession();
    }
    navigate("/");
  };

  const scrollToBottom = () => messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  useEffect(() => { scrollToBottom(); }, [messages]);
  useEffect(() => {
    localStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(messages));
  }, [messages]);

  // AR 가이드 복귀 시 동기화
  useEffect(() => {
    const handleFocus = () => {
      const saved = localStorage.getItem(CHAT_STORAGE_KEY);
      if (saved) {
        try {
          const parsed = JSON.parse(saved);
          if (parsed.length > messages.length) setMessages(parsed);
        } catch { /* ignore */ }
      }
    };
    window.addEventListener("focus", handleFocus);
    return () => window.removeEventListener("focus", handleFocus);
  }, [messages.length]);

  const endSession = () => sessionStorage.setItem(CHAT_ENDED_KEY, "true");

  const addMessage = (msg: Omit<Message, "id" | "time">) => {
    const full: Message = { id: Date.now().toString(), time: now(), ...msg };
    setMessages((prev) => [...prev, full]);
    return full;
  };

  const addUserMessage = (content: string) => {
    addMessage({ type: "user", content });
  };

  const addBotMessage = (content: string, extra?: Partial<Message>) => {
    setTimeout(async () => {
      setMessages((prev) => [
        ...prev,
        { id: (Date.now() + 1).toString(), type: "bot", content, time: now(), ...extra },
      ]);
    }, 600);
  };

  const statusFromAiResponse = (response: AiChatResponse): Message["status"] => {
    if (response.needs_clarification) return "needs_clarification";
    if (response.card_policy?.card_type === "safety_block") return "blocked";
    if (response.service_flow_type === "expert_as" || response.risk_level === "high") return "blocked";
    if ((response.guide_options?.ar_guides?.length ?? 0) > 0) return "ar_ready";
    if (response.guide_options) return "evidence_found";
    return "sent";
  };

  const guideButtonsFromAiResponse = (response: AiChatResponse): Message["guideButtons"] | undefined => {
    if (response.card_policy?.card_type === "safety_block") {
      return response.card_policy.show_service_button ? ["service"] : undefined;
    }
    if (response.service_flow_type === "expert_as" || response.risk_level === "high") return ["service"];
    if (!response.guide_options || response.needs_clarification) return undefined;
    return ["manual", "ar"];
  };

  const submitAiMessage = async (text: string, options?: { resetSession?: boolean }) => {
    const analyzingId = `analyzing-${Date.now()}`;
    const contextForRequest = {
      ...chatContext,
      symptom: text,
      ...(options?.resetSession ? { session_id: undefined } : {}),
    };

    setMessages((prev) => [
      ...prev,
      {
        id: analyzingId,
        type: "bot",
        content: "증상을 분석하고 있어요.",
        time: now(),
        status: "analyzing",
      },
    ]);

    try {
      await saveChatMessage(text, contextForRequest);
      const response = await requestAiChat(text, contextForRequest);
      if (response.session_id) {
        setChatContext((prev) => ({
          ...prev,
          session_id: response.session_id,
          symptom: text,
          recommendedActions: response.needs_clarification ? ["llm"] : prev.recommendedActions,
        }));
      }

      setMessages((prev) =>
        prev.map((message) =>
          message.id === analyzingId
            ? {
                ...message,
                content: response.message,
                status: statusFromAiResponse(response),
                guideButtons: guideButtonsFromAiResponse(response),
                guideOptions: response.needs_clarification ? undefined : response.guide_options ?? undefined,
                cardPolicy: response.card_policy ?? undefined,
              }
            : message,
        ),
      );
    } catch {
      setMessages((prev) =>
        prev.map((message) =>
          message.id === analyzingId
            ? {
                ...message,
                content: "API 연결을 확인하지 못했어요. 잠시 후 다시 시도해주세요.",
                status: "blocked",
              }
            : message,
        ),
      );
    }
  };

  const handleArGuideClick = (message: Message) => {
    if (!message.guideOptions || (message.guideOptions.ar_guides?.length ?? 0) > 0) {
      navigate("/ar-guide", {
        state: {
          from: "/chat",
          procedureType: message.guideOptions?.procedure_type,
          guideTitle: getProcedureLabel(message.guideOptions?.procedure_type),
          guideSteps: arGuideStepsFromOptions(message.guideOptions),
        },
      });
      return;
    }

    setMessages((prev) => [
      ...prev,
      {
        id: Date.now().toString(),
        type: "bot",
        content: "현재 이 증상은 공식 매뉴얼 가이드는 제공되지만 AR 가이드 템플릿은 아직 준비되지 않았어요. 먼저 영상과 단계별 매뉴얼로 확인해주세요.",
        time: now(),
        status: "blocked",
        showDoneAsk: true,
      },
    ]);
  };

  // 서비스센터 정보 수집 단계별 안내
  const nextServiceStep = (step: ServiceStep) => {
    setServiceStep(step);
    if (step === "model") {
      setTimeout(async () => {
        const devices = await getRegisteredDevices();
        setMessages((prev) => [...prev, {
          id: (Date.now() + 1).toString(), type: "bot",
          content: "등록된 가전 중 서비스를 신청할 제품을 선택해주세요.",
          time: now(),
          modelOptions: devices,
        }]);
      }, 600);
    } else if (step === "issue") {
      addBotMessage("겪고 계신 문제를 자세히 입력해주세요.");
    }
  };

  const handleSendMessage = async () => {
    if (!inputValue.trim()) return;
    const text = inputValue.trim();
    setInputValue("");
    addUserMessage(text);
    triggerGifPop();

    // 서비스 센터 정보 수집 중 (issue 단계만 텍스트 입력)
    if (serviceStep === "issue") {
      const updated = { ...serviceInfo, issue: text } as ServiceInfo;
      setServiceInfo(updated);
      setChatContext((prev) => ({ ...prev, issue: text, symptom: text, recommendedActions: ["service"] }));
      setServiceStep("idle");
      setTimeout(() => {
        setMessages((prev) => [...prev, {
          id: (Date.now() + 1).toString(), type: "bot",
          content: "입력하신 정보를 확인해주세요.\n방문 가능한 날짜를 선택해주시면 A/S를 신청해드릴게요.",
          time: now(),
          showServiceSummary: updated,
          showSchedule: true,
        }]);
      }, 600);
      return;
    }

    await submitAiMessage(text);
  };

  const handleOptionClick = (option: string) => {
    addUserMessage(option);
    triggerGifPop();

    setTimeout(async () => {
      // ── 최상위 메뉴 ──
      if (option === "제품 문제 해결") {
        setFlow("trouble");
        setChatContext({ intent: "trouble", session_id: undefined });
        setMessages((prev) => [...prev, { id: (Date.now() + 1).toString(), type: "bot", content: "어떤 제품에 문제가 생겼나요?", time: now(), options: PRODUCTS }]);
        return;
      }
      if (option === "가전 관리 방법") {
        setFlow("care");
        setChatContext({ intent: "care", session_id: undefined });
        setMessages((prev) => [...prev, { id: (Date.now() + 1).toString(), type: "bot", content: "관리 방법이 필요한 제품을 선택해주세요.", time: now(), options: PRODUCTS }]);
        return;
      }
      if (option === "서비스 센터 연결") {
        setFlow("service");
        setChatContext({ intent: "service", session_id: undefined });
        setMessages((prev) => [...prev, { id: (Date.now() + 1).toString(), type: "bot", content: "서비스를 신청할 제품을 선택해주세요.", time: now(), options: PRODUCTS }]);
        return;
      }

      // ── 제품 선택 ──
      if (PRODUCTS.includes(option)) {
        const types = getProductTypes(option);
        setChatContext((prev) => ({ ...prev, productCategory: option }));
        setMessages((prev) => [...prev, { id: (Date.now() + 1).toString(), type: "bot", content: `${option}의 종류를 선택해주세요.`, time: now(), options: types }]);
        setServiceInfo((prev) => ({ ...prev, product: option }));
        return;
      }

      // ── 제품군 선택 ──
      const allTypes = getAllProductTypes();
      if (allTypes.includes(option)) {
        setChatContext((prev) => ({ ...prev, productType: option }));
        if (flow === "service") {
          // 고객 정보 자동 불러오기
          const profile = await getUserProfile();
          setServiceInfo((prev) => ({
            ...prev,
            name: profile.name,
            phone: profile.phone,
            address: profile.address,
          }));
          // 자동 확인 메시지 후 모델 선택으로 이동
          setMessages((prev) => [...prev, {
            id: (Date.now() + 1).toString(), type: "bot",
            content: `고객 정보를 확인했습니다.\n\n이름: ${profile.name}\n연락처: ${profile.phone}\n주소: ${profile.address}\n\n이 정보로 진행할게요.`,
            time: now(),
          }]);
          nextServiceStep("model");
        } else {
          // 문제 해결 / 관리 방법 → 증상 선택
          setMessages((prev) => [...prev, {
            id: (Date.now() + 1).toString(), type: "bot",
            content: "🔍 현재 상태를 선택해주세요.",
            time: now(),
            problemOptions: getProblemOptions(),
          }]);
        }
        return;
      }

      // ── 증상 선택 ──
      if (getProblemOptions().includes(option) && option !== "그 외 다른 문제") {
        setChatContext((prev) => ({
          ...prev,
          session_id: undefined,
          symptom: option,
          recommendedActions: ["llm"],
        }));
        await submitAiMessage(option, { resetSession: true });
        return;
      }
      if (option === "그 외 다른 문제") {
        setChatContext((prev) => ({
          ...prev,
          symptom: option,
          recommendedActions: ["llm", "service"],
        }));
        setMessages((prev) => [...prev, {
          id: (Date.now() + 1).toString(), type: "bot",
          content: "불편하신 점을 자세히 입력해주세요.\n정확한 안내를 위해 최대한 구체적으로 작성해주시면 좋아요.",
          time: now(),
        }]);
        return;
      }

      // ── 매뉴얼 가이드 ──
      if (option === "매뉴얼 가이드") {
        setMessages((prev) => [...prev, {
          id: (Date.now() + 1).toString(), type: "bot",
          content: "영상과 순서를 따라 차례대로 진행해보세요.",
          time: now(),
          showVideo: true,
          showDoneAsk: true,
        }]);
        return;
      }

      // ── 완료 확인 ──
      if (option === "완료했어요") {
        const history = JSON.parse(localStorage.getItem("careHistory") || "[]");
        history.push({ id: Date.now().toString(), type: "Self A/S", title: "셀프 케어 완료", date: new Date().toISOString() });
        localStorage.setItem("careHistory", JSON.stringify(history));
        endSession();
        setMessages((prev) => [...prev, { id: (Date.now() + 1).toString(), type: "bot", content: "✅ 관리 완료가 기록되었어요!\n수고하셨습니다 😊", time: now() }]);
        return;
      }
      if (option === "아직 해결 안됐어요") {
        setMessages((prev) => [...prev, {
          id: (Date.now() + 1).toString(), type: "bot",
          content: "아직 해결이 안 되셨군요 😥\n어떤 부분에서 문제가 계속되는지 자세히 말씀해주시면 추가로 도움을 드릴게요.",
          time: now(),
        }]);
        return;
      }

      setMessages((prev) => [...prev, { id: (Date.now() + 1).toString(), type: "bot", content: "확인했습니다. 추가 도움이 필요하시면 말씀해주세요.", time: now() }]);
    }, 600);
  };

  const handleModelSelect = (device: ChatDeviceOption) => {
    addUserMessage(`${device.name} (${device.model})`);
    setServiceInfo((prev) => ({ ...prev, model: `${device.name} — ${device.model}` }));
    triggerGifPop();
    setChatContext((prev) => ({
      ...prev,
      deviceId: device.id,
      productName: device.name,
      model: device.model,
    }));
    nextServiceStep("issue");
  };

  const handleScheduleConfirm = (time: string) => {
    const full = `${selectedDate} ${time}`;
    addUserMessage(`${full} 방문 예약`);
    setServiceCompleted(true);
    setTimeout(() => {
      setMessages((prev) => [...prev, {
        id: (Date.now() + 1).toString(), type: "bot",
        content: "✅ A/S 신청이 완료되었습니다!\n\n담당 엔지니어가 방문 전날 확인 연락을 드릴 예정이에요.\n이용해주셔서 감사합니다 😊",
        time: now(),
        showServiceComplete: true,
      }]);
    }, 600);
  };

  return (
    <div
      className="relative h-full w-full overflow-hidden"
      style={{ background: "linear-gradient(160deg, #d6f2e8 0%, #f0f8e8 30%, #fce8f0 65%, #ede8f8 100%)" }}
    >
      <svg style={{ position: "absolute", width: 0, height: 0 }} aria-hidden="true">
        <defs>
          <filter id="remove-white" colorInterpolationFilters="sRGB" x="0" y="0" width="100%" height="100%">
            <feColorMatrix type="matrix" values="1 0 0 0 0 0 1 0 0 0 0 0 1 0 0 -40 -40 -40 120 -20" />
          </filter>
        </defs>
      </svg>

      <motion.div
        className="absolute inset-0 flex flex-col"
        animate={{ y: isInitial ? 0 : "-18%", opacity: isInitial ? 1 : 0, scale: isInitial ? 1 : 0.94, filter: isInitial ? "blur(0px)" : "blur(12px)" }}
        transition={{ duration: 1.1, ease: [0.4, 0.0, 0.15, 1] }}
        style={{ pointerEvents: isInitial ? "auto" : "none" }}
      >
        <div className="px-[25px] pt-[44px] pb-0 flex items-center gap-2">
          <button onClick={handleBack} className="p-1 -ml-1">
            <ChevronLeft size={22} className="text-[#555]" strokeWidth={2} />
          </button>
          <span className="font-['Pretendard:SemiBold',sans-serif] text-[17px] text-[#222]">LG Chat</span>
        </div>

        <div className="px-[28px] pt-[24px]">
          <p className="font-['Pretendard:SemiBold',sans-serif] text-[22px] text-[#222] leading-[1.35] tracking-[-0.4px]">
            {uiPhase === "initial" && <>안녕하세요!<br /><span style={{ color: "#5db88a" }}>무엇을 도와드릴까요?</span></>}
            {uiPhase === "selecting" && <>제품을 <span style={{ color: "#5db88a" }}>선택</span>해주세요</>}
            {uiPhase === "selecting-type" && <>종류를 <span style={{ color: "#5db88a" }}>선택</span>해주세요</>}
            {uiPhase === "pending-start" && <>선택을 <span style={{ color: "#5db88a" }}>완료</span>했어요!</>}
          </p>
        </div>

        <motion.div className="flex items-center justify-center" animate={{ flex: uiPhase === "initial" ? 1 : 0.35 }} transition={{ duration: 0.65 }}>
          <motion.div animate={{ width: uiPhase === "initial" ? 230 : 100, height: uiPhase === "initial" ? 230 : 100, y: [0, -10, 0], scale: gifPop ? 1.08 : 1 }} transition={{ y: { duration: 3.5, repeat: Infinity, ease: "easeInOut" }, scale: { duration: 0.2 } }} style={{ position: "relative", isolation: "isolate" }}>
            <div style={{ position: "absolute", inset: 10, borderRadius: "50%", background: "radial-gradient(circle at 40% 35%, #d4f7d4 0%, #b8f0d8 20%, #c8f0f8 40%, #e8d8f8 65%, #f8d8ec 85%)", boxShadow: "0 0 40px 12px rgba(180,240,200,0.55), 0 0 80px 24px rgba(220,180,255,0.30)", filter: "blur(2px)" }} />
            <img src={lgGif} alt="LG AI" style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "contain", filter: "url(#remove-white)" }} />
          </motion.div>
        </motion.div>

        <div className="px-[18px] pb-4">
          {floatingChips.length > 0 && (
            <div className="flex flex-wrap items-center gap-2 mb-3">
              {floatingChips.map((chip, i) => (
                <motion.div key={`${chip}-${i}`} initial={{ y: 28, opacity: 0 }} animate={{ y: 0, opacity: 1 }} transition={{ delay: i * 0.09 }} className="flex items-center gap-1.5 px-3 py-1.5 rounded-full" style={{ background: "rgba(255,255,255,0.85)", border: "1px solid rgba(155,142,246,0.4)", boxShadow: "0 4px 12px rgba(155,142,246,0.2)" }}>
                  <span className="text-[11px]">✓</span><span className="font-['Pretendard:SemiBold',sans-serif] text-[12px] text-[#9b8ef6]">{chip}</span>
                </motion.div>
              ))}
              <button onClick={() => { setUiPhase("initial"); setFloatingChips([]); setSelectingProducts(false); setSelectingTypes(false); setFlow(null); }} className="w-7 h-7 rounded-full flex items-center justify-center" style={{ background: "rgba(255,255,255,0.85)", border: "1px solid rgba(155,142,246,0.4)" }}>
                <ChevronLeft size={14} className="text-[#9b8ef6]" strokeWidth={2.5} />
              </button>
            </div>
          )}

          {uiPhase === "initial" && (
            <div className="grid grid-cols-2 gap-2 mb-3">
              {[
                { icon: <Wrench size={15} />, label: "제품 문제 해결", color: "#5db88a" },
                { icon: <Lightbulb size={15} />, label: "가전 관리 방법", color: "#5ba8d8" },
                { icon: <ClipboardList size={15} />, label: "서비스 센터 연결", color: "#d87ab0" },
                { icon: <CircleHelp size={15} />, label: "자주 묻는 질문", color: "#9b8ef6" },
              ].map((item, i) => (
                <motion.button key={item.label} onClick={() => i < 3 && handleInitialSelect(item.label)} whileTap={{ scale: 0.96 }} className="flex items-center gap-2 px-4 py-3 rounded-[14px] text-left" style={{ background: "rgba(255,255,255,0.62)", backdropFilter: "blur(16px)", WebkitBackdropFilter: "blur(16px)", border: "1px solid rgba(255,255,255,0.88)", boxShadow: "0 4px 14px rgba(0,0,0,0.05)" }}>
                  <span style={{ color: item.color }}>{item.icon}</span><p className="font-['Pretendard:Medium',sans-serif] text-[12px] text-[#333]">{item.label}</p>
                </motion.button>
              ))}
            </div>
          )}

          {uiPhase === "selecting" && selectingProducts && <div className="grid grid-cols-2 gap-2 mb-3">{PRODUCTS.map((product, i) => <motion.button key={product} initial={{ y: 28, opacity: 0 }} animate={{ y: 0, opacity: 1 }} transition={{ delay: i * 0.09 }} onClick={() => handleProductSelect(product, floatingChips[0])} whileTap={{ scale: 0.96 }} className="py-3 px-4 rounded-[14px] text-left font-['Pretendard:Medium',sans-serif] text-[13px] text-[#333]" style={{ background: "rgba(255,255,255,0.75)", border: "1px solid rgba(255,255,255,0.9)", boxShadow: "0 3px 10px rgba(0,0,0,0.06)" }}>{product}</motion.button>)}</div>}

          {uiPhase === "selecting-type" && selectingTypes && <div className="grid grid-cols-2 gap-2 mb-3">{getProductTypes(selectedProduct).map((type, i) => <motion.button key={type} initial={{ y: 28, opacity: 0 }} animate={{ y: 0, opacity: 1 }} transition={{ delay: i * 0.09 }} onClick={() => handleTypeSelect(type, floatingChips[0], floatingChips[1])} whileTap={{ scale: 0.96 }} className="py-3 px-4 rounded-[14px] text-left font-['Pretendard:Medium',sans-serif] text-[13px] text-[#333]" style={{ background: "rgba(255,255,255,0.75)", border: "1px solid rgba(255,255,255,0.9)", boxShadow: "0 3px 10px rgba(0,0,0,0.06)" }}>{type}</motion.button>)}</div>}

          {uiPhase === "pending-start" && <motion.button initial={{ y: 12, opacity: 0, scale: 0.96 }} animate={{ y: 0, opacity: 1, scale: 1 }} onClick={handleStartChat} whileTap={{ scale: 0.97 }} className="w-full py-[15px] mt-[15px] rounded-[28px] font-['Pretendard:SemiBold',sans-serif] text-[15px] text-white" style={{ background: "linear-gradient(135deg, #9b8ef6 0%, #6b8ef6 100%)", boxShadow: "0 6px 24px rgba(155,142,246,0.38), inset 0 1px 0 rgba(255,255,255,0.25)" }}>채팅을 시작할까요?</motion.button>}
        </div>
      </motion.div>

      <motion.div className="absolute inset-0 flex flex-col" animate={{ y: isInitial ? "12%" : 0, opacity: isInitial ? 0 : 1, scale: isInitial ? 0.96 : 1, filter: isInitial ? "blur(10px)" : "blur(0px)" }} transition={{ duration: 1.1, ease: [0.25, 0.0, 0.15, 1], delay: isInitial ? 0 : 0.18 }} style={{ pointerEvents: isInitial ? "none" : "auto" }}>
      {/* 헤더 */}
      <div className="px-[25px] pt-[40px] pb-3">
        <div className="flex items-center gap-2">
          <button onClick={handleBack} className="p-0 -ml-1">
            <ChevronLeft size={20} className="text-black cursor-pointer" strokeWidth={2} />
          </button>
          <p className="font-['Pretendard:Medium',sans-serif] text-[20px] tracking-[-0.3px] text-black leading-[15px]">
            Chat
          </p>
        </div>
      </div>

      {/* 메시지 영역 */}
      <div className="flex-1 overflow-y-auto px-[20px] py-6 space-y-4">
        {messages.map((message, index) => (
          <div key={message.id} className="space-y-1" ref={message.problemOptions ? problemMsgRef : undefined}>
            {message.type === "bot" ? (
              <>
                <div className="flex justify-start">
                  <div className="bg-white rounded-[18px] px-[16px] py-[12px] max-w-[290px] shadow-sm">
                    <p className="font-['Pretendard:Medium',sans-serif] text-[14px] text-black whitespace-pre-line leading-[20px] tracking-[-0.2px]">
                      {message.content}
                    </p>
                  </div>
                </div>
                <p className="font-['Inter:Regular',sans-serif] text-[10px] text-[#999] pl-2 mt-0.5">
                  {message.time}
                </p>

                {/* 일반 옵션 버튼 */}
                {message.options && (
                  <div className="flex flex-wrap gap-2 mt-3 pl-1">
                    {message.options.map((option, idx) => (
                      <button
                        key={idx}
                        onClick={() => handleOptionClick(option)}
                        className="bg-[#ff4c49] text-white rounded-[12px] py-[9px] px-[14px] font-['Pretendard:SemiBold',sans-serif] text-[13px] hover:bg-[#e63d3a] transition-colors shadow-sm"
                      >
                        {option}
                      </button>
                    ))}
                  </div>
                )}

                {/* 증상 옵션 버튼 */}
                {message.problemOptions && (
                  <div className="flex flex-col gap-2 mt-3 pl-1">
                    {message.problemOptions.map((option, idx) => (
                      <button
                        key={idx}
                        onClick={() => handleOptionClick(option)}
                        className="bg-[#ff4c49] text-white rounded-[10px] py-[10px] px-[14px] text-left font-['Pretendard:Medium',sans-serif] text-[13px] leading-snug hover:bg-[#e63d3a] transition-colors w-[220px] shadow-sm"
                      >
                        {option}
                      </button>
                    ))}
                  </div>
                )}

                {/* 공식자료 no-match 차단 안내 */}
                {message.cardPolicy?.card_type === "safety_block" && (
                  <div className="mt-3 pl-1 max-w-[290px]">
                    <div className="bg-white rounded-[15px] px-4 py-3 w-full shadow-sm border border-[#ffd7d7]">
                      <p className="font-['Pretendard:SemiBold',sans-serif] text-[13px] text-[#ff4c49] mb-1">
                        {message.cardPolicy.title || "공식자료 확인 불가"}
                      </p>
                      <p className="font-['Pretendard:Regular',sans-serif] text-[12px] text-[#444] leading-[18px]">
                        {message.cardPolicy.description || "공식 근거가 확인되지 않아 AR 자가 안내를 시작하지 않습니다."}
                      </p>
                    </div>
                  </div>
                )}

                {/* 가이드 버튼 */}
                {message.guideButtons && (
                  <div className="flex gap-2 mt-3 pl-1 max-w-[290px]">
                    {message.guideButtons.includes("manual") && (
                      <button
                        onClick={() => {
                          if (message.guideOptions) {
                            navigate("/self-care", { state: { tab: "manual", guideOptions: message.guideOptions } });
                            return;
                          }
                          handleOptionClick("매뉴얼 가이드");
                        }}
                        className="flex-1 bg-[#ff4c49] text-white rounded-[12px] py-[10px] px-[16px] font-['Pretendard:SemiBold',sans-serif] text-[13px] hover:bg-[#e63d3a] transition-colors shadow-sm"
                      >
                        매뉴얼 가이드
                      </button>
                    )}
                    {message.guideButtons.includes("ar") && (
                      <button
                        onClick={() => handleArGuideClick(message)}
                        className="flex-1 bg-white border border-[#ff4c49] text-[#ff4c49] rounded-[12px] py-[10px] px-[16px] font-['Pretendard:SemiBold',sans-serif] text-[13px] hover:bg-[#fff5f5] transition-colors shadow-sm"
                      >
                        AR 가이드
                      </button>
                    )}
                    {message.guideButtons.includes("service") && (
                      <button
                        onClick={() => handleOptionClick("서비스 센터 연결")}
                        className="flex-1 bg-white border border-[#ff4c49] text-[#ff4c49] rounded-[12px] py-[10px] px-[16px] font-['Pretendard:SemiBold',sans-serif] text-[13px] hover:bg-[#fff5f5] transition-colors shadow-sm"
                      >
                        서비스 센터 연결
                      </button>
                    )}
                  </div>
                )}

                {/* 공식근거 기반 영상 + 단계별 가이드 */}
                {message.guideOptions && (
                  <div className="mt-3 pl-1 space-y-2 max-w-[290px]">
                    {(() => {
                      const video = guideVideo(message.guideOptions);
                      const manual = message.guideOptions.manual_guides?.[0];
                      const procedureType = message.guideOptions.procedure_type;
                      const procedureLabel = getProcedureLabel(procedureType);
                      const steps = extractGuideSteps(manual, procedureType);
                      return (
                        <>
                          {(video.embedUrl || video.videoUrl) && (
                            <div className="bg-gray-900 w-full aspect-video rounded-[15px] overflow-hidden shadow-sm">
                              {video.embedUrl ? (
                                <iframe
                                  title={video.title}
                                  src={video.embedUrl}
                                  className="w-full h-full"
                                  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                                  allowFullScreen
                                />
                              ) : (
                                <video controls className="w-full h-full object-cover" src={video.videoUrl || undefined} controlsList="nodownload">
                                  브라우저가 비디오 태그를 지원하지 않습니다.
                                </video>
                              )}
                            </div>
                          )}
                          <div className="bg-white rounded-[15px] px-4 py-3 w-full shadow-sm border border-[#f0f0f0]">
                            <div className="flex items-center justify-between gap-2 mb-2">
                              <p className="font-['Pretendard:SemiBold',sans-serif] text-[13px] text-black">📋 {procedureLabel} 순서</p>
                              <span className="font-['Pretendard:Medium',sans-serif] text-[9px] text-[#2d9b69] bg-[#eaf8f1] rounded-full px-2 py-[2px] whitespace-nowrap">
                                LG 공식 기준
                              </span>
                            </div>
                            {steps.map((step, i) => (
                              <p key={i} className="font-['Pretendard:Regular',sans-serif] text-[12px] text-[#444] leading-[18px]">
                                {`${i + 1}. ${step}`}
                              </p>
                            ))}
                          </div>
                        </>
                      );
                    })()}
                  </div>
                )}

                {/* 비디오 + 매뉴얼 */}
                {message.showVideo && (
                  <div className="mt-3 pl-1 space-y-2 max-w-[290px]">
                    <div className="bg-gray-900 w-full aspect-video rounded-[15px] overflow-hidden shadow-sm">
                      <video controls className="w-full h-full object-cover" src={aiAlertVideo} controlsList="nodownload">
                        브라우저가 비디오 태그를 지원하지 않습니다.
                      </video>
                    </div>
                    <div className="bg-white rounded-[15px] px-4 py-3 w-full shadow-sm border border-[#f0f0f0]">
                      <p className="font-['Pretendard:SemiBold',sans-serif] text-[13px] text-black mb-2">📋 필터 청소 순서</p>
                      {["① 전원을 끄고 플러그를 뽑으세요.", "② 필터 커버를 천천히 들어 올리세요.", "③ 잠금을 풀고 필터를 분리하세요.", "④ 흐르는 물로 헹군 후 그늘에 말리세요.", "⑤ 필터를 재장착하고 커버를 닫으세요."].map((step, i) => (
                        <p key={i} className="font-['Pretendard:Regular',sans-serif] text-[12px] text-[#444] leading-[18px]">{step}</p>
                      ))}
                    </div>
                  </div>
                )}

                {/* 완료 확인 버튼 */}
                {(message.showDoneAsk || message.guideOptions) && index === messages.length - 1 && (
                  <div className="mt-3 pl-1">
                    <div className="bg-white rounded-[15px] px-4 py-4 max-w-[290px] shadow-sm border border-[#f0ecec]">
                      <p className="font-['Pretendard:SemiBold',sans-serif] text-[14px] text-black mb-3">관리를 완료하셨나요?</p>
                      <div className="flex gap-2">
                        <button onClick={() => handleOptionClick("완료했어요")}
                          className="flex-1 bg-gradient-to-r from-[#F77B50] to-[#F05C5C] text-white rounded-[10px] py-2.5 font-['Pretendard:SemiBold',sans-serif] text-[13px]">
                          완료했어요
                        </button>
                        <button onClick={() => handleOptionClick("아직 해결 안됐어요")}
                          className="flex-1 bg-white border border-[#F77B50] text-[#F77B50] rounded-[10px] py-2.5 font-['Pretendard:SemiBold',sans-serif] text-[13px]">
                          해결 안됐어요
                        </button>
                      </div>
                    </div>
                  </div>
                )}

                {/* 모델 선택 버튼 */}
                {message.modelOptions && (
                  <div className="flex flex-col gap-2 mt-3 pl-1">
                    {message.modelOptions.map((device) => (
                      <button
                        key={device.id}
                        onClick={() => handleModelSelect(device)}
                        className="bg-white border border-[#ff4c49] rounded-[12px] px-[14px] py-[10px] text-left shadow-sm hover:bg-[#fff5f5] transition-colors w-[240px]"
                      >
                        <p className="font-['Pretendard:SemiBold',sans-serif] text-[13px] text-[#ff4c49]">{device.name}</p>
                        <p className="font-['Pretendard:Regular',sans-serif] text-[11px] text-[#888] mt-[2px]">{device.model}</p>
                      </button>
                    ))}
                  </div>
                )}

                {/* 서비스 정보 요약 */}
                {message.showServiceSummary && (
                  <div className="mt-2 pl-2">
                    <div className="bg-white rounded-[15px] px-4 py-3 w-[220px] shadow-sm border border-[#f0ecec]">
                      <p className="font-['Pretendard:SemiBold',sans-serif] text-[11px] text-[#ff4c49] mb-2">📋 신청 정보 확인</p>
                      {[
                        ["제품", message.showServiceSummary.product],
                        ["성함", message.showServiceSummary.name],
                        ["연락처", message.showServiceSummary.phone],
                        ["주소", message.showServiceSummary.address],
                        ["모델명", message.showServiceSummary.model],
                        ["문제 증상", message.showServiceSummary.issue],
                      ].map(([label, value]) => (
                        <div key={label} className="flex gap-2 mb-1">
                          <span className="font-['Pretendard:SemiBold',sans-serif] text-[9px] text-[#888] w-[42px] shrink-0">{label}</span>
                          <span className="font-['Pretendard:Regular',sans-serif] text-[9px] text-[#333] leading-tight">{value}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* 날짜/시간 선택 */}
                {message.showSchedule && index === messages.length - 1 && (
                  <div className="mt-3 pl-2">
                    <div className="bg-white rounded-[15px] px-4 py-3 w-[240px] shadow-sm border border-[#f0ecec]">
                      <p className="font-['Pretendard:SemiBold',sans-serif] text-[11px] text-black mb-2">📅 방문 날짜 선택</p>
                      <div className="flex flex-wrap gap-1 mb-3">
                        {AVAILABLE_DATES.map((d) => (
                          <button key={d.value}
                            onClick={() => setSelectedDate(d.value)}
                            className={`px-2 py-1 rounded-[6px] text-[9px] font-['Pretendard:Medium',sans-serif] transition-colors ${
                              selectedDate === d.value
                                ? "bg-[#ff4c49] text-white"
                                : "bg-[#f5f5f5] text-[#444]"
                            }`}>
                            {d.label}
                          </button>
                        ))}
                      </div>
                      {selectedDate && (
                        <>
                          <p className="font-['Pretendard:SemiBold',sans-serif] text-[11px] text-black mb-2">⏰ 방문 시간 선택</p>
                          <div className="flex flex-col gap-1">
                            {TIME_SLOTS.map((t) => (
                              <button key={t}
                                onClick={() => handleScheduleConfirm(t)}
                                className="w-full bg-[#fff5f5] border border-[#ff4c49] text-[#ff4c49] rounded-[8px] py-1.5 font-['Pretendard:Medium',sans-serif] text-[10px] hover:bg-[#ff4c49] hover:text-white transition-colors">
                                {t}
                              </button>
                            ))}
                          </div>
                        </>
                      )}
                    </div>
                  </div>
                )}

                {/* A/S 신청 완료 */}
                {message.showServiceComplete && (
                  <div className="mt-2 pl-2">
                    <div className="bg-gradient-to-br from-[#fff5f5] to-[#fff] rounded-[15px] px-4 py-3 w-[220px] shadow-sm border border-[#ffdddd] text-center">
                      <p className="text-[28px] mb-1">🎉</p>
                      <p className="font-['Pretendard:Bold',sans-serif] text-[12px] text-[#ff4c49]">A/S 신청 완료</p>
                      <p className="font-['Pretendard:Regular',sans-serif] text-[9px] text-[#888] mt-1">방문 전날 확인 연락 예정</p>
                    </div>
                  </div>
                )}
              </>
            ) : (
              <>
                <div className="flex justify-end">
                  <div className="bg-[#555] rounded-[18px] px-[16px] py-[12px] max-w-[280px]">
                    <p className="font-['Pretendard:Medium',sans-serif] text-[14px] text-white leading-[20px] tracking-[-0.2px]">
                      {message.content}
                    </p>
                  </div>
                </div>
                <p className="font-['Inter:Regular',sans-serif] text-[10px] text-[#999] pr-2 text-right mt-0.5">
                  {message.time}
                </p>
              </>
            )}
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* 입력 영역 */}
      <div className="p-4 pb-5">
        <div
          className="flex items-center gap-2 rounded-[28px] px-4 py-3"
          style={{
            background: "rgba(255,255,255,0.72)",
            backdropFilter: "blur(28px)",
            WebkitBackdropFilter: "blur(28px)",
            border: "1px solid rgba(255,255,255,0.85)",
            boxShadow: "0 8px 32px rgba(0,0,0,0.10), inset 0 1px 0 rgba(255,255,255,0.95)",
          }}
        >
          <button className="text-[#333333] flex-shrink-0">
            <Paperclip size={18} strokeWidth={1.5} />
          </button>
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={(e) => e.key === "Enter" && handleSendMessage()}
            placeholder="메시지를 입력해주세요..."
            className="flex-1 bg-transparent outline-none font-['Pretendard:Regular',sans-serif] text-[13px] text-black placeholder:text-[#949ba5]"
          />
          <button onClick={handleSendMessage} className="text-[#4B4B4B] hover:text-[#000] transition-colors flex-shrink-0">
            <Send size={18} strokeWidth={1.5} />
          </button>
        </div>
      </div>
      </motion.div>
    </div>
  );
}

