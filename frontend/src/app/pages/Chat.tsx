import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router";
import { ChevronLeft, Send, Paperclip } from "lucide-react";
import aiAlertVideo from "../../imports/AS-Q24ENXE_filter_cleaning_MVP_hyperframes.mp4";
import {
  getAllProductTypes,
  getAvailableDates,
  getInitialChatMessages,
  getProblemOptions,
  getProductCategories,
  getProductTypes,
  getTimeSlots,
} from "../api/chat";
import { getRegisteredDevices } from "../api/devices";
import { getUserProfile } from "../api/user";
import type { ChatContext, FlowType, Message, ServiceInfo, ServiceStep } from "../types/chat";
import type { ChatDeviceOption } from "../types/device";

const LEGACY_CHAT_STORAGE_KEYS = ["chat_messages"];
const CHAT_STORAGE_KEY = "chat_messages_v20260612";
const CHAT_ENDED_KEY = "chat_session_ended";

const now = () =>
  new Date().toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit" });

const PRODUCTS = getProductCategories();
const AVAILABLE_DATES = getAvailableDates();
const TIME_SLOTS = getTimeSlots();

export function Chat() {
  const navigate = useNavigate();
  const messagesEndRef = useRef<HTMLDivElement>(null);

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

  const handleSendMessage = () => {
    if (!inputValue.trim()) return;
    const text = inputValue.trim();
    setInputValue("");
    addUserMessage(text);

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

    // 일반 키워드 감지
    if (text.includes("필터") && text.includes("먼지")) {
      setChatContext((prev) => ({
        ...prev,
        symptom: text,
        recommendedActions: ["manual", "ar"],
      }));
      addBotMessage("🔍 증상을 분석한 결과 셀프 케어로 해결 가능한 문제입니다.\n원하시는 가이드를 선택해주세요.", {
        guideButtons: ["manual", "ar"],
      });
    } else {
      addBotMessage("감사합니다. 문의사항을 확인하고 있습니다.");
    }
  };

  const handleOptionClick = (option: string) => {
    addUserMessage(option);

    setTimeout(async () => {
      // ── 최상위 메뉴 ──
      if (option === "제품 문제 해결") {
        setFlow("trouble");
        setChatContext({ intent: "trouble" });
        setMessages((prev) => [...prev, { id: (Date.now() + 1).toString(), type: "bot", content: "어떤 제품에 문제가 생겼나요?", time: now(), options: PRODUCTS }]);
        return;
      }
      if (option === "가전 관리 방법") {
        setFlow("care");
        setChatContext({ intent: "care" });
        setMessages((prev) => [...prev, { id: (Date.now() + 1).toString(), type: "bot", content: "관리 방법이 필요한 제품을 선택해주세요.", time: now(), options: PRODUCTS }]);
        return;
      }
      if (option === "서비스 센터 연결") {
        setFlow("service");
        setChatContext({ intent: "service" });
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
      if (option === "필터에 먼지가 많이 쌓여 있어요") {
        setChatContext((prev) => ({
          ...prev,
          symptom: option,
          recommendedActions: ["manual", "ar"],
        }));
        setMessages((prev) => [...prev, {
          id: (Date.now() + 1).toString(), type: "bot",
          content: "🔍 셀프 케어로 해결 가능한 문제예요!\n원하시는 가이드를 선택해주세요.",
          time: now(),
          guideButtons: ["manual", "ar"],
        }]);
        return;
      }
      if (["전원이 불안정하거나 자주 꺼져요", "냉방/기능이 잘 작동하지 않아요", "소음이나 진동이 심해요"].includes(option)) {
        setChatContext((prev) => ({
          ...prev,
          symptom: option,
          recommendedActions: ["video", "manual", "ar", "service"],
        }));
        setMessages((prev) => [...prev, {
          id: (Date.now() + 1).toString(), type: "bot",
          content: "🔍 증상을 분석했어요.\n먼저 영상 가이드로 확인해보시고, 해결되지 않으면 서비스 센터를 연결해드릴게요.",
          time: now(),
          showVideo: true,
          guideButtons: ["manual", "ar"],
        }]);
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
      className="h-full flex flex-col w-full"
      style={{
        backgroundImage:
          "linear-gradient(rgba(192, 255, 218, 0.2) 0%, rgba(255, 141, 27, 0.2) 100%), linear-gradient(90deg, rgb(255, 255, 255) 0%, rgb(255, 255, 255) 100%)",
      }}
    >
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
          <div key={message.id} className="space-y-1">
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

                {/* 가이드 버튼 */}
                {message.guideButtons && (
                  <div className="flex gap-2 mt-3 pl-1">
                    {message.guideButtons.includes("manual") && (
                      <button
                        onClick={() => handleOptionClick("매뉴얼 가이드")}
                        className="bg-[#ff4c49] text-white rounded-[12px] py-[10px] px-[16px] font-['Pretendard:SemiBold',sans-serif] text-[13px] hover:bg-[#e63d3a] transition-colors shadow-sm"
                      >
                        매뉴얼 가이드
                      </button>
                    )}
                    {message.guideButtons.includes("ar") && (
                      <button
                        onClick={() => navigate("/ar-guide", { state: { from: "/chat" } })}
                        className="bg-white border border-[#ff4c49] text-[#ff4c49] rounded-[12px] py-[10px] px-[16px] font-['Pretendard:SemiBold',sans-serif] text-[13px] hover:bg-[#fff5f5] transition-colors shadow-sm"
                      >
                        AR 가이드
                      </button>
                    )}
                  </div>
                )}

                {/* 비디오 + 매뉴얼 */}
                {message.showVideo && (
                  <div className="mt-3 pl-1 space-y-2">
                    <div className="bg-gray-900 h-[120px] w-[240px] rounded-[15px] overflow-hidden shadow-sm">
                      <video controls className="w-full h-full object-cover" src={aiAlertVideo} controlsList="nodownload">
                        브라우저가 비디오 태그를 지원하지 않습니다.
                      </video>
                    </div>
                    <div className="bg-white rounded-[15px] px-4 py-3 w-[240px] shadow-sm border border-[#f0f0f0]">
                      <p className="font-['Pretendard:SemiBold',sans-serif] text-[13px] text-black mb-2">📋 필터 청소 순서</p>
                      {["① 전원을 끄고 플러그를 뽑으세요.", "② 필터 커버를 천천히 들어 올리세요.", "③ 잠금을 풀고 필터를 분리하세요.", "④ 흐르는 물로 헹군 후 그늘에 말리세요.", "⑤ 필터를 재장착하고 커버를 닫으세요."].map((step, i) => (
                        <p key={i} className="font-['Pretendard:Regular',sans-serif] text-[12px] text-[#444] leading-[18px]">{step}</p>
                      ))}
                    </div>
                  </div>
                )}

                {/* 완료 확인 버튼 */}
                {message.showDoneAsk && index === messages.length - 1 && (
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
    </div>
  );
}
