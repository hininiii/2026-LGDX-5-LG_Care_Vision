import { useNavigate, useLocation } from "react-router";
import { useState, useRef, useEffect } from "react";
import { ChevronLeft, Camera, Volume2, VolumeX, Lightbulb, Check } from "lucide-react";
import { motion, AnimatePresence } from "motion/react";

const CHAT_STORAGE_KEY = "chat_messages_v20260612";

const steps = [
  { title: "전원 차단", desc: "전원을 끄고 플러그를 뽑으세요.", hint: "에어컨 전원 버튼을 길게 누르거나\n플러그를 직접 뽑아주세요." },
  { title: "커버 열기", desc: "필터 커버를 천천히 들어 올리세요.", hint: "필터 커버의 양쪽을 잡고\n천천히 위로 들어 올려주세요." },
  { title: "필터 분리", desc: "양쪽 잠금을 풀고 필터를 분리하세요.", hint: "필터 양쪽의 잠금 탭을 누른 상태로\n아래로 당겨주세요." },
  { title: "세척 및 건조", desc: "흐르는 물로 헹군 후 그늘에 말리세요.", hint: "세제 없이 흐르는 미지근한 물로만\n헹궈주세요." },
  { title: "재장착", desc: "필터를 다시 끼우고 커버를 닫으세요.", hint: "필터를 끼운 후 딸깍 소리가 날 때까지\n커버를 눌러주세요." },
];

