import { useState } from "react";
import { useNavigate } from "react-router";
import { Eye, EyeOff } from "lucide-react";
import careVisionLogo from "../../imports/care-vision-logo.svg";
import careVisionLogoIcon from "../../imports/care_vision_logo_icon.png";
import { loginUser } from "../api/user";
import { setCurrentUserEmail } from "../utils/authSession";

const airbrushBg = [
  "linear-gradient(160deg, #d6f2e8 0%, #f0f8e8 30%, #fce8f0 65%, #ede8f8 100%)",
].join(", ");

const inputStyle = {
  background: "rgba(255,255,255,0.70)",
  backdropFilter: "blur(16px)",
  WebkitBackdropFilter: "blur(16px)",
  border: "1px solid rgba(255,255,255,0.85)",
  boxShadow: "0 2px 12px rgba(0,0,0,0.06), inset 0 1px 0 rgba(255,255,255,0.95)",
};

const cardStyle = {
  background: "rgba(255,255,255,0.55)",
  backdropFilter: "blur(24px)",
  WebkitBackdropFilter: "blur(24px)",
  border: "1px solid rgba(255,255,255,0.85)",
  boxShadow: "0 8px 40px rgba(0,0,0,0.08), inset 0 1px 0 rgba(255,255,255,0.95)",
};

const primaryButtonStyle = {
  background: "linear-gradient(135deg, #3DDC97 0%, #14B989 100%)",
  boxShadow: "0 8px 24px rgba(29,184,122,0.32), inset 0 1px 0 rgba(255,255,255,0.25)",
};

export function Login() {
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: "", password: "" });
  const [showPw, setShowPw] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async () => {
    if (!form.email || !form.password) {
      setError("Please enter your email and password.");
      return;
    }
    try {
      const response = await loginUser({ user_email: form.email, password: form.password });
      setCurrentUserEmail(response.user.user_email ?? form.email);
      localStorage.setItem("isLoggedIn", "true");
      const langSet = localStorage.getItem("appLanguage");
      if (!langSet) navigate("/setup/language");
      else navigate("/splash");
    } catch {
      setError("Please check your email or password.");
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-100">
      <div className="relative h-screen w-full max-w-[390px] overflow-y-auto" style={{ background: airbrushBg }}>

        <div className="relative z-10 px-[28px] pt-[72px] pb-[48px]">
          {/* 로고 */}
          <div className="mb-[52px]">
            <div className="flex items-center gap-2 mb-3">
              <img
                src={careVisionLogoIcon}
                alt="Care Vision"
                className="w-9 h-9 rounded-[10px] object-cover"
                style={{ boxShadow: "0 4px 14px rgba(29,184,122,0.25)" }}
              />
              <img src={careVisionLogo} alt="Care Vision" className="h-[20px] w-[142px]" />
            </div>
            <p className="font-['Pretendard:Regular',sans-serif] text-[14px] text-[#888]">
              India Home Appliance Slef Care and A/S
              <br />
              AR Guide Service.
            </p>
          </div>

          <div className="rounded-[28px] p-6 mb-4" style={cardStyle}>
            <p className="font-['Pretendard:SemiBold',sans-serif] text-[16px] text-[#111] mb-5">Log In</p>

          <div className="flex flex-col gap-3 mb-2">
            <div>
              <p className="font-['Pretendard:Regular',sans-serif] text-[12px] text-[#888] mb-1.5 ml-1">Email</p>
              <input
                type="email"
                placeholder="Enter your email"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                className="w-full rounded-[14px] px-4 py-[13px] font-['Pretendard:Regular',sans-serif] text-[14px] text-[#111] placeholder:text-[#c8ccd0] outline-none"
                style={inputStyle}
              />
            </div>
            <div>
              <p className="font-['Pretendard:Regular',sans-serif] text-[12px] text-[#888] mb-1.5 ml-1">Password</p>
              <div className="relative">
                <input
                  type={showPw ? "text" : "password"}
                  placeholder="Enter your password"
                  value={form.password}
                  onChange={(e) => setForm({ ...form, password: e.target.value })}
                  className="w-full rounded-[14px] px-4 py-[13px] pr-12 font-['Pretendard:Regular',sans-serif] text-[14px] text-[#111] placeholder:text-[#c8ccd0] outline-none"
                  style={inputStyle}
                />
                <button
                  type="button"
                  onClick={() => setShowPw(!showPw)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-[#c8ccd0]"
                  aria-label={showPw ? "Hide password" : "Show password"}
                >
                  {showPw ? <EyeOff size={17} /> : <Eye size={17} />}
                </button>
              </div>
            </div>
          </div>

          {error && <p className="font-['Pretendard:Medium',sans-serif] text-[12px] text-[#ff4c49] mt-2 ml-1">{error}</p>}
          </div>

          <button
            onClick={handleSubmit}
            className="w-full text-white rounded-[18px] py-[15px] font-['Pretendard:Medium',sans-serif] text-[14px] mb-5 transition-opacity hover:opacity-90"
            style={primaryButtonStyle}
          >
            Log In
          </button>

          <div className="flex items-center justify-center gap-2">
            <p className="font-['Pretendard:Regular',sans-serif] text-[13px] text-[#888]">Don't have an account?</p>
            <button onClick={() => navigate("/signup")}
              className="font-['Pretendard:SemiBold',sans-serif] text-[13px] text-[#14B989]">
              Sign Up
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
