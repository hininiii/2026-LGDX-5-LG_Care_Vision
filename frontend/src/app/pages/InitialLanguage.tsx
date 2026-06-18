import { useState } from "react";
import { useNavigate } from "react-router";
import { Check } from "lucide-react";

const LANGUAGES = [
  { code: "ko", name: "Korean", native: "Korean" },
  { code: "en", name: "English", native: "English" },
  { code: "hi", name: "Hindi", native: "हिन्दी" },
  { code: "bn", name: "Bengali", native: "বাংলা" },
  { code: "ta", name: "Tamil", native: "தமிழ்" },
  { code: "te", name: "Telugu", native: "తెలుగు" },
];

const glass = {
  background: "rgba(255,255,255,0.55)",
  backdropFilter: "blur(28px)",
  WebkitBackdropFilter: "blur(28px)",
  border: "1px solid rgba(255,255,255,0.80)",
  boxShadow: "0 8px 32px rgba(0,0,0,0.08), inset 0 1px 0 rgba(255,255,255,0.95)",
};

export function InitialLanguage() {
  const navigate = useNavigate();
  const [selected, setSelected] = useState("ko");

  const handleConfirm = () => {
    localStorage.setItem("appLanguage", selected);
    navigate("/");
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-100">
      <div
        className="relative h-screen w-full max-w-[390px] overflow-y-auto"
        style={{ background: [
          "radial-gradient(ellipse 120% 55% at 50% -5%, rgba(255,190,140,0.22) 0%, transparent 70%)",
          "radial-gradient(ellipse 100% 50% at 50% 110%, rgba(100,220,185,0.18) 0%, transparent 70%)",
          "linear-gradient(180deg, #fffcf9 0%, #ffffff 50%, #f8fffc 100%)",
        ].join(", ") }}
      >

        <div className="relative z-10 px-[24px] pt-[64px] pb-[40px]">
          <p className="font-['Pretendard:SemiBold',sans-serif] text-[30px] text-[#ff4c49] mb-1">Care Shot</p>
          <p className="font-['Pretendard:Medium',sans-serif] text-[14px] text-[#888] mb-8">
            Home Appliance Care Management Service
          </p>

          <p className="font-['Pretendard:SemiBold',sans-serif] text-[24px] text-[#111] mb-2">Language Settings</p>
          <p className="font-['Pretendard:Regular',sans-serif] text-[13px] text-[#888] mb-6">
            Please select the language you want to use for the service.
          </p>

          <div className="rounded-[20px] overflow-hidden mb-6" style={glass}>
            {LANGUAGES.map((lang, idx) => (
              <div key={lang.code}>
                <button
                  onClick={() => setSelected(lang.code)}
                  className="w-full px-5 py-4 flex items-center justify-between hover:bg-white/30 transition-colors"
                >
                  <div className="text-left">
                    <p className="font-['Pretendard:SemiBold',sans-serif] text-[15px] text-[#111] mb-[2px]">
                      {lang.native}
                    </p>
                    <p className="font-['Pretendard:Regular',sans-serif] text-[12px] text-[#888]">
                      {lang.name}
                    </p>
                  </div>
                  {selected === lang.code && <Check size={20} className="text-[#1DB87A]" />}
                </button>
                {idx < LANGUAGES.length - 1 && (
                  <div className="h-[1px] mx-5" style={{ background: "rgba(200,200,200,0.3)" }} />
                )}
              </div>
            ))}
          </div>

          <button
            onClick={handleConfirm}
            className="w-full text-white rounded-[20px] py-[16px] font-['Pretendard:SemiBold',sans-serif] text-[15px] transition-opacity hover:opacity-90"
            style={{
              background: "linear-gradient(135deg, #ff6b35, #ff4c49)",
              boxShadow: "0 8px 24px rgba(255,76,73,0.30)",
            }}
          >
            Get Started
          </button>
        </div>
      </div>
    </div>
  );
}