export function ARGuide() {
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: string } | null)?.from ?? "/self-care";
  const [current, setCurrent] = useState(0);
  const [soundOn, setSoundOn] = useState(true);
  const videoRef = useRef<HTMLVideoElement>(null);
  const [camError, setCamError] = useState(false);

  useEffect(() => {
    let stream: MediaStream;
    navigator.mediaDevices?.getUserMedia({ video: { facingMode: "environment" } })
      .then((s) => {
        stream = s;
        if (videoRef.current) {
          videoRef.current.srcObject = s;
        }
      })
      .catch(() => setCamError(true));
    return () => { stream?.getTracks().forEach((t) => t.stop()); };
  }, []);

  const goBack = () => navigate(from);
  const handlePrev = () => {
    if (current > 0) setCurrent(current - 1);
  };
  const handleNext = () => {
    if (current < steps.length - 1) {
      setCurrent(current + 1);
      return;
    }
    if (from === "/chat") {
      const saved = localStorage.getItem(CHAT_STORAGE_KEY);
      const messages = saved ? JSON.parse(saved) : [];
      const doneMsg = {
        id: Date.now().toString(),
        type: "bot",
        content: "AR 가이드를 완료하셨나요?\n관리 내용을 기록해드릴게요.",
        time: new Date().toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit" }),
        showDoneAsk: true,
      };
      localStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify([...messages, doneMsg]));
      navigate("/chat");
      return;
    }
    navigate("/self-care", { state: { tab: "ar" } });
  };

  return (
    <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -14 }}
        transition={{ duration: 0.48, ease: [0.22, 1, 0.36, 1] }}
        className="relative flex h-full w-full flex-col overflow-hidden text-[#292B2E]" style={{ background: "linear-gradient(160deg, #d6f2e8 0%, #f0f8e8 30%, #fce8f0 65%, #ede8f8 100%)" }}>
        <header className="flex shrink-0 items-center justify-between px-[24px] pb-[24px] pt-[44px]">
          <button onClick={goBack} className="-ml-1 flex h-9 w-9 items-center justify-start" aria-label="뒤로가기">
            <ChevronLeft size={32} strokeWidth={1.9} className="text-[#35383B]" />
          </button>
          <h1 className="text-[23px] font-semibold leading-none tracking-[-0.025em]">AR</h1>
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
                    : <span className={`text-[11px] font-bold tracking-[-0.02em] ${isActive ? "text-white" : "text-[#B0B4B2]"}`}>{idx + 1}</span>
                  }
                </motion.button>
              </div>
            );
          })}
        </nav>

        <main className="flex min-h-0 flex-1 flex-col gap-[12px] overflow-y-auto px-[12px] pb-[10px] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
          <section className="relative flex flex-1 flex-col rounded-[18px] px-[14px] pb-[14px] pt-[14px]" style={{ background: "rgba(255,255,255,0.55)", backdropFilter: "blur(24px)", WebkitBackdropFilter: "blur(24px)", border: "1px solid rgba(255,255,255,0.75)", boxShadow: "0 16px 32px rgba(31,69,61,0.08), inset 0 1px 0 rgba(255,255,255,0.9)" }}>
              <button onClick={() => setSoundOn(!soundOn)} className="absolute right-[12px] top-[22px] z-10 flex h-10 w-10 items-center justify-center rounded-full bg-white/70 backdrop-blur-sm" aria-label="음성 안내">
                {soundOn ? <Volume2 size={22} strokeWidth={1.9} className="text-[#35383B]" /> : <VolumeX size={22} strokeWidth={1.9} className="text-[#C7CECC]" />}
              </button>
            <AnimatePresence mode="wait">
            <motion.div
              key={current}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -14 }}
              transition={{ duration: 0.38, ease: [0.22, 1, 0.36, 1] }}
              className="relative shrink-0">
              <span className="inline-flex rounded-[7px] bg-[#E4F5F0] text-[13px] font-medium leading-none tracking-[-0.03em] text-[#20AD86] px-[10px] py-[5px] mx-[10px] my-[0px]">STEP {current + 1} / 5</span>
              <h2 className="text-[22px] font-bold leading-none tracking-[-0.07em] text-[#202124] ml-[10px] mr-[0px] mt-[10px] mb-[0px]">{steps[current].title}</h2>
              <p className="text-[13px] font-medium leading-[1.28] tracking-[-0.055em] text-[#6A6D70] ml-[10px] mr-[0px] mt-[6px] mb-[0px]">{steps[current].desc}</p>
            </motion.div>
            </AnimatePresence>

            <div className="relative mt-[12px] flex flex-1 min-h-[160px] overflow-hidden rounded-[15px] border-[1.5px] border-[#22C59A]/40 bg-black">
              <video ref={videoRef} autoPlay playsInline muted className="h-full w-full object-cover" />
              <Corner className="left-[17px] top-[18px] rotate-0" />
              <Corner className="right-[17px] top-[18px] rotate-90" />
              <Corner className="bottom-[18px] right-[17px] rotate-180" />
              <Corner className="bottom-[18px] left-[17px] -rotate-90" />
              {camError && (
                <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/60">
                  <div className="flex h-[64px] w-[64px] items-center justify-center rounded-full bg-[#ECF5F2]">
                    <Camera size={36} strokeWidth={1.65} className="text-[#718E86]" />
                  </div>
                  <p className="mt-[16px] text-[15px] font-medium tracking-[-0.055em] text-white/80">카메라 권한이 필요합니다</p>
                </div>
              )}
            </div>
          </section>

          <section className="flex shrink-0 min-h-[104px] items-center rounded-[18px] bg-white px-[16px] py-[13px] shadow-[0_14px_32px_rgba(31,69,61,0.075)]">
            <div className="flex h-[78px] w-[98px] shrink-0 items-center justify-center overflow-hidden rounded-[11px] bg-[#F1F8F5]">
              <AirconIllustration className="h-[64px] w-[88px]" arrow />
            </div>
            <div className="mx-[16px] h-[70px] border-l border-dashed border-[#DDE5E2]" />
            <div className="min-w-0 flex-1">
              <div className="mb-[6px] flex items-center gap-[5px]">
                <span className="flex h-[18px] w-[18px] shrink-0 items-center justify-center rounded-full bg-[#DDF3EC] text-[#22B98F]"><Lightbulb size={11} strokeWidth={2} /></span>
                <strong className="text-[13px] font-semibold tracking-[-0.06em] text-[#20AD86]">이렇게 해보세요</strong>
              </div>
              <p className="whitespace-pre-line text-[13px] font-medium leading-[1.45] tracking-[-0.06em] text-[#55595D] pl-[20px] pr-[0px] py-[0px]">{steps[current].hint}</p>
            </div>
          </section>
        </main>

        <footer className="shrink-0 rounded-[16px] px-[8px] py-[8px] mx-[12px] mb-[20px]" style={{ background: "rgba(255,255,255,0.45)", backdropFilter: "blur(20px)", WebkitBackdropFilter: "blur(20px)", border: "1px solid rgba(255,255,255,0.65)", boxShadow: "0 4px 20px rgba(31,69,61,0.08), inset 0 1px 0 rgba(255,255,255,0.8)" }}>
          <div className="flex items-center gap-[8px]">
            <motion.button
              onClick={handlePrev}
              disabled={current === 0}
              whileTap={{ scale: 0.95 }}
              transition={{ type: "spring", stiffness: 400, damping: 22 }}
              className="h-[48px] flex-1 rounded-[12px] text-[15px] font-bold tracking-[-0.04em] transition disabled:opacity-30"
              style={{ background: "rgba(255,255,255,0.7)", border: "1px solid rgba(255,255,255,0.65)", color: "#20B88E", boxShadow: "0 2px 8px rgba(31,69,61,0.06), inset 0 1px 0 rgba(255,255,255,0.9)" }}
            >이전</motion.button>
            <motion.button
              onClick={handleNext}
              whileTap={{ scale: 0.95 }}
              transition={{ type: "spring", stiffness: 400, damping: 22 }}
              className="h-[48px] flex-1 rounded-[12px] text-[15px] font-bold tracking-[-0.04em] text-white"
              style={{ background: "linear-gradient(135deg, #24C99A, #14B989)", boxShadow: "0 4px 14px rgba(34,197,154,0.35), inset 0 1px 0 rgba(255,255,255,0.3)", border: "1px solid rgba(255,255,255,0.3)" }}
            >{current === steps.length - 1 ? "완료" : "다음"}</motion.button>
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
        <>
        </>
      )}
    </div>
  );
}

function Corner({ className }: { className: string }) {
  return <span className={`absolute h-[24px] w-[24px] rounded-tl-[5px] border-l-2 border-t-2 border-[#22B98F] ${className}`} />;
}


