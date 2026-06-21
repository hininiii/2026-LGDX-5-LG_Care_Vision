import { useState } from "react";
import { useNavigate } from "react-router";
import { Check } from "lucide-react";
import careVisionLogo from "../../imports/care-vision-logo.svg";
import careVisionLogoIcon from "../../imports/care_vision_logo_icon.png";

const LANGUAGES = [
  { code: "en", name: "English", native: "English" },
  { code: "ko", name: "Korean", native: "한국어" },
  { code: "hi", name: "Hindi", native: "हिन्दी" },
  { code: "bn", name: "Bengali", native: "বাংলা" },
  { code: "ta", name: "Tamil", native: "தமிழ்" },
  { code: "te", name: "Telugu", native: "తెలుగు" },
];

const airbrushBg = [
  "linear-gradient(160deg, #d6f2e8 0%, #f0f8e8 30%, #fce8f0 65%, #ede8f8 100%)",
].join(", ");

const glass = {
  background: "rgba(255,255,255,0.55)",
  backdropFilter: "blur(24px)",
  WebkitBackdropFilter: "blur(24px)",
  border: "1px solid rgba(255,255,255,0.85)",
  boxShadow: "0 8px 40px rgba(0,0,0,0.08), inset 0 1px 0 rgba(255,255,255,0.95)",
};

const primaryButtonStyle = {
  background: "linear-gradient(135deg, #3DDC97 0%, #14B989 100%)",
  boxShadow: "0 8px 28px rgba(29,184,122,0.32), inset 0 1px 0 rgba(255,255,255,0.25)",
};

export function InitialLanguage() {
  const navigate = useNavigate();
  const [selected, setSelected] = useState("en");

  const handleConfirm = () => {
    localStorage.setItem("appLanguage", selected);
    navigate("/splash");
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-100">
      <div
        className="relative h-screen w-full max-w-[390px] overflow-y-auto"
        style={{ background: airbrushBg }}
      >

        <div className="relative z-10 px-[28px] pt-[64px] pb-[48px]">
          <div className="mb-[40px]">
            <div className="flex items-center gap-3 mb-4">
              <img
                src={careVisionLogoIcon}
                alt="Care Vision"
                className="w-10 h-10 rounded-[12px] object-cover"
                style={{ boxShadow: "0 4px 16px rgba(29,184,122,0.25)" }}
              />
              <img src={careVisionLogo} alt="Care Vision" className="h-[20px] w-[142px]" />
            </div>
            <p className="font-['Pretendard:Regular',sans-serif] text-[15px] text-[#666] leading-[1.5]">
              Please select the language you want to
              <br />
              use for the service.
            </p>
          </div>

          <div className="rounded-[24px] p-4 mb-6" style={glass}>
            <div className="px-1 pt-1 pb-4">
              <p className="font-['Pretendard:SemiBold',sans-serif] text-[16px] text-[#111] mb-2">Language Settings</p>
              <p className="font-['Pretendard:Regular',sans-serif] text-[13px] text-[#888] leading-[1.45]">
                You can change this again from Settings.
              </p>
            </div>
            <div
              className="overflow-hidden rounded-[18px]"
              style={{
                background: "rgba(255,255,255,0.52)",
                border: "1px solid rgba(255,255,255,0.78)",
                boxShadow: "0 4px 18px rgba(0,0,0,0.055), inset 0 1px 0 rgba(255,255,255,0.9)",
              }}
            >
            {LANGUAGES.map((lang, idx) => (
              <div key={lang.code}>
                <button
                  onClick={() => setSelected(lang.code)}
                  className="w-full px-5 py-4 flex items-center justify-between hover:bg-white/30 transition-colors"
                  style={selected === lang.code ? {
                    background: "rgba(255,255,255,0.82)",
                    boxShadow: "inset 0 1px 0 rgba(255,255,255,0.96)",
                  } : undefined}
                >
                  <div className="text-left">
                    <p className={`font-['Pretendard:SemiBold',sans-serif] ${selected === lang.code ? "text-[16px]" : "text-[15px]"} text-[#111] mb-[2px] transition-all`}>
                      {lang.native}
                    </p>
                    <p className="font-['Pretendard:Regular',sans-serif] text-[12px] text-[#888]">
                      {lang.name}
                    </p>
                  </div>
                  {selected === lang.code && (
                    <div
                      className="w-6 h-6 rounded-full flex items-center justify-center"
                      style={{ background: "linear-gradient(135deg, #3DDC97 0%, #14B989 100%)" }}
                    >
                      <Check size={13} color="white" strokeWidth={3} />
                    </div>
                  )}
                </button>
                {idx < LANGUAGES.length - 1 && (
                  <div className="h-[1px] mx-5" style={{ background: "rgba(200,200,200,0.3)" }} />
                )}
              </div>
            ))}
            </div>
          </div>

          <button
            onClick={handleConfirm}
            className="w-full text-white rounded-[20px] py-[16px] font-['Pretendard:Medium',sans-serif] text-[14px] transition-opacity hover:opacity-90"
            style={primaryButtonStyle}
          >
            Get Started
          </button>
        </div>
      </div>
    </div>
  );
}
