import { useNavigate, useLocation } from "react-router";
import { useState, useRef, useEffect } from "react";
import { ChevronLeft, Camera, Volume2, VolumeX, Lightbulb, Check } from "lucide-react";
import { motion, AnimatePresence } from "motion/react";
import arTitleLogo from "../../imports/ar-title.svg";

const CHAT_STORAGE_KEY = "chat_messages_v20260618_transition_v2";

const steps = [
  { title: "Turn Off Power", desc: "Turn off the power and unplug the unit.", hint: "Press and hold the air conditioner power button\nor unplug it directly." },
  { title: "Open Cover", desc: "Slowly lift the filter cover.", hint: "Hold both sides of the filter cover\nand slowly lift it upward." },
  { title: "Remove Filter", desc: "Release both locks and remove the filter.", hint: "Press the lock tabs on both sides of the filter\nand pull it downward." },
  { title: "Wash and Dry", desc: "Rinse under running water, then dry in the shade.", hint: "Rinse only with lukewarm running water\nwithout detergent." },
  { title: "Reinstall", desc: "Reinstall the filter and close the cover.", hint: "After inserting the filter, press the cover\nuntil it clicks." },
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
        content: "Did you finish the AR guide?\nI'll record the care details.",
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
          <button onClick={goBack} className="-ml-1 flex h-9 w-9 items-center justify-start" aria-label="Go back">
            <ChevronLeft size={32} strokeWidth={1.9} className="text-[#35383B]" />
          </button>
          <h1 className="flex h-[24px] items-center justify-center" aria-label="AR">
            <img src={arTitleLogo} alt="" className="h-[17px] w-[30px]" />
          </h1>
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
              <button
                onClick={() => setSoundOn(!soundOn)}
                className="absolute right-[12px] top-[22px] z-10 flex h-10 w-10 items-center justify-center rounded-full backdrop-blur-sm"
                style={{
                  background: "rgba(255,255,255,0.86)",
                }}
                aria-label="Voice guidance"
              >
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

            <div className="relative mt-[12px] flex flex-1 min-h-[160px] overflow-hidden rounded-[15px] border-[1.5px] border-[#22C59A]/40 bg-white/20">
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
                  <p className="mt-[16px] text-[15px] font-medium tracking-[-0.055em] text-white/80">Camera permission is required</p>
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
                <strong className="text-[13px] font-semibold tracking-[-0.06em] text-[#20AD86]">Try this</strong>
              </div>
              <div className="grid pl-[20px] pr-[0px] py-[0px]">
                {steps.map((step) => (
                  <p
                    key={step.title}
                    aria-hidden="true"
                    className="invisible col-start-1 row-start-1 whitespace-pre-line text-[13px] font-medium leading-[1.45] tracking-[-0.06em] text-[#55595D]"
                  >
                    {step.hint}
                  </p>
                ))}
                <p className="col-start-1 row-start-1 whitespace-pre-line text-[13px] font-medium leading-[1.45] tracking-[-0.06em] text-[#55595D]">{steps[current].hint}</p>
              </div>
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
            >Previous</motion.button>
            <motion.button
              onClick={handleNext}
              whileTap={{ scale: 0.95 }}
              transition={{ type: "spring", stiffness: 400, damping: 22 }}
              className="h-[48px] flex-1 rounded-[12px] text-[15px] font-bold tracking-[-0.04em] text-white"
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
        <>
        </>
      )}
    </div>
  );
}

function Corner({ className }: { className: string }) {
  return <span className={`absolute h-[24px] w-[24px] rounded-tl-[5px] border-l-2 border-t-2 border-[#22B98F] ${className}`} />;
}


