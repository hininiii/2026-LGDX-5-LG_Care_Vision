import { useState, useRef, useEffect, useCallback } from "react";
import { useNavigate } from "react-router";
import { ChevronLeft, Send, Paperclip, Lightbulb, ClipboardList, Wrench, CircleHelp, Check } from "lucide-react";
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

const LEGACY_CHAT_STORAGE_KEYS = ["chat_messages", "chat_messages_v20260612", "chat_messages_v20260618_transition"];
const CHAT_STORAGE_KEY = "chat_messages_v20260618_transition_v2";
const CHAT_ENDED_KEY = "chat_session_ended";

const now = () =>
  new Date().toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit" });

const PRODUCTS = getProductCategories();
const AVAILABLE_DATES = getAvailableDates();
const TIME_SLOTS = getTimeSlots();

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
  no_cooling_self_check: ["Check Temperature Setting", "Check Filter Status", "Check Outdoor Unit Ventilation", "Check Indoor Environment", "Request Professional Service"],
  noise_self_check: ["Check Warning Signs", "Check Cover Status", "Check Nearby Items", "Check Tilt", "Check Low Airflow", "Do Not Disassemble", "Request Professional Service"],
  power_troubleshooting: ["Check Warning Signs", "Check Display", "Check Power Connection", "Check Circuit Breaker", "Request Professional Service"],
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
    { targetHint: "Air conditioner body", targetClasses: ["aircon"] },
    { targetHint: "Air outlet / airflow path", targetClasses: ["outlet"], contextClasses: ["aircon"] },
    { targetHint: "Filter mesh", targetClasses: ["filter"], contextClasses: ["aircon"] },
    { targetHint: "Air conditioner body", targetClasses: ["aircon"] },
    { targetHint: "Air conditioner body", targetClasses: ["aircon"] },
    { targetHint: "Air conditioner body", targetClasses: ["aircon"] },
  ],
};

const CLIENT_AR_GUIDE_PROCEDURES = new Set(Object.keys(AR_GUIDE_STEP_TARGETS));

