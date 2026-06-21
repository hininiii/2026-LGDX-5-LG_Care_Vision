import { useState, useEffect } from "react";
import { useNavigate } from "react-router";
import { ChevronLeft, Check } from "lucide-react";

const LANGUAGES = [
  { code: "en", name: "English", native: "English" },
  { code: "ko", name: "Korean", native: "한국어" },
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

export function LanguageSettings() {
  const navigate = useNavigate();
  const [selected, setSelected] = useState<string>("ko");

  useEffect(() => {
    const saved = localStorage.getItem("appLanguage");
    if (saved) setSelected(saved);
  }, []);

  const handleSave = () => {
    localStorage.setItem("appLanguage", selected);
    navigate("/settings");
  };

  return (
    <div className="relative min-h-full w-full bg-[#f7f9f8]">
      <div className="pointer-events-none absolute -top-20 -left-16 w-72 h-72 rounded-full"
        style={{ background: "rgba(61,220,151,0.09)", filter: "blur(90px)" }} />

      <div className="relative z-10 px-[18px] pt-[40px] pb-[20px] w-full max-w-[390px] mx-auto">
        <div className="flex items-center gap-1 mb-5 -mx-[2px]">
          <button onClick={() => navigate("/settings")} className="p-1">
            <ChevronLeft size={22} className="text-[#555]" />
          </button>
          <p className="font-['Pretendard:Medium',sans-serif] text-[20px] tracking-[-0.3px] text-black leading-[15px]">
            Language Settings
          </p>
        </div>

        <p className="font-['Pretendard:Regular',sans-serif] text-[13px] text-[#888] mb-4 px-1">
          The UI, manual/AR guide, and voice guidance will be provided in the selected language.
        </p>

        <div className="rounded-[20px] overflow-hidden mb-4" style={glass}>
          {LANGUAGES.map((lang, idx) => {
            const isSelected = selected === lang.code;
            return (
            <div key={lang.code}>
              <button
                onClick={() => setSelected(lang.code)}
                className="w-full px-5 py-4 flex items-center justify-between hover:bg-white/30 transition-colors"
              >
                <div className="text-left">
                  <p className={`${isSelected ? "font-['Pretendard:SemiBold',sans-serif] text-[16px] text-[#111]" : "font-['Pretendard:Regular',sans-serif] text-[15px] text-[#111]"} mb-[2px] transition-all duration-200`}>{lang.native}</p>
                  <p className={`${isSelected ? "font-['Pretendard:Regular',sans-serif] text-[12px] text-[#888]" : "font-['Pretendard:Regular',sans-serif] text-[12px] text-[#888]"} transition-all duration-200`}>{lang.name}</p>
                </div>
                {isSelected && <Check size={20} className="text-[#1DB87A]" />}
              </button>
              {idx < LANGUAGES.length - 1 && (
                <div className="h-[1px] mx-5" style={{ background: "rgba(200,200,200,0.3)" }} />
              )}
            </div>
            );
          })}
        </div>

        <button
          onClick={handleSave}
          className="w-full text-white rounded-[15px] py-4 font-['Pretendard:Medium',sans-serif] text-[14px]"
          style={{
            background: "linear-gradient(135deg, #1DB87A 0%, #3DDC97 100%)",
            boxShadow: "0 6px 22px rgba(29,184,122,0.28), inset 0 1px 0 rgba(255,255,255,0.28)",
          }}
        >
          Save
        </button>
      </div>
    </div>
  );
}