const canOpenArGuide = (guideOptions?: ChatGuideOptions) => {
  if (!guideOptions) return true;
  if ((guideOptions.ar_guides?.length ?? 0) > 0) return true;
  const procedureType = guideOptions.procedure_type;
  return Boolean(procedureType && CLIENT_AR_GUIDE_PROCEDURES.has(procedureType));
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

const getProcedureLabel = (procedure?: string) =>
  (procedure && PROCEDURE_LABELS[procedure]) || "Guide";

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
  const [problemFocusSpacer, setProblemFocusSpacer] = useState(false);
  const [expandedManualGuideIds, setExpandedManualGuideIds] = useState<string[]>([]);

  const triggerGifPop = useCallback(() => {
    setGifPop(true);
    setTimeout(() => setGifPop(false), 700);
  }, []);

  const handleInitialSelect = (label: string) => {
    setFloatingChips([label]);
    setUiPhase("selecting");
    setSelectingProducts(false);
    setSelectingTypes(false);
    if (label === "Troubleshoot Product Issue") setFlow("trouble");
    else if (label === "Appliance Care Guide") setFlow("care");
    else if (label === "Connect to Service Center") setFlow("service");
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
    setProblemFocusSpacer(false);
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
  const isResumedChatEntry = useRef(messages.length > 1).current;
  const introLayerTransition = isResumedChatEntry
    ? { duration: 0 }
    : { duration: 1.1, ease: [0.4, 0.0, 0.15, 1] };
  const chatLayerTransition = isResumedChatEntry
    ? { duration: 0 }
    : { duration: 1.1, ease: [0.25, 0.0, 0.15, 1], delay: isInitial ? 0 : 0.18 };
  const shouldRenderChatLayer = !isInitial;

  const handleBack = () => {
    if (serviceCompleted) {
      endSession();
    }
    navigate("/");
  };

  const scrollToBottom = () => messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  useEffect(() => {
    if (!problemFocusSpacer) {
      scrollToBottom();
    }
  }, [messages, problemFocusSpacer]);
  useEffect(() => {
    localStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(messages));
  }, [messages]);

  // AR Guide 복귀 시 동기화
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
    if (response.guide_options && canOpenArGuide(response.guide_options)) return "ar_ready";
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
        content: "Analyzing the symptom.",
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
                content: "Could not verify the API connection. Please try again later.",
                status: "blocked",
              }
            : message,
        ),
      );
    }
  };

  const handleArGuideClick = (message: Message) => {
    if (canOpenArGuide(message.guideOptions)) {
      const procedureType = message.guideOptions?.procedure_type;
      const procedureQuery = procedureType ? `?procedure_type=${encodeURIComponent(procedureType)}` : "";
      navigate(`/ar-guide${procedureQuery}`, {
        state: {
          from: "/chat",
          procedureType,
          guideTitle: message.guideOptions?.display_title || getProcedureLabel(procedureType),
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
        content: "An official manual guide is available for this symptom, but the AR guide template is not ready yet. Please check the video and step-by-step manual first.",
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
          content: "Select the registered appliance that needs service.",
          time: now(),
          modelOptions: devices,
        }]);
      }, 600);
    } else if (step === "issue") {
      addBotMessage("Please describe the issue in detail.");
    }
  };

  const handleSendMessage = async () => {
    if (!inputValue.trim()) return;
    const text = inputValue.trim();
    setInputValue("");
    setProblemFocusSpacer(false);
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
          content: "Please review the information you entered.\nSelect an available visit date and I'll request service for you.",
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
      if (option === "Troubleshoot Product Issue") {
        setFlow("trouble");
        setChatContext({ intent: "trouble", session_id: undefined });
        setMessages((prev) => [...prev, { id: (Date.now() + 1).toString(), type: "bot", content: "Which product has an issue?", time: now(), options: PRODUCTS }]);
        return;
      }
      if (option === "Appliance Care Guide") {
        setFlow("care");
        setChatContext({ intent: "care", session_id: undefined });
        setMessages((prev) => [...prev, { id: (Date.now() + 1).toString(), type: "bot", content: "Select the product you need care instructions for.", time: now(), options: PRODUCTS }]);
        return;
      }
      if (option === "Connect to Service Center") {
        setFlow("service");
        setChatContext({ intent: "service", session_id: undefined });
        setMessages((prev) => [...prev, { id: (Date.now() + 1).toString(), type: "bot", content: "Select the product you want to request service for.", time: now(), options: PRODUCTS }]);
        return;
      }

      // ── 제품 선택 ──
      if (PRODUCTS.includes(option)) {
        const types = getProductTypes(option);
        setChatContext((prev) => ({ ...prev, productCategory: option }));
        setMessages((prev) => [...prev, { id: (Date.now() + 1).toString(), type: "bot", content: `Select a ${option} type.`, time: now(), options: types }]);
        setServiceInfo((prev) => ({ ...prev, product: option }));
        return;
      }

      // ── Product Type 선택 ──
      const allTypes = getAllProductTypes();
      if (allTypes.includes(option)) {
        setChatContext((prev) => ({ ...prev, productType: option }));
        if (flow === "service") {
          // 고객 정보 Auto 불러오기
          const profile = await getUserProfile();
          setServiceInfo((prev) => ({
            ...prev,
            name: profile.name,
            phone: profile.phone,
            address: profile.address,
          }));
          // Auto 확인 메시지 후 모델 선택으로 이동
          setMessages((prev) => [...prev, {
            id: (Date.now() + 1).toString(), type: "bot",
            content: `Customer information confirmed.\n\nName: ${profile.name}\nPhone: ${profile.phone}\nAddress: ${profile.address}\n\nI'll proceed with this information.`,
            time: now(),
          }]);
          nextServiceStep("model");
        } else {
          // 문제 해결 / Care 방법 → 증상 선택
          setProblemFocusSpacer(true);
          setMessages((prev) => [...prev, {
            id: (Date.now() + 1).toString(), type: "bot",
            content: "🔍 Please select the current status.",
            time: now(),
            problemOptions: getProblemOptions(),
          }]);
          setTimeout(() => {
            problemMsgRef.current?.scrollIntoView({ behavior: "instant", block: "start" });
          }, 80);
        }
        return;
      }

      // ── 증상 선택 ──
      if (getProblemOptions().includes(option) && option !== "Other issue") {
        setProblemFocusSpacer(false);
        setChatContext((prev) => ({
          ...prev,
          session_id: undefined,
          symptom: option,
          recommendedActions: ["llm"],
        }));
        await submitAiMessage(option, { resetSession: true });
        return;
      }
      if (option === "Other issue") {
        setProblemFocusSpacer(false);
        setChatContext((prev) => ({
          ...prev,
          symptom: option,
          recommendedActions: ["llm", "service"],
        }));
        setMessages((prev) => [...prev, {
          id: (Date.now() + 1).toString(), type: "bot",
          content: "Please describe the inconvenience in detail.\nThe more specific you are, the more accurate the guidance can be.",
          time: now(),
        }]);
        return;
      }

      // ── Manual Guide ──
      if (option === "Manual Guide") {
        setMessages((prev) => [...prev, {
          id: (Date.now() + 1).toString(), type: "bot",
          content: "Follow the video and steps in order.",
          time: now(),
          showVideo: true,
          showDoneAsk: true,
        }]);
        return;
      }

      // ── Done 확인 ──
      if (option === "Completed") {
        const history = JSON.parse(localStorage.getItem("careHistory") || "[]");
        history.push({ id: Date.now().toString(), type: "Self A/S", title: "Self Care Completed", date: new Date().toISOString() });
        localStorage.setItem("careHistory", JSON.stringify(history));
        endSession();
        setMessages((prev) => [...prev, { id: (Date.now() + 1).toString(), type: "bot", content: "✅ Care completion has been recorded! Great work 😊", time: now() }]);
        return;
      }
      if (option === "Still not resolved") {
        setMessages((prev) => [...prev, {
          id: (Date.now() + 1).toString(), type: "bot",
          content: "It is still not resolved 😥\nTell me which part is still causing trouble and I'll help further.",
          time: now(),
        }]);
        return;
      }

      setMessages((prev) => [...prev, { id: (Date.now() + 1).toString(), type: "bot", content: "Got it. Let me know if you need more help.", time: now() }]);
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
    addUserMessage(`${full} visit reservation`);
    setServiceCompleted(true);
    setTimeout(() => {
      setMessages((prev) => [...prev, {
        id: (Date.now() + 1).toString(), type: "bot",
        content: "✅ Service request completed!\n\nThe assigned engineer will contact you the day before the visit.\nThank you for using our service 😊",
        time: now(),
        showServiceComplete: true,
      }]);
    }, 600);
  };

  const chatGlassSurface = {
    background: "rgba(255,255,255,0.78)",
    backdropFilter: "blur(12px)",
    WebkitBackdropFilter: "blur(12px)",
    border: "1px solid rgba(255,255,255,0.9)",
    boxShadow: "0 3px 10px rgba(0,0,0,0.07)",
  } as const;

  const chatSoftCard = {
    background: "rgba(255,255,255,0.82)",
    backdropFilter: "blur(14px)",
    WebkitBackdropFilter: "blur(14px)",
    border: "1px solid rgba(255,255,255,0.9)",
    boxShadow: "0 4px 16px rgba(0,0,0,0.08)",
  } as const;

  const chatAccentSurface = {
    background: "linear-gradient(135deg, #9b8ef6, #7b9ef8)",
    boxShadow: "0 4px 14px rgba(155,142,246,0.3)",
  } as const;

  return (
    <motion.div
      className="relative h-full w-full overflow-hidden"
      initial={isResumedChatEntry ? { opacity: 0, y: 14 } : { opacity: 0, y: 18, filter: "blur(8px)" }}
      animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
      transition={isResumedChatEntry ? { duration: 0.85, ease: [0.22, 1, 0.36, 1] } : { duration: 1.8, ease: [0.22, 1, 0.36, 1] }}
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
        transition={introLayerTransition}
        style={{ pointerEvents: isInitial ? "auto" : "none" }}
      >
        <div className="px-[25px] pt-[44px] pb-0 flex items-center gap-1">
          <button onClick={handleBack} className="p-1 -ml-1">
            <ChevronLeft size={22} className="text-[#555]" strokeWidth={2} />
          </button>
          <span className="font-['Pretendard:Medium',sans-serif] text-[20px] tracking-[-0.3px] text-black leading-[15px]">LG Chat</span>
        </div>

        <div className="px-[28px] pt-[24px]">
          <p className="font-['Pretendard:SemiBold',sans-serif] text-[22px] text-[#222] leading-[1.35] tracking-[-0.4px]">
            {uiPhase === "initial" && <>Hello!<br /><span style={{ color: "#5db88a" }}>How can I help you?</span></>}
            {uiPhase === "selecting" && <>Select a <span style={{ color: "#5db88a" }}>product</span></>}
            {uiPhase === "selecting-type" && <>Select a <span style={{ color: "#5db88a" }}>type</span></>}
            {uiPhase === "pending-start" && <>Selection <span style={{ color: "#5db88a" }}>complete</span>!</>}
          </p>
        </div>

        <motion.div
          className="flex items-center justify-center"
          animate={{ flex: uiPhase === "initial" ? 1 : 0.35 }}
          transition={{ duration: 0.65 }}
        >
          <motion.div
            animate={{ width: uiPhase === "initial" ? 230 : 100, height: uiPhase === "initial" ? 230 : 100, y: [0, -10, 0], scale: gifPop ? 1.08 : 1 }}
            transition={{
              y: { duration: 3.5, repeat: Infinity, ease: "easeInOut" },
              scale: { duration: 0.2 },
            }}
            style={{ position: "relative", isolation: "isolate" }}
          >
            <div style={{ position: "absolute", inset: 10, borderRadius: "50%", background: "radial-gradient(circle at 40% 35%, #d4f7d4 0%, #b8f0d8 20%, #c8f0f8 40%, #e8d8f8 65%, #f8d8ec 85%)", boxShadow: "0 0 40px 12px rgba(180,240,200,0.55), 0 0 80px 24px rgba(220,180,255,0.30)", filter: "blur(2px)" }} />
            <img src={lgGif} alt="LG AI" style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "contain", filter: "url(#remove-white)" }} />
          </motion.div>
        </motion.div>

        <div className="px-[18px] pb-4">
          {floatingChips.length > 0 && (
            <div className="flex flex-wrap items-center gap-2 mb-3">
              {floatingChips.map((chip, i) => (
                <motion.div key={`${chip}-${i}`} initial={{ y: 28, opacity: 0 }} animate={{ y: 0, opacity: 1 }} transition={{ delay: i * 0.09 }} className="flex items-center gap-1.5 px-3 py-1.5 rounded-full" style={{ background: "rgba(255,255,255,0.85)", border: "1px solid rgba(155,142,246,0.4)", boxShadow: "0 4px 12px rgba(155,142,246,0.2)" }}>
                  <span className="text-[#9b8ef6]"><Check size={11} strokeWidth={3} /></span><span className="font-['Pretendard:SemiBold',sans-serif] text-[12px] text-[#9b8ef6]">{chip}</span>
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
                { icon: <Wrench size={15} />, label: "Troubleshoot Product Issue", color: "#5db88a" },
                { icon: <Lightbulb size={15} />, label: "Appliance Care Guide", color: "#5ba8d8" },
                { icon: <ClipboardList size={15} />, label: "Connect to Service Center", color: "#d87ab0" },
                { icon: <CircleHelp size={15} />, label: "FAQ", color: "#9b8ef6" },
              ].map((item, i) => (
                <motion.button key={item.label} onClick={() => i < 3 && handleInitialSelect(item.label)} whileTap={{ scale: 0.96 }} className="flex items-center gap-2 px-4 py-3 rounded-[14px] text-left" style={{ background: "rgba(255,255,255,0.62)", backdropFilter: "blur(16px)", WebkitBackdropFilter: "blur(16px)", border: "1px solid rgba(255,255,255,0.88)", boxShadow: "0 4px 14px rgba(0,0,0,0.05)" }}>
                  <span style={{ color: item.color }}>{item.icon}</span><p className="font-['Pretendard:Medium',sans-serif] text-[12px] text-[#333]">{item.label}</p>
                </motion.button>
              ))}
            </div>
          )}

          {uiPhase === "selecting" && selectingProducts && <div className="grid grid-cols-2 gap-2 mb-3">{PRODUCTS.map((product, i) => <motion.button key={product} initial={{ y: 28, opacity: 0 }} animate={{ y: 0, opacity: 1 }} transition={{ delay: i * 0.09 }} onClick={() => handleProductSelect(product, floatingChips[0])} whileTap={{ scale: 0.96 }} className="py-3 px-4 rounded-[14px] text-left font-['Pretendard:Medium',sans-serif] text-[13px] text-[#333]" style={{ background: "rgba(255,255,255,0.75)", border: "1px solid rgba(255,255,255,0.9)", boxShadow: "0 3px 10px rgba(0,0,0,0.06)" }}>{product}</motion.button>)}</div>}

          {uiPhase === "selecting-type" && selectingTypes && <div className="grid grid-cols-2 gap-2 mb-3">{getProductTypes(selectedProduct).map((type, i) => <motion.button key={type} initial={{ y: 28, opacity: 0 }} animate={{ y: 0, opacity: 1 }} transition={{ delay: i * 0.09 }} onClick={() => handleTypeSelect(type, floatingChips[0], floatingChips[1])} whileTap={{ scale: 0.96 }} className="py-3 px-4 rounded-[14px] text-left font-['Pretendard:Medium',sans-serif] text-[13px] text-[#333]" style={{ background: "rgba(255,255,255,0.75)", border: "1px solid rgba(255,255,255,0.9)", boxShadow: "0 3px 10px rgba(0,0,0,0.06)" }}>{type}</motion.button>)}</div>}

          {uiPhase === "pending-start" && <motion.button initial={{ y: 12, opacity: 0, scale: 0.96 }} animate={{ y: 0, opacity: 1, scale: 1 }} onClick={handleStartChat} whileTap={{ scale: 0.97 }} className="w-full py-[15px] mt-[15px] rounded-[28px] font-['Pretendard:SemiBold',sans-serif] text-[15px] text-white" style={{ background: "linear-gradient(135deg, #9b8ef6 0%, #6b8ef6 100%)", boxShadow: "0 6px 24px rgba(155,142,246,0.38), inset 0 1px 0 rgba(255,255,255,0.25)" }}>Start chat?</motion.button>}
        </div>
      </motion.div>

      {shouldRenderChatLayer && (
      <motion.div
        className="absolute inset-0 flex flex-col"
        initial={isResumedChatEntry ? false : { y: "12%", opacity: 0, scale: 0.96, filter: "blur(10px)" }}
        animate={{ y: 0, opacity: 1, scale: 1, filter: "blur(0px)" }}
        transition={chatLayerTransition}
        style={{ pointerEvents: "auto" }}
      >
      {/* Chat header */}
      <div
        className="px-[20px] pt-[44px] pb-2 flex items-center gap-3"
        style={{ borderBottom: "none" }}
      >
        <button onClick={handleBack} className="p-1 -ml-1 flex-shrink-0">
          <ChevronLeft size={22} className="text-[#555]" strokeWidth={2} />
        </button>
        <motion.div
          animate={{ y: [0, -6, 0] }}
          transition={{ y: { duration: 3.5, repeat: Infinity, ease: "easeInOut" } }}
          style={{ flexShrink: 0 }}
        >
          <div
            style={{
              position: "relative",
              width: 44,
              height: 44,
              borderRadius: "50%",
              overflow: "hidden",
              clipPath: "circle(50% at 50% 50%)",
              background: "radial-gradient(circle at 40% 35%, #d4f7d4, #c8f0f8, #e8d8f8, #f8d8ec)",
              boxShadow: "0 0 14px 4px rgba(180,240,200,0.45)",
              isolation: "isolate",
            }}
          >
            <img
              src={lgGif}
              alt="LG AI"
              style={{
                position: "absolute",
                inset: 0,
                width: "100%",
                height: "100%",
                objectFit: "contain",
                filter: "url(#remove-white)",
              }}
            />
          </div>
        </motion.div>
        <div>
          <p className="font-['Pretendard:SemiBold',sans-serif] text-[16px] text-[#222] leading-tight">
            LG Chat
          </p>
          <p className="font-['Pretendard:Regular',sans-serif] text-[11px] text-[#5db88a]">
            Online - Support ready
          </p>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-[20px] py-4 space-y-4 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        {messages.map((message, index) => (
          <div key={message.id} className="space-y-1" ref={message.problemOptions ? problemMsgRef : undefined}>
            {message.type === "bot" ? (
              <>
                <div className="flex justify-start gap-2 items-end">
                  <div
                    className="w-7 h-7 rounded-full flex-shrink-0 overflow-hidden relative"
                    style={{
                      background: "radial-gradient(circle, #d4f7d4, #e8d8f8)",
                      boxShadow: "0 2px 8px rgba(180,240,200,0.4)",
                      isolation: "isolate",
                    }}
                  >
                    <img src={lgGif} alt="" style={{ width: "100%", height: "100%", objectFit: "contain", filter: "url(#remove-white)" }} />
                  </div>
                  <div className="rounded-[18px] rounded-bl-[6px] px-[15px] py-[11px] max-w-[270px] shadow-sm" style={chatGlassSurface}>
                    <p className="font-['Pretendard:Medium',sans-serif] text-[14px] text-[#222] whitespace-pre-line leading-[20px] tracking-[-0.2px]">
                      {message.content}
                    </p>
                  </div>
                </div>
                <p className="font-['Inter:Regular',sans-serif] text-[10px] text-[#999] pl-9 mt-0.5">
                  {message.time}
                </p>

                {/* Option buttons */}
                {message.options && (
                  <div className="flex flex-wrap gap-2 mt-3 pl-9">
                    {message.options.map((option, idx) => (
                      <button
                        key={idx}
                        onClick={() => handleOptionClick(option)}
                        className="rounded-[12px] py-[9px] px-[14px] font-['Pretendard:SemiBold',sans-serif] text-[13px] text-[#444] transition-all"
                        style={chatGlassSurface}
                      >
                        {option}
                      </button>
                    ))}
                  </div>
                )}

                {/* Problem option buttons */}
                {message.problemOptions && (
                  <div className="flex flex-col gap-2 mt-3 pl-9">
                    {message.problemOptions.map((option, idx) => (
                      <button
                        key={idx}
                        onClick={() => handleOptionClick(option)}
                        className="rounded-[10px] py-[10px] px-[14px] text-left font-['Pretendard:Medium',sans-serif] text-[13px] leading-snug text-[#444] w-[230px]"
                        style={chatGlassSurface}
                      >
                        {option}
                      </button>
                    ))}
                  </div>
                )}

                {/* Safety notice */}
                {message.cardPolicy?.card_type === "safety_block" && (
                  <div className="mt-3 pl-9 max-w-[290px]">
                    <div className="rounded-[15px] px-4 py-3 w-full" style={{ ...chatSoftCard, border: "1px solid rgba(155,142,246,0.25)" }}>
                      <p className="font-['Pretendard:SemiBold',sans-serif] text-[13px] text-[#8b80e8] mb-1">
                        {message.cardPolicy.title || "Official Source Not Available"}
                      </p>
                      <p className="font-['Pretendard:Regular',sans-serif] text-[12px] text-[#444] leading-[18px]">
                        {message.cardPolicy.description || "AR self-guidance will not start because an official source could not be verified."}
                      </p>
                    </div>
                  </div>
                )}

                {/* Guide buttons */}
                {message.guideButtons && (
                  <div className="flex gap-2 mt-3 pl-9 max-w-[290px]">
                    {message.guideButtons.includes("manual") && (
                      <button
                        onClick={() => {
                          if (message.guideOptions) {
                            setExpandedManualGuideIds((prev) => (prev.includes(message.id) ? prev : [...prev, message.id]));
                            setProblemFocusSpacer(false);
                            setTimeout(scrollToBottom, 80);
                            return;
                          }
                          handleOptionClick("Manual Guide");
                        }}
                        className="flex-1 rounded-[12px] py-[10px] px-[16px] font-['Pretendard:SemiBold',sans-serif] text-[13px] text-[#444] transition-all"
                        style={chatGlassSurface}
                      >
                        Manual Guide
                      </button>
                    )}
                    {message.guideButtons.includes("ar") && (
                      <button
                        onClick={() => handleArGuideClick(message)}
                        className="flex-1 rounded-[12px] py-[10px] px-[16px] font-['Pretendard:SemiBold',sans-serif] text-[13px] text-[#444] transition-all"
                        style={chatGlassSurface}
                      >
                        AR Guide
                      </button>
                    )}
                    {message.guideButtons.includes("service") && (
                      <button
                        onClick={() => handleOptionClick("Connect to Service Center")}
                        className="flex-1 rounded-[12px] py-[10px] px-[16px] font-['Pretendard:SemiBold',sans-serif] text-[13px] text-[#444] transition-all"
                        style={chatGlassSurface}
                      >
                        Connect to Service Center
                      </button>
                    )}
                  </div>
                )}

                {/* Official guide content */}
                {message.guideOptions && expandedManualGuideIds.includes(message.id) && (
                  <div className="mt-3 ml-9 w-[calc(100%-2.25rem)] max-w-[290px] space-y-2">
                    {(() => {
                      const video = guideVideo(message.guideOptions);
                      const manual = message.guideOptions.manual_guides?.[0];
                      const procedureType = message.guideOptions.procedure_type;
                      const procedureLabel = getProcedureLabel(procedureType);
                      const steps = extractGuideSteps(manual, procedureType);
                      return (
                        <div className="w-full rounded-[16px] px-4 py-3" style={chatSoftCard}>
                          {(video.embedUrl || video.videoUrl) && (
                            <>
                              <div className="mb-2">
                                <p className="flex flex-wrap items-baseline gap-[5px]">
                                  <span className="font-['Pretendard:SemiBold',sans-serif] text-[13px] text-[#555]">Official Video Guide</span>
                                  <span className="font-['Pretendard:Medium',sans-serif] text-[11px] text-[#aaa]">·</span>
                                  <span className="font-['Pretendard:Medium',sans-serif] text-[11px] text-[#888]">{procedureLabel}</span>
                                </p>
                              </div>
                              <div
                                className="relative mb-3 flex aspect-video w-full items-center justify-center overflow-hidden rounded-[14px]"
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
                                ) : (
                                  <video controls className="w-full h-full object-cover" src={video.videoUrl || undefined} controlsList="nodownload">
                                    Your browser does not support the video tag.
                                  </video>
                                )}
                              </div>
                            </>
                          )}
                          <div className="flex items-center justify-between gap-2 mb-2">
                            <p className="font-['Pretendard:SemiBold',sans-serif] text-[13px] text-black">📋 {procedureLabel} Steps</p>
                            <span className="font-['Pretendard:Medium',sans-serif] text-[9px] text-[#2d9b69] bg-[#eaf8f1] rounded-full px-2 py-[2px] whitespace-nowrap">
                              LG official standard
                            </span>
                          </div>
                          {steps.map((step, i) => (
                            <p key={i} className="font-['Pretendard:Regular',sans-serif] text-[12px] text-[#444] leading-[18px]">
                              {`${i + 1}. ${step}`}
                            </p>
                          ))}
                        </div>
                      );
                    })()}
                  </div>
                )}

                {/* Video and manual */}
                {message.showVideo && (
                  <div className="mt-3 ml-9 w-[calc(100%-2.25rem)] max-w-[290px] space-y-2">
                    <div className="w-full rounded-[16px] px-4 py-3" style={chatSoftCard}>
                      <div className="mb-2">
                        <p className="flex flex-wrap items-baseline gap-[5px]">
                          <span className="font-['Pretendard:SemiBold',sans-serif] text-[13px] text-[#555]">Official Video Guide</span>
                          <span className="font-['Pretendard:Medium',sans-serif] text-[11px] text-[#aaa]">·</span>
                          <span className="font-['Pretendard:Medium',sans-serif] text-[11px] text-[#888]">Filter Cleaning</span>
                        </p>
                      </div>
                      <div
                        className="relative mb-3 flex aspect-video w-full items-center justify-center overflow-hidden rounded-[14px]"
                        style={{
                          background: "rgba(255,255,255,0.52)",
                          border: "1px solid rgba(255,255,255,0.80)",
                          boxShadow: "inset 0 1px 0 rgba(255,255,255,0.9), 0 4px 18px rgba(31,69,61,0.06)",
                        }}
                      >
                        <video controls className="w-full h-full object-cover" src={aiAlertVideo} controlsList="nodownload">
                          Your browser does not support the video tag.
                        </video>
                      </div>
                      <p className="font-['Pretendard:SemiBold',sans-serif] text-[13px] text-black mb-2">📋 Filter Cleaning Steps</p>
                      {["1. Turn off the power and unplug the unit.", "2. Slowly lift the filter cover.", "3. Release the lock and remove the filter.", "4. Rinse under running water, then dry in the shade.", "5. Reinstall the filter and close the cover."].map((step, i) => (
                        <p key={i} className="font-['Pretendard:Regular',sans-serif] text-[12px] text-[#444] leading-[18px]">{step}</p>
                      ))}
                    </div>
                  </div>
                )}

                {/* Done confirmation */}
                {(message.showDoneAsk || (message.guideOptions && expandedManualGuideIds.includes(message.id))) && index === messages.length - 1 && (
                  <div className="mt-3 ml-9 w-[calc(100%-2.25rem)] max-w-[290px]">
                    <div className="w-full rounded-[15px] px-4 py-4" style={chatSoftCard}>
                      <p className="font-['Pretendard:SemiBold',sans-serif] text-[14px] text-black mb-3">Did you complete the care task?</p>
                      <div className="flex gap-2">
                        <button onClick={() => handleOptionClick("Completed")}
                          className="flex-1 text-white rounded-[10px] py-2.5 font-['Pretendard:SemiBold',sans-serif] text-[13px]"
                          style={chatAccentSurface}>
                          Completed
                        </button>
                        <button onClick={() => handleOptionClick("Still not resolved")}
                          className="flex-1 rounded-[10px] py-2.5 font-['Pretendard:SemiBold',sans-serif] text-[13px] text-[#8b80e8]"
                          style={{ ...chatGlassSurface, border: "1px solid rgba(155,142,246,0.4)" }}>
                          Not resolved
                        </button>
                      </div>
                    </div>
                  </div>
                )}

                {/* Model selection buttons */}
                {message.modelOptions && (
                  <div className="flex flex-col gap-2 mt-3 pl-9">
                    {message.modelOptions.map((device) => (
                      <button
                        key={device.id}
                        onClick={() => handleModelSelect(device)}
                        className="rounded-[12px] px-[14px] py-[10px] text-left transition-all w-[240px]"
                        style={chatGlassSurface}
                      >
                        <p className="font-['Pretendard:SemiBold',sans-serif] text-[13px] text-[#8b80e8]">{device.name}</p>
                        <p className="font-['Pretendard:Regular',sans-serif] text-[11px] text-[#888] mt-[2px]">{device.model}</p>
                      </button>
                    ))}
                  </div>
                )}

                {/* Service summary */}
                {message.showServiceSummary && (
                  <div className="mt-2 pl-9">
                    <div className="rounded-[15px] px-4 py-3 w-[220px]" style={chatSoftCard}>
                      <p className="font-['Pretendard:SemiBold',sans-serif] text-[11px] text-[#8b80e8] mb-2">📋 Confirm Request Information</p>
                      {[
                        ["Product", message.showServiceSummary.product],
                        ["Name", message.showServiceSummary.name],
                        ["Phone", message.showServiceSummary.phone],
                        ["Address", message.showServiceSummary.address],
                        ["Model", message.showServiceSummary.model],
                        ["Issue", message.showServiceSummary.issue],
                      ].map(([label, value]) => (
                        <div key={label} className="flex gap-2 mb-1">
                          <span className="font-['Pretendard:SemiBold',sans-serif] text-[9px] text-[#888] w-[42px] shrink-0">{label}</span>
                          <span className="font-['Pretendard:Regular',sans-serif] text-[9px] text-[#333] leading-tight">{value}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Schedule selection */}
                {message.showSchedule && index === messages.length - 1 && (
                  <div className="mt-3 pl-9">
                    <div className="rounded-[15px] px-4 py-3 w-[240px]" style={chatSoftCard}>
                      <p className="font-['Pretendard:SemiBold',sans-serif] text-[11px] text-black mb-2">📅 Select Visit Date</p>
                      <div className="flex flex-wrap gap-1 mb-3">
                        {AVAILABLE_DATES.map((d) => (
                          <button key={d.value}
                            onClick={() => setSelectedDate(d.value)}
                            className={`px-2 py-1 rounded-[6px] text-[9px] font-['Pretendard:Medium',sans-serif] transition-colors ${
                              selectedDate === d.value
                                ? "bg-[#9b8ef6] text-white"
                                : "bg-[#f5f5f5] text-[#444]"
                            }`}>
                            {d.label}
                          </button>
                        ))}
                      </div>
                      {selectedDate && (
                        <>
                          <p className="font-['Pretendard:SemiBold',sans-serif] text-[11px] text-black mb-2">⏰ Select Visit Time</p>
                          <div className="flex flex-col gap-1">
                            {TIME_SLOTS.map((t) => (
                              <button key={t}
                                onClick={() => handleScheduleConfirm(t)}
                                className="w-full bg-white/70 border border-[#b8aff8] text-[#8b80e8] rounded-[8px] py-1.5 font-['Pretendard:Medium',sans-serif] text-[10px] hover:bg-[#f4f1ff] transition-colors">
                                {t}
                              </button>
                            ))}
                          </div>
                        </>
                      )}
                    </div>
                  </div>
                )}

                {/* Service Request Completed */}
                {message.showServiceComplete && (
                  <div className="mt-2 pl-9">
                    <div className="rounded-[15px] px-4 py-3 w-[220px] text-center" style={chatSoftCard}>
                      <p className="text-[28px] mb-1">🎉</p>
                      <p className="font-['Pretendard:Bold',sans-serif] text-[12px] text-[#8b80e8]">Service Request Completed</p>
                      <p className="font-['Pretendard:Regular',sans-serif] text-[9px] text-[#888] mt-1">Confirmation call scheduled for the day before the visit</p>
                    </div>
                  </div>
                )}
              </>
            ) : (
              <>
                <div className="flex justify-end">
                  <div className="rounded-[18px] rounded-br-[6px] px-[15px] py-[11px] max-w-[270px]" style={chatAccentSurface}>
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
        {problemFocusSpacer && <div className="h-[390px] shrink-0" aria-hidden="true" />}
        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <div className="px-[18px] pb-5 pt-2">
        <div
          className="flex items-center gap-2 rounded-[28px] px-4 py-3"
          style={{
            background: "rgba(255,255,255,0.75)",
            backdropFilter: "blur(20px)",
            WebkitBackdropFilter: "blur(20px)",
            border: "1px solid rgba(255,255,255,0.9)",
            boxShadow: "0 4px 20px rgba(0,0,0,0.07)",
          }}
        >
          <button className="text-[#bbb] flex-shrink-0">
            <Paperclip size={17} strokeWidth={1.5} />
          </button>
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={(e) => e.key === "Enter" && handleSendMessage()}
            placeholder="Enter a message..."
            className="flex-1 bg-transparent outline-none font-['Pretendard:Regular',sans-serif] text-[13px] text-black placeholder:text-[#aaa]"
          />
          <button
            onClick={handleSendMessage}
            className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0"
            style={{ background: "linear-gradient(135deg, #9b8ef6, #6b8ef6)" }}
          >
            <Send size={14} className="text-white" strokeWidth={2} />
          </button>
        </div>
      </div>
      </motion.div>
      )}
    </motion.div>
  );
}

